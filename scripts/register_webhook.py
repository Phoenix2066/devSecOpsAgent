# scripts/register_webhook.py
# Registers a GitHub webhook for a repository.
# Usage: python scripts/register_webhook.py \
#          --token YOUR_PAT \
#          --repo owner/repo \
#          --url https://your-domain/webhook/github \
#          --secret YOUR_WEBHOOK_SECRET

import argparse
import secrets
import httpx
import sys

def register_webhook(token: str, repo: str,
                      url: str, secret: str) -> dict:
    """POST https://api.github.com/repos/{repo}/hooks"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "name": "web",
        "active": True,
        "events": ["push", "workflow_run", "check_run"],
        "config": {
            "url": url,
            "content_type": "json",
            "secret": secret,
            "insecure_ssl": "0"
        }
    }
    
    with httpx.Client() as client:
        response = client.post(f"https://api.github.com/repos/{repo}/hooks", headers=headers, json=payload)
        if response.status_code != 201:
            print(f"Error: Failed to register webhook ({response.status_code})")
            print(response.text)
            sys.exit(1)
        return response.json()

def generate_secret() -> str:
    return secrets.token_hex(32)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--repo", required=True, help="Repository in owner/repo format")
    parser.add_argument("--url", required=True, help="Publicly accessible URL of your backend webhook endpoint")
    parser.add_argument("--secret", default=None, help="Webhook secret (auto-generated if omitted)")
    args = parser.parse_args()

    secret = args.secret or generate_secret()
    print(f"Webhook secret: {secret}")
    print("CRITICAL: Store this secret in your project's 'webhook_secret' field in PostgreSQL.")

    result = register_webhook(args.token, args.repo, args.url, secret)
    print(f"Webhook registered successfully: ID={result['id']}")
