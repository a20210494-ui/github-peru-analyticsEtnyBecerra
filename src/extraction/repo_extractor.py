import base64
from src.extraction.github_client import GitHubClient

class RepoExtractor:
    def __init__(self, client: GitHubClient):
        self.client = client

    def search_repos_by_stars(self, location_users: list[str], min_stars: int = 1) -> list[dict]:
        """
        Search for top repositories from users in a location.
        """
        repos = []

        for username in location_users:
            user_repos = self.client.make_request(
                f"users/{username}/repos",
                params={"sort": "stars", "direction": "desc"}
            )

            for repo in user_repos:
                if repo.get("stargazers_count", 0) >= min_stars:
                    repos.append(repo)

        # Ordenar todos los repositorios por estrellas de mayor a menor y tomar los 1000 mejores
        repos.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
        return repos[:1000]

    def get_repo_readme(self, owner: str, repo: str) -> str:
        """
        Get the README content of a repository.
        Returns empty string if not found.
        """
        try:
            result = self.client.make_request(
                f"repos/{owner}/{repo}/readme"
            )

            content = base64.b64decode(result["content"]).decode("utf-8")
            return content[:5000]  # Limitado a 5000 caracteres para ahorrar costos de API

        except Exception:
            return ""

    def get_repo_languages(self, owner: str, repo: str) -> dict:
        """Get the language breakdown of a repository."""
        return self.client.make_request(f"repos/{owner}/{repo}/languages")

    def get_repo_contributors(self, owner: str, repo: str) -> list[dict]:
        """Get the contributors of a repository."""
        return self.client.make_request(
            f"repos/{owner}/{repo}/contributors",
            params={"per_page": 100}
        )