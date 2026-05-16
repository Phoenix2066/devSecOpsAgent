import asyncio
import io
import zipfile
from github import Github, InputGitTreeElement, GithubException

def _get_client(token: str) -> Github:
    """Helper to create a PyGithub instance."""
    return Github(token)

async def get_file(token: str, repo_name: str, path: str, ref: str = "main") -> str:
    """Fetch decoded file content as string. Raise FileNotFoundError if path doesn't exist."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        try:
            content = repo.get_contents(path, ref=ref)
            if isinstance(content, list):
                raise FileNotFoundError(f"Path {path} is a directory, not a file.")
            return content.decoded_content.decode("utf-8")
        except GithubException as e:
            if e.status == 404:
                raise FileNotFoundError(f"File not found: {path}")
            raise e
    return await asyncio.to_thread(_sync)

async def get_file_tree(token: str, repo_name: str, ref: str = "main") -> list[str]:
    """Return flat list of all file paths in repo. Max depth: full tree."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        # Get the tree SHA for the ref
        branch = repo.get_branch(ref)
        sha = branch.commit.commit.tree.sha
        tree = repo.get_git_tree(sha, recursive=True)
        return [item.path for item in tree.tree if item.type == "blob"]
    return await asyncio.to_thread(_sync)

async def get_actions_logs(token: str, repo_name: str, run_id: str) -> str:
    """Fetch GitHub Actions workflow run logs. Download zip, extract, return concatenated text."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        run = repo.get_workflow_run(int(run_id))
        
        # This returns a redirect URL to a zip file
        logs_url = run.download_logs()
        import httpx
        with httpx.Client() as client:
            response = client.get(logs_url, follow_redirects=True)
            response.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                log_contents = []
                for filename in z.namelist():
                    # GitHub logs are usually in .txt files within the zip
                    with z.open(filename) as f:
                        log_contents.append(f.read().decode("utf-8", errors="ignore"))
                return "\n".join(log_contents)
    return await asyncio.to_thread(_sync)

async def create_branch(token: str, repo_name: str, base_sha: str, branch_name: str) -> str:
    """Create new branch from base_sha. Return branch ref string."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        ref = repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        return ref.ref
    return await asyncio.to_thread(_sync)

async def commit_files(token: str, repo_name: str, branch: str, message: str, files: dict[str, str]) -> str:
    """Commit multiple files in one commit. files = {filepath: content}. Return commit SHA."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        
        # 1. Get the current branch reference
        git_ref = repo.get_git_ref(f"heads/{branch}")
        base_commit = repo.get_git_commit(git_ref.object.sha)
        base_tree = base_commit.tree
        
        # 2. Create tree elements
        element_list = []
        for path, content in files.items():
            element = InputGitTreeElement(path, "100644", "blob", content=content)
            element_list.append(element)
            
        # 3. Create a new tree
        new_tree = repo.create_git_tree(element_list, base_tree)
        
        # 4. Create a new commit
        new_commit = repo.create_git_commit(message, new_tree, [base_commit])
        
        # 5. Update the reference
        git_ref.edit(new_commit.sha)
        
        return new_commit.sha
    return await asyncio.to_thread(_sync)

async def open_pull_request(token: str, repo_name: str, head: str, base: str, title: str, body: str) -> str:
    """Open PR from head branch to base branch. Return PR URL."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return pr.html_url
    return await asyncio.to_thread(_sync)

async def get_latest_run_id(token: str, repo_name: str, branch: str) -> str:
    """Get the most recent Actions workflow run ID for a branch. Return run ID as string."""
    def _sync():
        g = _get_client(token)
        repo = g.get_repo(repo_name)
        runs = repo.get_workflow_runs(branch=branch)
        if runs.totalCount == 0:
            raise RuntimeError(f"No workflow runs found for branch {branch}")
        return str(runs[0].id)
    return await asyncio.to_thread(_sync)
