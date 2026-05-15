from pathlib import Path


def read_file(root: str, path: str) -> str:
    return (Path(root) / path).read_text(encoding="utf-8")


def write_file(root: str, path: str, content: str) -> None:
    target = Path(root) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
