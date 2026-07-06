import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

REPOS_QUERY = """
query($username: String!) {
  user(login: $username) {
    avatarUrl
    repositories(
      first: 100,
      ownerAffiliations: OWNER,
      isFork: false,
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      nodes {
        databaseId
        name
        description
        url
        homepageUrl
        stargazerCount
        forkCount
        isArchived
        isPrivate
        createdAt
        pushedAt
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
        repositoryTopics(first: 10) {
          nodes { topic { name } }
        }
        readme:      object(expression: "HEAD:README.md")   { ... on Blob { text } }
        readmeLower: object(expression: "HEAD:readme.md")   { ... on Blob { text } }
        readmeAlt:   object(expression: "HEAD:README")      { ... on Blob { text } }
        pyprojectToml: object(expression: "HEAD:pyproject.toml") { ... on Blob { byteSize } }
        cargoToml:     object(expression: "HEAD:Cargo.toml")     { ... on Blob { byteSize } }
        packageJson:   object(expression: "HEAD:package.json")   { ... on Blob { byteSize } }
      }
    }
  }
}
"""


async def fetch_user_repos(access_token: str, username: str) -> tuple[list[dict], str | None]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_GRAPHQL_URL,
            json={"query": REPOS_QUERY, "variables": {"username": username}},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    user_data = data.get("data", {}).get("user", {})
    avatar_url = user_data.get("avatarUrl")
    repos = user_data.get("repositories", {}).get("nodes", [])
    return [_format_repo(r) for r in repos], avatar_url


def _parse_datetime(date_str: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string, returning None on failure."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.warning("Could not parse datetime string: %s", date_str)
        return None


def _format_repo(raw: dict) -> dict:
    languages = {}
    for edge in (raw.get("languages") or {}).get("edges", []):
        languages[edge["node"]["name"]] = edge["size"]

    topics = [t["topic"]["name"] for t in (raw.get("repositoryTopics") or {}).get("nodes", [])]
    if raw.get("pyprojectToml"):
        topics.append("pyproject-toml")
    if raw.get("cargoToml"):
        topics.append("cargo-toml")
    if raw.get("packageJson"):
        topics.append("package-json")

    readme = None
    for key in ("readme", "readmeLower", "readmeAlt"):
        val = raw.get(key)
        if val and val.get("text"):
            readme = val["text"]
            break

    return {
        "github_repo_id": raw["databaseId"],
        "name": raw["name"],
        "description": raw.get("description"),
        "stars": raw.get("stargazerCount", 0),
        "languages": languages,
        "readme_text": readme,
        "topics": topics,
        "last_push": _parse_datetime(raw.get("pushedAt")),
        "homepage_url": raw.get("homepageUrl"),
        "forks": raw.get("forkCount", 0),
        "is_archived": raw.get("isArchived", False),
        "is_private": raw.get("isPrivate", False),
        "repo_created_at": _parse_datetime(raw.get("createdAt")),
        "url": raw.get("url"),
    }
