"""
insights_agent.py
==================
Agente de IA que combina GPT-4 con herramientas de análisis de datos
para responder preguntas en lenguaje natural sobre el ecosistema de
desarrolladores de GitHub en Perú.

Flujo completo
--------------
1. run_pipeline()  → calcula métricas (UserMetricsCalculator) y clasifica
                     repositorios (IndustryClassifier), guarda CSVs.
2. ask(question)   → agente conversacional con tool-calling que consulta
                     los datos procesados para responder preguntas.
3. main()          → CLI interactiva para explorar los datos.

Uso rápido
----------
    python src/agents/insights_agent.py
"""

import os
import sys
import json
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# ── Asegurar que el directorio raíz esté en el path ────────────────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.metrics.user_metrics import UserMetricsCalculator
from src.classification.industry_classifier import IndustryClassifier

load_dotenv()


class InsightsAgent:
    """
    Agente conversacional que responde preguntas sobre el ecosistema
    de desarrolladores peruanos en GitHub usando GPT-4 + tool-calling.
    """

    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = data_dir
        self.client = OpenAI()

        # ── Cargar datos procesados ─────────────────────────────────────────
        self.users_df = pd.DataFrame()
        self.class_df = pd.DataFrame()
        self.reload_data()

        # ── Definición de herramientas para GPT-4 ──────────────────────────
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_top_developers",
                    "description": (
                        "Obtiene los mejores desarrolladores de Perú según una métrica "
                        "específica. Útil para rankingss, comparaciones y liderazgo."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metric": {
                                "type": "string",
                                "enum": [
                                    "impact_score",
                                    "followers",
                                    "total_stars_received",
                                    "public_repos",
                                    "activity_index",
                                ],
                                "description": "La métrica para ordenar a los desarrolladores.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Número de desarrolladores a retornar (ej. 5, 10).",
                            },
                        },
                        "required": ["metric", "limit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_industry_stats",
                    "description": (
                        "Obtiene un resumen de cuántos repositorios hay por cada industria. "
                        "Útil para analizar sectores dominantes."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_language_stats",
                    "description": (
                        "Obtiene la distribución de lenguajes de programación en los "
                        "repositorios clasificados. Útil para analizar tendencias tecnológicas."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "top_n": {
                                "type": "integer",
                                "description": "Cuántos lenguajes mostrar (ej. 10).",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_profile",
                    "description": (
                        "Obtiene el perfil detallado de un desarrollador específico por su login de GitHub. "
                        "Útil para ver métricas individuales como impacto, seguidores y actividad."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "login": {
                                "type": "string",
                                "description": "El nombre de usuario (login) en GitHub.",
                            }
                        },
                        "required": ["login"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_location_stats",
                    "description": (
                        "Obtiene estadísticas sobre la ubicación geográfica de los desarrolladores. "
                        "Útil para ver en qué ciudades o regiones de Perú se concentra el talento."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        ]

    def reload_data(self):
        """Recarga los archivos CSV de la carpeta de datos."""
        users_path = os.path.join(self.data_dir, "users_enriched.csv")
        class_path = os.path.join(self.data_dir, "classifications.csv")
        
        if os.path.exists(users_path):
            try:
                self.users_df = pd.read_csv(users_path)
                print(f"✅ Usuarios cargados: {len(self.users_df)} registros")
            except Exception as e:
                print(f"⚠️ Error cargando {users_path}: {e}")
        
        if os.path.exists(class_path):
            try:
                self.class_df = pd.read_csv(class_path)
                print(f"✅ Clasificaciones cargadas: {len(self.class_df)} registros")
            except Exception as e:
                print(f"⚠️ Error cargando {class_path}: {e}")

    # ──────────────────────────────────────────────────────────────────────
    # Implementación de herramientas (lógica de datos)
    # ──────────────────────────────────────────────────────────────────────

    def _get_top_developers(self, metric: str, limit: int) -> list:
        """Devuelve los top N desarrolladores para la métrica dada."""
        print(f"🛠️  Herramienta: _get_top_developers(metric={metric}, limit={limit})")
        if self.users_df.empty:
            return {"error": "No hay datos de usuarios. Ejecuta run_pipeline() primero."}

        if metric not in self.users_df.columns:
            # Intentar con columna aproximada
            available = self.users_df.select_dtypes(include="number").columns.tolist()
            return {"error": f"Métrica '{metric}' no disponible. Disponibles: {available}"}

        cols = ["login", "name", metric]
        optional = ["followers", "public_repos", "total_stars_received", "activity_index"]
        for col in optional:
            if col in self.users_df.columns and col != metric:
                cols.append(col)

        top = self.users_df.nlargest(limit, metric)
        return top[cols].to_dict("records")

    def _get_industry_stats(self) -> dict:
        """Cuenta repositorios por industria."""
        print("🛠️  Herramienta: _get_industry_stats()")
        if self.class_df.empty:
            return {"error": "No hay datos de clasificaciones. Ejecuta run_pipeline() primero."}

        counts = self.class_df["industry_name"].value_counts()
        total = counts.sum()
        result = {
            "total_repositories": int(total),
            "by_industry": counts.to_dict(),
            "top_industry": counts.index[0] if len(counts) > 0 else "N/A",
        }
        return result

    def _get_language_stats(self, top_n: int = 10) -> dict:
        """Distribución de lenguajes de programación."""
        print(f"🛠️  Herramienta: _get_language_stats(top_n={top_n})")
        if self.class_df.empty:
            return {"error": "No hay datos de clasificaciones. Ejecuta run_pipeline() primero."}

        if "language" not in self.class_df.columns:
            return {"error": "Columna 'language' no encontrada en classifications.csv"}

        lang_counts = (
            self.class_df["language"]
            .dropna()
            .replace("", "Unknown")
            .value_counts()
            .head(top_n)
        )
        return {
            "top_languages": lang_counts.to_dict(),
            "total_repos_with_language": int(lang_counts.sum()),
        }

    def _get_user_profile(self, login: str) -> dict:
        """Devuelve el perfil detallado de un usuario."""
        print(f"🛠️  Herramienta: _get_user_profile(login={login})")
        if self.users_df.empty:
            return {"error": "No hay datos de usuarios."}

        user_data = self.users_df[self.users_df["login"].str.lower() == login.lower()]
        if user_data.empty:
            return {"error": f"Usuario '{login}' no encontrado en la base de datos."}

        # Convertir a dict y limpiar valores nulos para JSON
        profile = user_data.iloc[0].to_dict()
        return {k: (v if pd.notnull(v) else None) for k, v in profile.items()}

    def _get_location_stats(self) -> dict:
        """Estadísticas por ubicación."""
        print("🛠️  Herramienta: _get_location_stats()")
        if self.users_df.empty:
            return {"error": "No hay datos de usuarios."}

        if "location" not in self.users_df.columns:
            return {"error": "Columna 'location' no encontrada."}

        loc_counts = self.users_df["location"].value_counts().head(10)
        return {
            "top_locations": loc_counts.to_dict(),
            "total_users_with_location": int(len(self.users_df[self.users_df["location"].notnull()])),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Motor del agente (GPT-4 + tool-calling)
    # ──────────────────────────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """
        Envía una pregunta en lenguaje natural al agente y retorna
        la respuesta generada por GPT-4 usando los datos del proyecto.

        Args:
            question: Pregunta en español o inglés.

        Returns:
            Respuesta en texto (Markdown).
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un Analista de Datos Experto en IA para un proyecto sobre el ecosistema "
                    "de desarrolladores de GitHub en Perú. Tu trabajo es responder preguntas sobre "
                    "los datos usando las herramientas proporcionadas.\n\n"
                    "Capacidades:\n"
                    "- Rankings de desarrolladores (`get_top_developers`)\n"
                    "- Perfiles individuales detallados (`get_user_profile`)\n"
                    "- Estadísticas de industrias/sectores (`get_industry_stats`)\n"
                    "- Distribución de lenguajes (`get_language_stats`)\n"
                    "- Distribución geográfica/ciudades (`get_location_stats`)\n\n"
                    "Sé analítico, directo y usa formato Markdown. Si una herramienta devuelve "
                    "un error indicando que los datos no están disponibles, explícale al usuario "
                    "que la clasificación de repositorios sigue en proceso en segundo plano."
                ),
            },
            {"role": "user", "content": question},
        ]

        # ── Bucle ReAct del agente ──────────────────────────────────────────
        while True:
            # Si los datos están vacíos, intentar recargar por si el pipeline avanzó
            if self.users_df.empty or self.class_df.empty:
                self.reload_data()

            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.2,
            )

            message = response.choices[0].message

            if message.tool_calls:
                # ── BUG FIX: añadir el mensaje del asistente UNA SOLA VEZ
                #    antes del loop de tool_calls, no dentro de él.
                messages.append(message)

                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    # Ejecutar la herramienta correspondiente
                    if function_name == "get_top_developers":
                        result = self._get_top_developers(
                            metric=arguments["metric"],
                            limit=arguments["limit"],
                        )
                    elif function_name == "get_industry_stats":
                        result = self._get_industry_stats()
                    elif function_name == "get_language_stats":
                        result = self._get_language_stats(
                            top_n=arguments.get("top_n", 10)
                        )
                    elif function_name == "get_user_profile":
                        result = self._get_user_profile(login=arguments["login"])
                    elif function_name == "get_location_stats":
                        result = self._get_location_stats()
                    else:
                        result = {"error": f"Herramienta desconocida: {function_name}"}

                    # Devolver el resultado de la herramienta al agente
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
            else:
                # El agente ya tiene suficiente información → respuesta final
                return message.content

    # ──────────────────────────────────────────────────────────────────────
    # Orquestador del pipeline completo
    # ──────────────────────────────────────────────────────────────────────

    def run_pipeline(
        self,
        users_csv: str = "data/processed/users.csv",
        repos_csv: str = None,
        output_dir: str = "data/processed",
        classify_limit: int = None,
        fetch_stars: bool = False,
    ) -> dict:
        """
        Ejecuta el pipeline de procesamiento completo:
          1. Calcula métricas de usuario (UserMetricsCalculator)
          2. Clasifica repositorios por industria (IndustryClassifier) — opcional
          3. Recarga los DataFrames del agente con los nuevos datos

        Args:
            users_csv:       CSV de usuarios generado por extract_data.py.
            repos_csv:       CSV de repositorios para clasificar (opcional).
            output_dir:      Carpeta donde guardar los CSVs resultantes.
            classify_limit:  Limitar la clasificación a los primeros N repos (pruebas).
            fetch_stars:     Si True, consulta GitHub API para estrellas reales.

        Returns:
            dict con rutas de los archivos generados.
        """
        os.makedirs(output_dir, exist_ok=True)
        output_files = {}

        # ── Paso 1: Métricas de usuarios ───────────────────────────────────
        print("\n" + "=" * 60)
        print("PASO 1/2 — Calculando métricas de usuarios")
        print("=" * 60)
        users_output = os.path.join(output_dir, "users_enriched.csv")
        calc = UserMetricsCalculator(data_dir=output_dir)
        self.users_df = calc.process_users_csv(
            input_path=users_csv,
            output_path=users_output,
            fetch_stars=fetch_stars,
        )
        output_files["users_enriched"] = users_output
        print(f"✅ Métricas calculadas para {len(self.users_df)} usuarios.")

        # ── Paso 2: Clasificación por industria (solo si se provee repos_csv) ──
        if repos_csv and os.path.exists(repos_csv):
            print("\n" + "=" * 60)
            print("PASO 2/2 — Clasificando repositorios por industria (GPT-4)")
            print("=" * 60)
            class_output = os.path.join(output_dir, "classifications.csv")
            clf = IndustryClassifier()
            self.class_df = clf.run(
                repos_csv_path=repos_csv,
                output_csv_path=class_output,
                limit=classify_limit,
            )
            output_files["classifications"] = class_output
            print(f"✅ {len(self.class_df)} repositorios clasificados.")
        else:
            print("\n⏩ Paso 2 omitido (no se proporcionó repos_csv o el archivo no existe).")

        print("\n🎉 Pipeline completado. El agente está listo para responder preguntas.")
        return output_files

    # ──────────────────────────────────────────────────────────────────────
    # Resumen rápido de los datos disponibles
    # ──────────────────────────────────────────────────────────────────────

    def summary(self) -> str:
        """Devuelve un resumen formateado de los datos cargados en el agente."""
        lines = ["## 📊 Resumen del Agente de Insights\n"]

        if not self.users_df.empty:
            lines.append(f"- **Usuarios**: {len(self.users_df)} desarrolladores peruanos")
            top = self.users_df.nlargest(3, "impact_score") if "impact_score" in self.users_df.columns else self.users_df.head(3)
            lines.append(f"- **Top 3 por impacto**: {', '.join(top['login'].tolist())}")
        else:
            lines.append("- ⚠️ Sin datos de usuarios (ejecuta `run_pipeline()`)")

        if not self.class_df.empty:
            lines.append(f"- **Repositorios clasificados**: {len(self.class_df)}")
            top_ind = self.class_df["industry_name"].value_counts().index[0]
            lines.append(f"- **Industria dominante**: {top_ind}")
        else:
            lines.append("- ⚠️ Sin datos de clasificación (ejecuta `run_pipeline()` con `repos_csv`)")

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# CLI interactiva
# ──────────────────────────────────────────────────────────────────────────────

def main():
    """Punto de entrada para la CLI interactiva del agente."""
    print("\n" + "=" * 60)
    print("🤖  INSIGHTS AGENT — Ecosistema GitHub Perú")
    print("=" * 60)
    print("Escribe tu pregunta en lenguaje natural.")
    print("Comandos especiales: 'pipeline', 'summary', 'salir'\n")

    agent = InsightsAgent(data_dir="data/processed")
    print()
    print(agent.summary())
    print()

    while True:
        try:
            question = input("💬 Tu pregunta: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 ¡Hasta luego!")
            break

        if not question:
            continue

        if question.lower() in ("salir", "exit", "quit", "q"):
            print("👋 ¡Hasta luego!")
            break

        if question.lower() == "summary":
            print(agent.summary())
            continue

        if question.lower() == "pipeline":
            agent.run_pipeline(
                users_csv="data/processed/users.csv",
                output_dir="data/processed",
            )
            continue

        print("\n🔍 Consultando al agente…\n")
        try:
            answer = agent.ask(question)
            print(answer)
        except Exception as exc:
            print(f"❌ Error: {exc}")
        print()


if __name__ == "__main__":
    main()