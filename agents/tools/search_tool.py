async def search(query: str, num_results: int = 5) -> list[dict]:
    return [
        {
            "title": "Requests installation documentation",
            "url": "https://requests.readthedocs.io/",
            "snippet": "Pin a compatible requests version and rebuild the environment.",
        }
    ][:num_results]


async def fetch_page(url: str) -> str:
    return "Pin compatible dependency versions and rerun the package installer."
