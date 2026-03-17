"""
extract_data.py
================
Extrae más de 1.000 repositorios de desarrolladores de GitHub en Perú.

Flujo:
  1. Busca usuarios con "location:peru" en múltiples páginas (API Search)
  2. Por cada usuario, descarga sus repositorios públicos (paginado)
  3. Repite hasta juntar ≥ TARGET_REPOS repositorios
  4. Guarda data/processed/repositories.csv  y  data/processed/users.csv

Rate-limit awareness:
  - Con GITHUB_TOKEN: 5.000 req/h → seguro para 1000+ repos
  - Sin token: 60 req/h → muy lento, se recomienda usar token
"""

import os
import sys
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

# ── Path trick para encontrar el .env en la raíz del proyecto ──────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
load_dotenv(os.path.join(_ROOT, ".env"))

# ── Configuración ───────────────────────────────────────────────────────────
TARGET_REPOS   = 1_000          # Meta de repositorios
USERS_PER_PAGE = 30             # Max permitido por la Search API (sin GraphQL)
REPOS_PER_PAGE = 100            # Max por página para /users/{login}/repos
OUTPUT_DIR     = os.path.join(_ROOT, "data", "processed")
REPOS_CSV      = os.path.join(OUTPUT_DIR, "repositories.csv")
USERS_CSV      = os.path.join(OUTPUT_DIR, "users.csv")

