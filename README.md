# 🇵🇪 Peru Tech Insights: Analizador del Ecosistema GitHub

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![OpenAI](https://img.shields.io/badge/AI-GPT--4-green.svg)](https://openai.com/)

## Sección 1: Descripción del Proyecto
Este proyecto es una plataforma avanzada de análisis de datos orientada a mapear y comprender el ecosistema de desarrolladores de software en Perú. Utilizando la API de GitHub y modelos de lenguaje de gran escala (GPT-4), el sistema extrae repositorios, calcula métricas de impacto, clasifica proyectos por industria y ofrece una interfaz interactiva (Streamlit) y un agente de IA para responder preguntas en tiempo real sobre el talento tecnológico nacional.

### 🌌 Huevo de Pascua: Antigravedad
Como parte del desarrollo, se ha incluido una referencia visual al módulo `antigravity`, simbolizando el impulso y la elevación del ecosistema tech peruano.

![Antigravity Easter Egg](antigravity_easter_egg_1773351491379.png)

---

## Sección 2: Hallazgos Clave
1.  **Dominio de Web & Mobile**: La gran mayoría de los repositorios clasificados pertenecen al sector de Información y Comunicaciones (Código ISIC J), con un fuerte enfoque en desarrollo full-stack.
2.  **Top 3 Lenguajes**: 
    - **JavaScript**: Lidera con 96 repositorios (aprox. 9% de la muestra).
    - **Java**: Segundo lugar con 87 repositorios, dominante en entornos corporativos.
    - **Python**: Tercer lugar con 84 repositorios, con crecimiento en Ciencia de Datos.
3.  **Distribución Industrial**: Se observa una alta densidad de proyectos orientados a Servicios de Tecnología de la Información, seguidos minoritariamente por soluciones para E-commerce y Fintech.
4.  **Impacto vs Seguidores**: Los desarrolladores peruanos con mayor `impact_score` no siempre son los que tienen más seguidores, sino los que mantienen una relación equilibrada entre repositorios públicos activos y estrellas recibidas.
5.  **Actividad Reciente**: Más del 40% de los repositorios extraídos muestran actualizaciones en el último año, indicando una comunidad vibrante y en crecimiento.

---

## Sección 3: Recopilación de Datos
-   **Volumen**: Se recopilaron datos detallados de **1,071 repositorios** de desarrolladores basados en Perú.
-   **Periodo**: Datos extraídos el 12 de marzo de 2026, capturando el estado actual del mercado.
-   **Limitación de Velocidad (Rate Limiting)**:
    -   El sistema utiliza un `GITHUB_TOKEN` para permitir hasta **5,000 peticiones por hora**.
    -   Implementa un manejo automático de errores 403 y esperas programadas (exponential back-off) para asegurar la integridad de la descarga masiva sin bloqueos.

---

## Sección 4: Características del Panel (Dashboard)
-   **📊 Telemetría en Vivo**: Gráficos interactivos (Plotly) de lenguajes y rankings de desarrolladores.
-   **👤 Perfiles de Desarrolladores**: Tabla enriquecida con métricas de impacto y filtros de búsqueda.
-   **🤖 Chat de IA Integrado**: Interfaz para consultar los datos usando lenguaje natural.
-   **📥 Exportación**: Botón para descargar el dataset procesado en formato CSV.

*(Nota: Ejecute `streamlit run app/main.py` para visualizar las páginas: Dashboard, AI Chat y Explorador).*

---

## Sección 5: Instalación
1.  **Clonar y venv**:
    ```bash
    git clone [url-del-repo]
    python -m venv venv
    ./venv/Scripts/activate
    ```
2.  **Dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configuración de Tokens (`.env`)**:
    Cree un archivo `.env` en la raíz con lo siguiente:
    - `GITHUB_TOKEN=tu_token_personal`: [Generar aquí](https://github.com/settings/tokens).
    - `OPENAI_API_KEY=tu_clave_secreta`: Necesaria para la clasificación de industria y el agente de IA.

---

## Sección 6: Uso
-   **Extracción de Datos**:
    `python scripts/extract_data.py` (Descarga los >1,000 repositorios).
-   **Cálculo de Métricas**:
    `python src/metrics/user_metrics.py` (Genera el archivo `users_enriched.csv`).
-   **Iniciar Dashboard**:
    `streamlit run app/main.py`

---

## Sección 7: Documentación de Métricas
### Métricas de Usuario
-   **Impact Score**: `(Seguidores × 0.5) + (Estrellas Totales × 0.3) + (Repos Públicos × 0.2)`. Mide la influencia y producción real.
-   **Activity Index**: `log1p(repos) × log1p(followers)`. Penaliza cuentas con muchos repositorios pero sin tracción social.
-   **Impact Percentile**: Ranking relativo de un desarrollador frente al resto del ecosistema local.

### Métricas del Ecosistema
-   **Language Distribution**: Porcentaje de uso por lenguaje sobre el total de repositorios.
-   **Industry Density**: Clasificación ISIC basada en la descripción y tópicos del proyecto mediante GPT-4.

---

## Sección 8: Documentación del Agente de IA
### Arquitectura
El agente utiliza el modelo **GPT-4o/Turbo** con una arquitectura de **Tool-Calling**. El agente no solo "habla", sino que tiene acceso a funciones de Python que consultan los DataFrames de Pandas en tiempo real.

### Herramientas (Tools)
1.  `get_top_developers`: Filtra y ordena a los mejores talentos por cualquier métrica.
2.  `get_industry_stats`: Resume la distribución de categorías industriales.
3.  `get_language_stats`: Analiza los lenguajes predominantes en la muestra.

### Ejemplo de Ejecución
> **Usuario**: "¿Quién es el desarrollador con más impacto en Lima que use Python?"
> **Agente**: [Llamada a `get_top_developers(metric='impact_score')`] -> "El desarrollador líder es [Name] con un puntaje de X..."

---

## Sección 9: Limitaciones
1.  **Sesgo de Ubicación**: Basado únicamente en el campo "Location" del perfil de GitHub. Muchos desarrolladores peruanos no especifican su ubicación o trabajan remotamente para empresas extranjeras.
2.  **Limitación de Clasificación**: La clasificación por industria depende de la calidad de la `description` del repositorio. Repositorios sin descripción son clasificados con "confianza baja".
3.  **API Rate Limits**: A pesar del uso de tokens, la clasificación masiva de miles de repositorios por GPT-4 puede ser costosa y lenta debido a los límites de tokens por minuto (TPM) de OpenAI.

---

## Sección 10: Información del Autor
-   **Nombre**: [Tu Nombre / Estudiante]
-   **Curso**: Desarrollo de Agentes de IA / Tarea 2
-   **Fecha**: 12 de marzo de 2026
