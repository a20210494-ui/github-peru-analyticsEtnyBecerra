import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import json
from datetime import datetime

# ── Path Setup ─────────────────────────────────────────────────────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.insights_agent import InsightsAgent

# ── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="GitHub Peru - Insights Dashboard",
    page_icon="🇵🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Premium Look ───────────────────────────────────────────
st.markdown("""
    <style>
    /* Gradient Background for headers */
    .main {
        background-color: #0e1117;
    }
    .stAppHeader {
        background-color: rgba(14, 17, 23, 0.8);
    }
    
    /* Custom Card Style */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #ff4b4b;
    }
    
    /* Heading style */
    h1, h2, h3 {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-image: linear-gradient(#2e7bcf, #2e7bcf);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ── Data Loading & State ───────────────────────────────────────────────────
@st.cache_resource(show_spinner="Cargando Cerebro de IA...")
def get_agent(data_version=0):
    return InsightsAgent(data_dir=os.path.join(_ROOT, "data", "processed"))

def load_data():
    base_path = os.path.join(_ROOT, "data", "processed")
    users_path = os.path.join(base_path, "users_enriched.csv")
    repos_path = os.path.join(base_path, "repositories.csv")
    
    users_df = pd.read_csv(users_path) if os.path.exists(users_path) else pd.DataFrame()
    repos_df = pd.read_csv(repos_path) if os.path.exists(repos_path) else pd.DataFrame()
    
    return users_df, repos_df

# ── App Layout ─────────────────────────────────────────────────────────────

def main():
    if "data_version" not in st.session_state:
        st.session_state.data_version = 0
        
    agent = get_agent(st.session_state.data_version)
    users_df, repos_df = load_data()

    # Sidebar Navigation
    with st.sidebar:
        st.image("https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png", width=80)
        st.title("GitHub Perú")
        st.caption("Ecosistema de Desarrolladores")
        st.divider()
        
        page = st.radio(
            "Navegación",
            ["📊 Dashboard", "🤖 AI Agent Chat", "🔍 Explorador de Datos"]
        )
        
        st.divider()
        if st.button("🔄 Recargar Datos"):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.session_state.data_version += 1
            st.rerun()

    # ── Page: Dashboard ────────────────────────────────────────────────────
    if page == "📊 Dashboard":
        st.title("🚀 Dashboard de Insights")
        st.markdown("Análisis avanzado del talento tecnológico en el Perú.")

        # Top Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        total_repos = len(repos_df)
        total_users = len(users_df)
        top_lang = repos_df['language'].mode()[0] if not repos_df.empty else "N/A"
        avg_impact = users_df['impact_score'].mean() if not users_df.empty else 0

        with col1:
            st.markdown(f'<div class="metric-card"><h3>📦 Repositorios</h3><h2>{total_repos:,}</h2></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><h3>👥 Desarrolladores</h3><h2>{total_users:,}</h2></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><h3>💻 Top Lenguaje</h3><h2>{top_lang}</h2></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card"><h3>⚡ Impacto Promedio</h3><h2>{avg_impact:.1f}</h2></div>', unsafe_allow_html=True)

        st.divider()

        # Graphs Section
        g1, g2 = st.columns(2)

        with g1:
            st.subheader("🌐 Distribución de Lenguajes")
            if not repos_df.empty:
                lang_counts = repos_df['language'].fillna("Unknown").value_counts().head(10)
                fig_lang = px.pie(
                    values=lang_counts.values,
                    names=lang_counts.index,
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_lang.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_lang, use_container_width=True)

        with g2:
            st.subheader("📈 Top Desarrolladores por Impacto")
            if not users_df.empty:
                top_devs = users_df.sort_values('impact_score', ascending=False).head(10)
                fig_devs = px.bar(
                    top_devs,
                    x='impact_score',
                    y='login',
                    orientation='h',
                    color='impact_score',
                    labels={'impact_score': 'Impact Score', 'login': 'Usuario'},
                    color_continuous_scale='Reds'
                )
                fig_devs.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_devs, use_container_width=True)

    # ── Page: AI Agent Chat ────────────────────────────────────────────────
    elif page == "🤖 AI Agent Chat":
        st.title("🤖 Consultas Inteligentes")
        st.markdown("Pregunta cualquier cosa sobre los desarrolladores peruanos.")

        # Data Status Indicator
        users_ready = not users_df.empty
        repos_ready = not repos_df.empty
        class_path = os.path.join(_ROOT, "data", "processed", "classifications.csv")
        class_ready = os.path.exists(class_path)
        
        with st.expander("📡 Estado de los Datos", expanded=not (users_ready and class_ready)):
            c1, c2, c3 = st.columns(3)
            c1.metric("Usuarios", "✅ Listo" if users_ready else "❌ Faltan Datos")
            c2.metric("Repositorios", "✅ Listo" if repos_ready else "❌ Faltan Datos")
            c3.metric("Clasificación", "✅ Listo" if class_ready else "⏳ En Proceso")
            
            if not class_ready:
                st.info("💡 La clasificación por industria se está procesando en segundo plano. Algunas preguntas podrían no tener respuesta completa aún.")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Suggested Questions
        st.subheader("💡 Preguntas Sugeridas")
        cols = st.columns(2)
        suggestions = [
            "¿Cuáles son los lenguajes de programación más populares en Perú?",
            "¿Qué sectores industriales están más representados?",
            "¿Quiénes son los 5 desarrolladores con mayor impacto?",
            "¿En qué ciudades hay más desarrolladores?",
        ]
        
        for i, hint in enumerate(suggestions):
            if cols[i % 2].button(hint, key=f"hint_{i}", use_container_width=True):
                st.session_state.pending_prompt = hint

        st.divider()

        # Display history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Input logic
        prompt = st.chat_input("Ej: ¿Quiénes son los expertos en Python en Lima?")
        
        # Check for pending prompt from buttons
        if "pending_prompt" in st.session_state:
            prompt = st.session_state.pop("pending_prompt")
            st.rerun() # Rerun to show the prompt in the chat immediately

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analizando datos..."):
                    try:
                        response = agent.ask(prompt)
                    except Exception as e:
                        response = f"❌ Error al consultar al agente: {str(e)}"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            # Botón para limpiar chat
            if st.button("🗑️ Limpiar Historial"):
                st.session_state.messages = []
                st.rerun()

    # ── Page: Explorador de Datos ──────────────────────────────────────────
    elif page == "🔍 Explorador de Datos":
        st.title("🔍 Tabla de Desarrolladores")
        st.markdown("Filtra y explora los datos crudos.")
        
        if not users_df.empty:
            search = st.text_input("Buscar por nombre o login")
            filtered_df = users_df
            if search:
                filtered_df = users_df[
                    users_df['login'].str.contains(search, case=False, na=False) |
                    users_df['name'].str.contains(search, case=False, na=False)
                ]
            
            st.dataframe(
                filtered_df.sort_values('impact_score', ascending=False),
                column_config={
                    "login": "Usuario",
                    "name": "Nombre",
                    "followers": st.column_config.NumberColumn("Seguidores", format="%d 👤"),
                    "public_repos": "Repos Públicos",
                    "impact_score": st.column_config.ProgressColumn("Puntaje de Impacto", min_value=0, max_value=users_df['impact_score'].max()),
                },
                use_container_width=True
            )
            
            st.download_button(
                "📥 Descargar CSV",
                filtered_df.to_csv(index=False).encode('utf-8'),
                "peru_devs_export.csv",
                "text/csv"
            )
        else:
            st.warning("No hay datos de usuarios disponibles. Ejecuta el pipeline primero.")

if __name__ == "__main__":
    main()