GITHUB_API  = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    **({"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}),
}

# ── Helpers ─────────────────────────────────────────────────────────────────

def _check_rate_limit(response: requests.Response) -> None:
    """Si queda poco rate-limit, espera hasta que se renueve."""
    remaining = int(response.headers.get("X-RateLimit-Remaining", 99))
    if remaining < 5:
        reset_ts = int(response.headers.get("X-RateLimit-Reset", time.time() + 65))
        wait = max(reset_ts - int(time.time()), 5) + 2
        print(f"\n⏳ Rate-limit casi agotado. Esperando {wait}s para renovar…")
        time.sleep(wait)


def _get(url: str, params: dict = None, retries: int = 4) -> dict | list | None:
    """GET con reintentos y manejo de rate-limit."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
            _check_rate_limit(resp)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"\n⏳ 403 Forbidden – esperando {wait}s…")
                time.sleep(wait)
                continue
            if resp.status_code == 422:
                return None   # query inválida, no reintentar
            time.sleep(2 ** attempt)
        except requests.RequestException as exc:
            print(f"  ⚠️  Request error ({attempt+1}/{retries}): {exc}")
            time.sleep(4)
    return None


def search_peru_users(min_users: int = 300) -> list[dict]:
    """
    Busca usuarios con location:peru usando múltiples variantes de query
    para superar el límite de 1000 resultados de la Search API.
    """
    queries = [
        "location:peru",
        "location:lima",
        "location:arequipa",
        "location:trujillo",
        "location:cusco",
        "location:piura",
    ]
    seen_logins: set = set()
    users: list[dict] = []

    print(f"🔍 Buscando usuarios en Perú (meta: ≥{min_users} usuarios únicos)…")

    for query in queries:
        if len(users) >= min_users:
            break

        page = 1
        while len(users) < min_users:
            data = _get(
                f"{GITHUB_API}/search/users",
                params={"q": query, "per_page": USERS_PER_PAGE, "page": page},
            )
            if not data:
                break
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                login = item.get("login")
                if login and login not in seen_logins:
                    seen_logins.add(login)
                    users.append(item)

            total_count = data.get("total_count", 0)
            fetched = page * USERS_PER_PAGE
            print(
                f"   query='{query}' · página {page} · "
                f"usuarios únicos acumulados: {len(users)} / total API: {total_count}"
            )

            if fetched >= min(total_count, 1000):   # Search API limita a 1000 resultados
                break
            page += 1
            time.sleep(0.5)

    print(f"✅ {len(users)} usuarios únicos encontrados.\n")
    return users


def get_user_detail(login: str) -> dict:
    """Devuelve el detalle de un usuario (followers, public_repos, etc.)."""
    data = _get(f"{GITHUB_API}/users/{login}")
    if not data:
        return {}
    return {
        "login":        data.get("login"),
        "name":         data.get("name", login),
        "location":     data.get("location", "Peru"),
        "followers":    data.get("followers", 0),
        "public_repos": data.get("public_repos", 0),
        "impact_score": 0,
    }


def get_user_repos(login: str, max_repos: int = 200) -> list[dict]:
    """
    Descarga todos los repositorios públicos de un usuario (paginado).
    Devuelve lista de dicts con los campos que nos interesan.
    """
    repos = []
    page  = 1
    while len(repos) < max_repos:
        data = _get(
            f"{GITHUB_API}/users/{login}/repos",
            params={"per_page": REPOS_PER_PAGE, "page": page, "type": "owner", "sort": "updated"},
        )
        if not data or not isinstance(data, list):
            break
        for r in data:
            repos.append({
                "id":          r.get("id"),
                "name":        r.get("name"),
                "full_name":   r.get("full_name"),
                "owner_login": login,
                "description": r.get("description") or "",
                "language":    r.get("language") or "",
                "stars":       r.get("stargazers_count", 0),
                "forks":       r.get("forks_count", 0),
                "watchers":    r.get("watchers_count", 0),
                "open_issues": r.get("open_issues_count", 0),
                "topics":      ", ".join(r.get("topics", [])),
                "is_fork":     r.get("fork", False),
                "created_at":  r.get("created_at", ""),
                "updated_at":  r.get("updated_at", ""),
                "size_kb":     r.get("size", 0),
                "has_readme":  r.get("has_wiki", False),
                "url":         r.get("html_url", ""),
            })
        if len(data) < REPOS_PER_PAGE:
            break
        page += 1
        time.sleep(0.2)
    return repos


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not GITHUB_TOKEN:
        print("⚠️  GITHUB_TOKEN no encontrado en .env. Usarás el límite anónimo (60 req/h).")
        print("   Se recomienda agregar tu token para una extracción rápida.\n")
    else:
        print(f"🔑 GitHub Token detectado: {GITHUB_TOKEN[:8]}…  (5.000 req/h)\n")

    print("=" * 62)
    print("  🚀 EXTRACTOR DE REPOSITORIOS GITHUB PERÚ")
    print(f"  Meta: ≥ {TARGET_REPOS:,} repositorios")
    print("=" * 62 + "\n")

    # ── PASO 1: Buscar usuarios ──────────────────────────────────────────────
    raw_users = search_peru_users(min_users=300)

    # ── PASO 2: Detalles de cada usuario + repositorios ──────────────────────
    all_repos:  list[dict] = []
    all_users:  list[dict] = []
    users_done: set        = set()

    print(f"📦 Descargando repositorios de {len(raw_users)} usuarios…")
    print(f"   (parará cuando alcance {TARGET_REPOS:,} repos)\n")

    with tqdm(
        total=TARGET_REPOS,
        desc="📁 Repositorios",
        unit="repo",
    ) as repo_bar:

        for raw_user in tqdm(raw_users, desc="👤 Usuarios", unit="user", leave=False):
            if len(all_repos) >= TARGET_REPOS:
                break

            login = raw_user.get("login")
            if not login or login in users_done:
                continue
            users_done.add(login)

            # Detalle del usuario
            user_detail = get_user_detail(login)
            if user_detail:
                all_users.append(user_detail)

            # Repositorios del usuario
            repos = get_user_repos(login)
            newly_added = len(repos)
            all_repos.extend(repos)
            repo_bar.update(newly_added)

            time.sleep(0.1)   # cortesía con la API

    # ── PASO 3: Guardar resultados ───────────────────────────────────────────
    print(f"\n\n✅ Extracción lista. Total repositorios: {len(all_repos):,}")

    # repositories.csv
    repos_df = pd.DataFrame(all_repos).drop_duplicates(subset=["id"])
    repos_df.to_csv(REPOS_CSV, index=False, encoding="utf-8")
    print(f"💾 {len(repos_df):,} repositorios guardados en: {REPOS_CSV}")

    # users.csv (actualizado con detalles enriquecidos)
    if all_users:
        users_df = pd.DataFrame(all_users).drop_duplicates(subset=["login"])
        users_df.to_csv(USERS_CSV, index=False, encoding="utf-8")
        print(f"💾 {len(users_df):,} usuarios actualizados en: {USERS_CSV}")

    # ── PASO 4: Resumen ──────────────────────────────────────────────────────
    print("\n📊 RESUMEN")
    print("-" * 40)
    print(f"  Repositorios totales : {len(repos_df):,}")
    print(f"  Repositorios únicos  : {repos_df['id'].nunique():,}")
    print(f"  Usuarios cubiertos   : {repos_df['owner_login'].nunique():,}")
    print(f"  Lenguajes distintos  : {repos_df['language'].replace('', 'Unknown').nunique():,}")

    top_lang = repos_df["language"].replace("", "Unknown").value_counts().head(5)
    print("\n  Top 5 lenguajes:")
    for lang, count in top_lang.items():
        print(f"    {lang:<20} {count:>5} repos")

    if len(repos_df) < TARGET_REPOS:
        print(f"\n⚠️  Solo se obtuvieron {len(repos_df):,} repos (meta: {TARGET_REPOS:,}).")
        print("   Esto puede ocurrir si los usuarios de Perú tienen pocos repos públicos.")
        print("   El archivo está igualmente guardado y listo para clasificar.")
    else:
        print(f"\n🎉 ¡Meta de {TARGET_REPOS:,} repositorios alcanzada!")

    print(f"\n⏭️  Siguiente paso: clasificar con IndustryClassifier")
    print(f"   python src/agents/insights_agent.py")


if __name__ == "__main__":
    main()