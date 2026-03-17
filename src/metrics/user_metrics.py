"""
user_metrics.py
================
Calcula métricas agregadas a nivel de usuario para el ecosistema de
desarrolladores peruanos en GitHub.

Métricas principales
--------------------
- impact_score       : (followers×0.5) + (total_stars×0.3) + (public_repos×0.2)
- total_stars_received: suma de estrellas de todos los repositorios públicos
- activity_index      : log1p(public_repos) × log1p(followers)  — mide actividad combinada
"""

import os
import math
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


# ──────────────────────────────────────────────────────────────────────────────
# Función de nivel de módulo (compatible con código anterior)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_impact_score(followers: int, total_stars: int, public_repos: int) -> float:
    """
    Calcula el impacto de un desarrollador en la comunidad peruana.
    Fórmula: (Followers × 0.5) + (Stars × 0.3) + (Repos × 0.2)
    """
    try:
        score = (int(followers) * 0.5) + (int(total_stars) * 0.3) + (int(public_repos) * 0.2)
        return round(score, 2)
    except (ValueError, TypeError):
        return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Clase principal
# ──────────────────────────────────────────────────────────────────────────────

class UserMetricsCalculator:
    """
    Calcula y enriquece las métricas de los desarrolladores extraídos de GitHub.

    Uso básico:
        calc = UserMetricsCalculator()
        df   = calc.process_users_csv("data/processed/users.csv",
                                       "data/processed/users_enriched.csv")
    """

    GITHUB_API = "https://api.github.com"

    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = data_dir
        self.github_token = os.getenv("GITHUB_TOKEN")
        self._headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            self._headers["Authorization"] = f"token {self.github_token}"

    # ── Métrica individual ──────────────────────────────────────────────────

    @staticmethod
    def calculate_impact_score(
        followers: int, total_stars: int, public_repos: int
    ) -> float:
        """
        Fórmula de impacto:
            (followers × 0.5) + (total_stars × 0.3) + (public_repos × 0.2)
        """
        try:
            score = (
                int(followers) * 0.5
                + int(total_stars) * 0.3
                + int(public_repos) * 0.2
            )
            return round(score, 2)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def calculate_activity_index(followers: int, public_repos: int) -> float:
        """
        Índice de actividad combinada:
            log1p(public_repos) × log1p(followers)
        Penaliza perfiles con muchos seguidores pero poca producción de código,
        o viceversa.
        """
        try:
            return round(math.log1p(int(public_repos)) * math.log1p(int(followers)), 4)
        except (ValueError, TypeError):
            return 0.0

    # ── Llamada a GitHub API para obtener estrellas ─────────────────────────

    def _get_total_stars(self, username: str) -> int:
        """
        Suma las estrellas de todos los repositorios públicos del usuario.
        Paginado: 100 repos por página.
        """
        total = 0
        page = 1
        while True:
            url = f"{self.GITHUB_API}/users/{username}/repos"
            params = {"per_page": 100, "page": page, "type": "owner"}
            try:
                resp = requests.get(url, headers=self._headers, params=params, timeout=10)
                if resp.status_code == 403:
                    # Rate-limit alcanzado
                    reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait = max(reset_ts - int(time.time()), 5)
                    print(f"  ⏳ Rate-limit GitHub. Esperando {wait}s …")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    break
                repos = resp.json()
                if not repos:
                    break
                total += sum(r.get("stargazers_count", 0) for r in repos)
                if len(repos) < 100:
                    break
                page += 1
            except requests.RequestException:
                break
        return total

    # ── Cálculo sobre un DataFrame completo ────────────────────────────────

    def calculate_all_metrics(
        self, users_df: pd.DataFrame, fetch_stars: bool = False
    ) -> pd.DataFrame:
        """
        Añade columnas de métricas al DataFrame de usuarios.

        Args:
            users_df:    DataFrame con columnas: login, followers, public_repos.
            fetch_stars: Si True, consulta la API de GitHub para obtener
                         total_stars_received (más preciso pero más lento).

        Returns:
            DataFrame enriquecido con las nuevas columnas de métricas.
        """
        df = users_df.copy()

        # Asegurar tipos numéricos
        df["followers"] = pd.to_numeric(df.get("followers", 0), errors="coerce").fillna(0).astype(int)
        df["public_repos"] = pd.to_numeric(df.get("public_repos", 0), errors="coerce").fillna(0).astype(int)

        # ── Estrellas totales ──────────────────────────────────────────────
        if fetch_stars:
            print("⭐ Obteniendo estrellas totales desde GitHub API…")
            stars_list = []
            for login in tqdm(df["login"], desc="Fetching stars", unit="user"):
                stars_list.append(self._get_total_stars(login))
                time.sleep(0.3)  # cortesía con la API
            df["total_stars_received"] = stars_list
        else:
            # Si el CSV ya tiene la columna, la preservamos; si no, ponemos 0
            if "total_stars_received" not in df.columns:
                df["total_stars_received"] = 0

        df["total_stars_received"] = (
            pd.to_numeric(df["total_stars_received"], errors="coerce").fillna(0).astype(int)
        )

        # ── Impact Score ───────────────────────────────────────────────────
        df["impact_score"] = df.apply(
            lambda row: self.calculate_impact_score(
                row["followers"],
                row["total_stars_received"],
                row["public_repos"],
            ),
            axis=1,
        )

        # ── Activity Index ─────────────────────────────────────────────────
        df["activity_index"] = df.apply(
            lambda row: self.calculate_activity_index(
                row["followers"], row["public_repos"]
            ),
            axis=1,
        )

        # ── Percentil de impacto (ranking relativo 0–100) ──────────────────
        max_score = df["impact_score"].max()
        df["impact_percentile"] = (
            (df["impact_score"] / max_score * 100).round(1) if max_score > 0 else 0.0
        )

        # Ordenar de mayor a menor impacto
        df = df.sort_values("impact_score", ascending=False).reset_index(drop=True)
        df.insert(0, "rank", range(1, len(df) + 1))

        return df

    # ── Flujo completo CSV → CSV ────────────────────────────────────────────

    def process_users_csv(
        self,
        input_path: str,
        output_path: str,
        fetch_stars: bool = False,
    ) -> pd.DataFrame:
        """
        Carga users.csv, calcula métricas y guarda un CSV enriquecido.

        Args:
            input_path:  Ruta al CSV de entrada (generado por extract_data.py).
            output_path: Ruta de salida para el CSV enriquecido.
            fetch_stars: Si True, consulta GitHub API para obtener estrellas reales.

        Returns:
            DataFrame enriquecido.
        """
        print(f"📂 Cargando usuarios desde: {input_path}")
        df = pd.read_csv(input_path)
        print(f"👥 {len(df)} usuarios encontrados.\n")

        enriched_df = self.calculate_all_metrics(df, fetch_stars=fetch_stars)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        enriched_df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"\n💾 CSV enriquecido guardado en: {output_path}")

        # Vista previa del top 5
        print("\n🏆 Top 5 desarrolladores por impact_score:")
        preview_cols = ["rank", "login", "name", "followers", "public_repos",
                        "total_stars_received", "impact_score", "activity_index"]
        available = [c for c in preview_cols if c in enriched_df.columns]
        print(enriched_df[available].head(5).to_string(index=False))

        return enriched_df

    # ── Utilidad de consulta ────────────────────────────────────────────────

    def get_top_developers(
        self,
        df: pd.DataFrame,
        metric: str = "impact_score",
        n: int = 10,
    ) -> pd.DataFrame:
        """
        Retorna los top N desarrolladores según la métrica indicada.

        Args:
            df:     DataFrame ya enriquecido (resultado de calculate_all_metrics).
            metric: Columna por la que ordenar (impact_score, followers, …).
            n:      Cantidad de desarrolladores a retornar.

        Returns:
            DataFrame con los top N desarrolladores.
        """
        if metric not in df.columns:
            raise ValueError(f"Métrica '{metric}' no encontrada. Disponibles: {list(df.columns)}")
        return df.nlargest(n, metric)[["rank", "login", "name", metric]].reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# Script independiente (python src/metrics/user_metrics.py)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os
    # Asegurar que el directorio raíz del proyecto esté en el path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    calc = UserMetricsCalculator(data_dir="data/processed")
    enriched = calc.process_users_csv(
        input_path="data/processed/users.csv",
        output_path="data/processed/users_enriched.csv",
        fetch_stars=False,  # Cambia a True para obtener estrellas reales de GitHub
    )
    print("\n✅ ¡Métricas calculadas exitosamente!")