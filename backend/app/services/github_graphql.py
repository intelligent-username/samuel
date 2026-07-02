import httpx

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

REPOS_QUERY = """
query($username: String!) {
  user(login: $username) {
    repositories(first: 50, orderBy: {field: UPDATED_AT, direction: DESC}, ownerAffiliations: OWNER) {
      nodes {
        id
        name
        description
        stargazerCount
        languages(first: 10) {
          edges {
            size
            node { name }
          }
        }
        repositoryTopics(first: 10) {
          nodes { topic { name } }
        }
        pushedAt
        readme: object(expression: "HEAD:README.md") {
          ... on Blob { text }
        }
        readmeAlt: object(expression: "HEAD:README") {
          ... on Blob { text }
        }
      }
    }
  }
}
"""


async def fetch_user_repos(access_token: str, username: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_GRAPHQL_URL,
            json={"query": REPOS_QUERY, "variables": {"username": username}},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    repos = data.get("data", {}).get("user", {}).get("repositories", {}).get("nodes", [])
    return [_format_repo(r) for r in repos]


def _format_repo(raw: dict) -> dict:
    languages = {}
    for edge in (raw.get("languages") or {}).get("edges", []):
        languages[edge["node"]["name"]] = edge["size"]

    topics = [t["topic"]["name"] for t in (raw.get("repositoryTopics") or {}).get("nodes", [])]

    readme = None
    if raw.get("readme"):
        readme = raw["readme"].get("text")
    if not readme and raw.get("readmeAlt"):
        readme = raw["readmeAlt"].get("text")

    return {
        "github_repo_id": int(raw["id"]),
        "name": raw["name"],
        "description": raw.get("description"),
        "stars": raw.get("stargazerCount", 0),
        "languages": languages,
        "readme_text": readme,
        "topics": topics,
        "last_push": raw.get("pushedAt"),
    }