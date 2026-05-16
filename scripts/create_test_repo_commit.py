# scripts/create_test_repo_commit.py
# Script that pushes a broken commit to trigger the demo.
# Usage: python scripts/create_test_repo_commit.py --token YOUR_PAT --repo owner/repo

import argparse
import base64
import httpx
import sys

def push_broken_commit(token: str, repo: str, branch: str = "main"):
    """
    Creates a commit that adds a conflicting dependency to requirements.txt.
    Content: requests==2.28.0 and httpx==0.23.0
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    file_path = "requirements.txt"
    content = "requests==2.28.0\nhttpx==0.23.0\n"
    message = "test: introduce dependency conflict for demo"
    
    # 1. Get the current file SHA (if it exists)
    sha = None
    with httpx.Client() as client:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            sha = resp.json()["sha"]
        
        # 2. Push the new commit
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch
        }
        if sha:
            payload["sha"] = sha
            
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        resp = client.put(url, headers=headers, json=payload)
        
        if resp.status_code in [200, 201]:
            print(f"Successfully pushed broken commit to {repo} on branch {branch}")
            print(f"Commit SHA: {resp.json()['commit']['sha']}")
        else:
            print(f"Error: Failed to push commit ({resp.status_code})")
            print(resp.text)
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--repo", required=True, help="Repository in owner/repo format")
    parser.add_argument("--branch", default="main", help="Target branch (default: main)")
    args = parser.parse_args()

    push_broken_commit(args.token, args.repo, args.branch)
