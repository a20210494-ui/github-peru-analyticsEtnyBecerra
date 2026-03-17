import os
import requests
from dotenv import load_dotenv

# Cargamos el archivo .env por si tienes tu Token de GitHub ahí
load_dotenv()

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        # Si tienes token, lo usa para que GitHub no te bloquee por descargar mucho
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        
        self.base_url = "https://api.github.com"

    def search_users(self, query: str, limit: int = 50) -> list:
        """Busca usuarios en GitHub y obtiene sus detalles básicos."""
        url = f"{self.base_url}/search/users"
        params = {"q": query, "per_page": limit}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status() # Verifica que no haya errores de conexión
            
            data = response.json()
            items = data.get("items", [])[:limit]
            
            detailed_users = []
            
            # Por cada usuario encontrado, pedimos sus detalles (para saber sus seguidores)
            for item in items:
                user_resp = requests.get(item["url"], headers=self.headers)
                if user_resp.status_code == 200:
                    u_data = user_resp.json()
                    detailed_users.append({
                        "login": u_data.get("login"),
                        "name": u_data.get("name", u_data.get("login")),
                        "location": u_data.get("location", "Peru"),
                        "followers": u_data.get("followers", 0),
                        "public_repos": u_data.get("public_repos", 0),
                        "impact_score": 0 # Lo calcularemos después
                    })
            
            return detailed_users

        except requests.exceptions.RequestException as e:
            print(f"❌ Error al conectar con GitHub: {e}")
            return []