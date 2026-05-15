def resolve_import(name: str, files: dict[str, str]) -> bool:
    return any(name in content for content in files.values())
