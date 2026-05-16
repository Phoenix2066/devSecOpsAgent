import ast
import asyncio
import re
import yaml
import json
from pathlib import Path

async def detect_language(filepath: str, content: str) -> str:
    """Detect programming language from filepath extension and content hints."""
    ext = Path(filepath).suffix.lower()
    
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".yaml": "yaml",
        ".yml": "yaml",
        "dockerfile": "dockerfile"
    }
    
    if ext in mapping:
        return mapping[ext]
    
    filename = Path(filepath).name.lower()
    if filename == "dockerfile":
        return "dockerfile"
    
    # Hints in content
    if content.startswith("#!"):
        if "python" in content: return "python"
        if "node" in content: return "javascript"
    
    if "package.json" in filename: return "javascript"
    if "go.mod" in filename: return "go"
    
    return "unknown"

async def analyze_imports(filepath: str, content: str) -> dict:
    """Analyze import statements in a source file."""
    language = await detect_language(filepath, content)
    
    result = {
        "language": language,
        "imports": [],
        "issues": []
    }
    
    if language == "python":
        def _analyze_py():
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            result["imports"].append({
                                "module": alias.name,
                                "alias": alias.asname,
                                "line": node.lineno
                            })
                    elif isinstance(node, ast.ImportFrom):
                        result["imports"].append({
                            "module": node.module,
                            "alias": None,
                            "line": node.lineno
                        })
                # Basic unused/circular check would require cross-file analysis or 
                # tracking all names in the AST. For now, just collect.
            except SyntaxError as e:
                result["issues"].append({
                    "type": "syntax_error",
                    "detail": str(e),
                    "line": e.lineno
                })
        await asyncio.to_thread(_analyze_py)
    
    elif language in ["javascript", "typescript"]:
        # Simple regex for JS/TS
        import_regex = r'(?:import\s+(?:.*?\s+from\s+)?[\'"](.*?)[\'"]|require\s*\(\s*[\'"](.*?)[\'"]\s*\))'
        matches = re.finditer(import_regex, content)
        for i, match in enumerate(matches):
            module = match.group(1) or match.group(2)
            result["imports"].append({
                "module": module,
                "alias": None,
                "line": content.count('\n', 0, match.start()) + 1
            })
            
    elif language == "go":
        # Simple regex for Go imports
        import_block = re.search(r'import\s+\((.*?)\)', content, re.DOTALL)
        if import_block:
            for line_no, line in enumerate(import_block.group(1).split('\n'), 1):
                m = re.search(r'[\'"](.*?)[\'"]', line)
                if m:
                    result["imports"].append({"module": m.group(1), "alias": None, "line": line_no})
        else:
            m = re.search(r'import\s+[\'"](.*?)[\'"]', content)
            if m:
                result["imports"].append({"module": m.group(1), "alias": None, "line": 1})

    return result

async def analyze_dependencies(filepath: str, content: str) -> dict:
    """Parse a dependency file and extract package list with versions."""
    filename = Path(filepath).name.lower()
    
    result = {
        "package_manager": "unknown",
        "packages": [],
        "issues": []
    }
    
    if filename == "requirements.txt":
        result["package_manager"] = "pip"
        for line_no, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # Simple pip split
            match = re.split(r'(==|>=|<=|>|<|~=)', line)
            if len(match) >= 3:
                name, version = match[0].strip(), "".join(match[1:]).strip()
                result["packages"].append({"name": name, "version": version, "raw": line})
            else:
                result["packages"].append({"name": line.strip(), "version": "unpinned", "raw": line})
                result["issues"].append({
                    "type": "unpinned_version",
                    "detail": "Package is not pinned to a specific version",
                    "package": line.strip()
                })
                
    elif filename == "package.json":
        result["package_manager"] = "npm"
        try:
            data = json.loads(content)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for name, version in deps.items():
                result["packages"].append({"name": name, "version": version, "raw": f"{name}: {version}"})
                if version == "*" or version == "":
                    result["issues"].append({
                        "type": "unpinned_version",
                        "detail": "Package version is unpinned",
                        "package": name
                    })
        except json.JSONDecodeError as e:
            result["issues"].append({"type": "syntax_error", "detail": str(e), "package": "json"})

    elif filename == "go.mod":
        result["package_manager"] = "go"
        # Very basic go.mod parsing
        for line in content.splitlines():
            m = re.search(r'^\s*([^\s]+)\s+(v[^\s]+)', line)
            if m:
                result["packages"].append({"name": m.group(1), "version": m.group(2), "raw": line.strip()})

    return result

