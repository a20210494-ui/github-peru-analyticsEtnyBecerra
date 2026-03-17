from datetime import datetime, timedelta
from collections import Counter

class UserMetricsCalculator:
    def __init__(self):
        self.today = datetime.now()

    def calculate_all_metrics(self, user: dict, repos: list[dict], classifications: list[dict]) -> dict:
        """
        Calculate all user-level metrics.
        Args:
            user: User data from GitHub API
            repos: List of user's repositories
            classifications: Industry classifications for repos
        Returns:
            Dictionary with all calculated metrics
        """
        metrics = {}

        # 1. Métricas de Actividad (Activity Metrics)
        metrics["total_repos"] = len(repos)
        metrics["total_stars_received"] = sum(r.get("stargazers_count", 0) for r in repos)
        metrics["total_forks_received"] = sum(r.get("forks_count", 0) for r in repos)
        metrics["avg_stars_per_repo"] = (
            metrics["total_stars_received"] / metrics["total_repos"]
            if metrics["total_repos"] > 0 else 0
        )

        # Manejo de fechas de GitHub (quitando la 'Z' del formato ISO)
        created_at = datetime.fromisoformat(user["created_at"].replace("Z", ""))
        metrics["account_age_days"] = (self.today - created_at).days
        metrics["repos_per_year"] = (
            metrics["total_repos"] / (metrics["account_age_days"] / 365)
            if metrics["account_age_days"] > 0 else 0
        )

        # 2. Métricas de Influencia (Influence Metrics)
        metrics["followers"] = user.get("followers", 0)
        metrics["following"] = user.get("following", 0)
        metrics["follower_ratio"] = (
            metrics["followers"] / metrics["following"]
            if metrics["following"] > 0 else metrics["followers"]
        )
        metrics["h_index"] = self._calculate_h_index(repos)
        metrics["impact_score"] = (
            metrics["total_stars_received"] +
            (metrics["total_forks_received"] * 2) +
            metrics["followers"]
        )

        # 3. Métricas Técnicas (Technical Metrics)
        languages = [r["language"] for r in repos if r.get("language")]
        lang_counts = Counter(languages)
        # Saca los 3 lenguajes más usados
        metrics["primary_languages"] = [l for l, _ in lang_counts.most_common(3)]
        metrics["language_diversity"] = len(set(languages))

        industry_codes = [c.get("industry_code") for c in classifications if c.get("industry_code")]
        metrics["industries_served"] = len(set(industry_codes))
        metrics["primary_industry"] = Counter(industry_codes).most_common(1)[0][0] if industry_codes else None

        # Calidad de la documentación
        repos_with_readme = sum(1 for r in repos if r.get("has_readme", False))
        repos_with_license = sum(1 for r in repos if r.get("license"))
        metrics["has_readme_pct"] = repos_with_readme / len(repos) if repos else 0
        metrics["has_license_pct"] = repos_with_license / len(repos) if repos else 0

        # 4. Métricas de Participación (Engagement Metrics)
        metrics["total_open_issues"] = sum(r.get("open_issues_count", 0) for r in repos)

        if repos:
            # Encuentra la fecha del código más reciente subido
            last_push = max(
                datetime.fromisoformat(r["pushed_at"].replace("Z", ""))
                for r in repos if r.get("pushed_at")
            )
            metrics["days_since_last_push"] = (self.today - last_push).days
            # ¿Es activo? Sí, si subió código en los últimos 90 días
            metrics["is_active"] = metrics["days_since_last_push"] < 90
        else:
            metrics["days_since_last_push"] = None
            metrics["is_active"] = False

        return metrics

    def _calculate_h_index(self, repos: list[dict]) -> int:
        """
        Calculate h-index based on repository stars.
        h-index = h if h repos have at least h stars each.
        """
        stars = sorted([r.get("stargazers_count", 0) for r in repos], reverse=True)
        h = 0
        for i, s in enumerate(stars):
            if s >= i + 1:
                h = i + 1
            else:
                break
        return h
        