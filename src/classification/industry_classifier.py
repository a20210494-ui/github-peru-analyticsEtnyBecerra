import os
import json
import time
import pandas as pd
from openai import OpenAI, RateLimitError, APIError
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

# Cargamos las variables del .env automáticamente al importar el módulo
load_dotenv()


class IndustryClassifier:
    """
    Clasifica repositorios de GitHub en categorías industriales ISIC
    usando GPT-4 con reintentos automáticos y gestión de rate-limits.
    """

    def __init__(self):
        self.client = OpenAI()  # Usa OPENAI_API_KEY del .env
        self.industries = {
            "A": "Agriculture, forestry and fishing",
            "B": "Mining and quarrying",
            "C": "Manufacturing",
            "D": "Electricity, gas, steam supply",
            "E": "Water supply; sewerage",
            "F": "Construction",
            "G": "Wholesale and retail trade",
            "H": "Transportation and storage",
            "I": "Accommodation and food services",
            "J": "Information and communication",
            "K": "Financial and insurance activities",
            "L": "Real estate activities",
            "M": "Professional, scientific activities",
            "N": "Administrative and support activities",
            "O": "Public administration and defense",
            "P": "Education",
            "Q": "Human health and social work",
            "R": "Arts, entertainment and recreation",
            "S": "Other service activities",
            "T": "Activities of households",
            "U": "Extraterritorial organizations",
        }
        # Fallback cuando la API falla definitivamente
        self._fallback = {
            "industry_code": "J",
            "industry_name": "Information and communication",
            "confidence": "low",
            "reasoning": "Classification failed – defaulted to Information and communication.",
        }

    # -----------------------------------------------------------------
    # Llamada individual a la API (con reintentos automáticos)
    # -----------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(4),
        reraise=False,
    )
    def _call_api(self, prompt: str) -> dict:
        """Llama a GPT-4 y devuelve un dict JSON. Reintenta hasta 4 veces."""
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at classifying software projects by industry. "
                        "Always respond with valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    # -----------------------------------------------------------------
    # Clasificar un repositorio individual
    # -----------------------------------------------------------------

    def classify_repository(
        self,
        name: str,
        description: str,
        readme: str,
        topics: list,
        language: str,
    ) -> dict:
        """
        Clasifica un repositorio en una categoría industrial.

        Returns:
            dict con claves: industry_code, industry_name, confidence, reasoning
        """
        prompt = f"""Analyze this GitHub repository and classify it into ONE of the following industry categories based on its potential application or the industry it serves.

REPOSITORY INFORMATION:
- Name: {name}
- Description: {description or 'No description'}
- Primary Language: {language or 'Not specified'}
- Topics: {', '.join(topics) if topics else 'None'}
- README (first 2000 chars): {readme[:2000] if readme else 'No README'}

INDUSTRY CATEGORIES:
{json.dumps(self.industries, indent=2)}

INSTRUCTIONS:
1. Analyze the repository's purpose, functionality, and potential use cases
2. Consider what industry would most benefit from or use this software
3. If it's a general-purpose tool (e.g., utility library), classify based on the most likely industry application
4. If truly generic (e.g., "hello world"), use "J" (Information and communication)

Respond in JSON format:
{{
    "industry_code": "X",
    "industry_name": "Full industry name",
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of why this classification was chosen"
}}"""

        try:
            result = self._call_api(prompt)
            # Validación mínima
            if "industry_code" not in result:
                raise ValueError("Respuesta de la API incompleta")
            return result
        except Exception as exc:
            print(f"  ⚠️  Error clasificando '{name}': {exc} — usando fallback.")
            return self._fallback.copy()

    # -----------------------------------------------------------------
    # Clasificar múltiples repositorios
    # -----------------------------------------------------------------

    def batch_classify(
        self, repositories: list, batch_size: int = 10, delay: float = 1.0
    ) -> list:
        """
        Clasifica una lista de repositorios con barra de progreso.

        Args:
            repositories: Lista de dicts con al menos 'id', 'name'.
            batch_size:   Pausa cada N clasificaciones (para no saturar la API).
            delay:        Segundos de pausa entre lotes.

        Returns:
            Lista de dicts con la clasificación de cada repo.
        """
        results = []
        total = len(repositories)

        with tqdm(total=total, desc="🏭 Clasificando repositorios", unit="repo") as pbar:
            for idx, repo in enumerate(repositories):
                # Handle cases where topics might be NaN or float from pandas read_csv
                raw_topics = repo.get("topics", [])
                if isinstance(raw_topics, str):
                    try:
                        import ast
                        topics_list = ast.literal_eval(raw_topics)
                    except (ValueError, SyntaxError):
                        topics_list = [raw_topics]
                elif isinstance(raw_topics, (list, tuple)):
                    topics_list = list(raw_topics)
                else:
                    topics_list = []

                classification = self.classify_repository(
                    name=repo.get("name", ""),
                    description=repo.get("description", ""),
                    readme=repo.get("readme", ""),
                    topics=topics_list,
                    language=repo.get("language", ""),
                )

                results.append(
                    {
                        "repo_id": repo.get("id", idx),
                        "repo_name": repo.get("name", "unknown"),
                        "owner_login": repo.get("owner", {}).get("login", "") if isinstance(repo.get("owner"), dict) else repo.get("owner_login", ""),
                        "language": repo.get("language", ""),
                        **classification,
                    }
                )

                pbar.update(1)
                pbar.set_postfix({"último": repo.get("name", "")[:25]})

                # Progressive saving to avoid losing data and allow early access
                if (idx + 1) % 20 == 0:
                    temp_df = pd.DataFrame(results)
                    temp_df.to_csv("data/processed/classifications.csv", index=False, encoding="utf-8")

                # Pausa cortés entre lotes para respetar el rate-limit
                if (idx + 1) % batch_size == 0 and (idx + 1) < total:
                    time.sleep(delay)

        return results

    # -----------------------------------------------------------------
    # Guardar/leer resultados
    # -----------------------------------------------------------------

    @staticmethod
    def save_classifications(results: list, output_path: str) -> pd.DataFrame:
        """
        Guarda la lista de clasificaciones en un archivo CSV.

        Returns:
            El DataFrame generado.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"💾 Clasificaciones guardadas en: {output_path}  ({len(df)} filas)")
        return df

    # -----------------------------------------------------------------
    # Método de alto nivel: leer CSV → clasificar → guardar
    # -----------------------------------------------------------------

    def run(
        self,
        repos_csv_path: str,
        output_csv_path: str = "data/processed/classifications.csv",
        limit: int = None,
    ) -> pd.DataFrame:
        """
        Flujo completo: carga un CSV de repositorios, los clasifica y guarda el resultado.

        Args:
            repos_csv_path:  Ruta al CSV con columnas esperadas (name, description, language, …).
            output_csv_path: Dónde guardar el CSV de clasificaciones.
            limit:           Procesar solo los primeros N repositorios (útil para pruebas).

        Returns:
            DataFrame con las clasificaciones.
        """
        print(f"📂 Cargando repositorios desde: {repos_csv_path}")
        repos_df = pd.read_csv(repos_csv_path)

        if limit:
            repos_df = repos_df.head(limit)
            print(f"⚡ Modo prueba: clasificando solo {limit} repositorios.")

        repos = repos_df.to_dict("records")
        print(f"🔍 Total a clasificar: {len(repos)} repositorios\n")

        results = self.batch_classify(repos)
        df = self.save_classifications(results, output_csv_path)

        # Resumen rápido
        print("\n📊 Distribución por industria:")
        print(df["industry_name"].value_counts().to_string())
        return df