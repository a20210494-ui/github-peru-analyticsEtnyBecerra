from src.extraction.github_client import GitHubClient

class UserExtractor:
    def __init__(self, client: GitHubClient):
        self.client = client

    def search_users_by_location(self, location: str, max_users: int = 1000) -> list[dict]:
        """
        Search for users by location.
        Args:
            location: Location string (e.g., "Peru", "Lima")
            max_users: Maximum number of users to retrieve
        Returns:
            List of user dictionaries
        """
        users = []
        page = 1
        per_page = 100  # Máximo permitido por GitHub por página

        while len(users) < max_users:
            result = self.client.make_request(
                "search/users",
                params={
                    "q": f"location:{location}",
                    "per_page": per_page,
                    "page": page,
                    "sort": "followers",  # Obtener los más influyentes primero
                    "order": "desc"
                }
            )

            if not result.get("items"):
                break

            users.extend(result["items"])
            page += 1

            # La API de búsqueda de GitHub limita a 1000 resultados en total
            if page * per_page >= 1000:
                break

        return users[:max_users]

    def get_user_details(self, username: str) -> dict:
        """Get detailed information for a specific user."""
        return self.client.make_request(f"users/{username}")

    def get_user_repos(self, username: str) -> list[dict]:
        """Get all repositories for a user."""
        repos = []
        page = 1

        while True:
            result = self.client.make_request(
                f"users/{username}/repos",
                params={
                    "per_page": 100,
                    "page": page,
                    "type": "owner"  # SOLO repositorios propios, no copias (forks)
                }
            )

            if not result:
                break

            repos.extend(result)
            page += 1

        return repos