async def extract_error_signature(raw_log: str) -> str:
    """Extract a normalized, short error signature from raw log/traceback text."""
    def _extract():
        sig = "unknown_error"
        
        # Python
        if "Traceback" in raw_log:
            lines = raw_log.strip().splitlines()
            # Find last line which is usually the Exception: Detail
            last_line = lines[-1]
            exc_match = re.match(r'^(\w+):', last_line)
            exc_type = exc_match.group(1).lower() if exc_match else "error"
            
            # Find last frame
            frame_match = re.findall(r'File "(.*?)", line (\d+), in (.*)', raw_log)
            if frame_match:
                last_frame = frame_match[-1]
                module = Path(last_frame[0]).stem
                func = last_frame[2]
                sig = f"{exc_type}:{module}:{func}"
            else:
                sig = f"{exc_type}:{last_line[:30]}"
        
        # npm / Node
        elif "npm ERR!" in raw_log or "Error: " in raw_log:
            code_match = re.search(r'code (\w+)', raw_log)
            pkg_match = re.search(r'npm ERR!.*?\s+([^\s]+)@', raw_log)
            code = code_match.group(1).lower() if code_match else "error"
            pkg = pkg_match.group(1).lower() if pkg_match else "npm"
            sig = f"npm_{code}:{pkg}"
            
        # Go
        elif "go:" in raw_log or "panic:" in raw_log:
            pkg_match = re.search(r'([^\s/]+\.[^\s/]+/[^\s:]+)', raw_log)
            pkg = pkg_match.group(1).lower() if pkg_match else "go"
            sig = f"go_error:{pkg}"

        # Docker
        elif "Step " in raw_log and "ERROR:" in raw_log:
            step_match = re.search(r'Step (\d+/\d+)', raw_log)
            step = step_match.group(1) if step_match else "step"
            sig = f"docker_error:{step}"

        # Normalize
        sig = sig.lower()
        sig = re.sub(r'\d+\.\d+\.\d+', 'VERSION', sig)
        sig = re.sub(r'[^a-z0-9_:]', '_', sig)
        return sig[:120]

    return await asyncio.to_thread(_extract)

async def validate_yaml(content: str) -> dict:
    """Validate YAML syntax."""
    def _validate():
        try:
            yaml.safe_load(content)
            return {"valid": True, "error": None, "line": None}
        except yaml.YAMLError as e:
            line = None
            if hasattr(e, 'problem_mark'):
                line = e.problem_mark.line + 1
            return {"valid": False, "error": str(e), "line": line}
            
    return await asyncio.to_thread(_validate)

async def validate_dockerfile(content: str) -> dict:
    """Validate Dockerfile basic structure."""
    issues = []
    lines = content.splitlines()
    instructions = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"): continue
        
        # Get instruction
        match = re.match(r'^([A-Z]+)\s+(.*)', line)
        if match:
            inst = match.group(1)
            args = match.group(2)
            instructions.append((inst, args, i))
            
            if inst == "RUN" and not args.strip():
                issues.append({"rule": "no_empty_run", "line": i, "detail": "RUN command is empty"})
            
            if inst == "EXPOSE":
                if not re.match(r'^\d+', args):
                    issues.append({"rule": "numeric_port", "line": i, "detail": "EXPOSE should use numeric ports"})

    if not instructions:
        issues.append({"rule": "no_instructions", "line": 0, "detail": "Dockerfile has no instructions"})
    else:
        if instructions[0][0] != "FROM":
            issues.append({"rule": "from_first", "line": instructions[0][2], "detail": "FROM must be the first instruction"})
            
    has_from = any(i[0] == "FROM" for i in instructions)
    if not has_from:
        issues.append({"rule": "missing_from", "line": 0, "detail": "Missing FROM instruction"})
        
    has_entry = any(i[0] in ["CMD", "ENTRYPOINT"] for i in instructions)
    if not has_entry:
        issues.append({"rule": "missing_entrypoint", "line": 0, "detail": "Missing CMD or ENTRYPOINT"})

    return {"valid": len(issues) == 0, "issues": issues}
