import os
import pandas as pd
# Importamos la herramienta que creamos en el Paso 6
from src.extraction.github_client import GitHubClient

def main():
    print("🚀 Iniciando la extracción de datos de GitHub Perú...")
    
    # 1. Asegurarnos de que las carpetas existan
    os.makedirs("data/processed", exist_ok=True)
    
    client = GitHubClient()
    
    # 2. Buscar desarrolladores en Perú (Ejemplo: buscamos a los primeros 50 para probar)
    print("🔍 Buscando desarrolladores en Perú...")
    peru_users = client.search_users("location:peru", limit=50)
    
    if not peru_users:
        print("❌ No se encontraron usuarios o hubo un error con la API.")
        return

    print(f"✅ ¡Se encontraron {len(peru_users)} usuarios!")
    
    # 3. Guardar los usuarios en un CSV
    users_df = pd.DataFrame(peru_users)
    users_csv_path = "data/processed/users.csv"
    users_df.to_csv(users_csv_path, index=False)
    print(f"💾 Usuarios guardados en {users_csv_path}")

    # Aquí luego agregaremos la descarga de repositorios para cada usuario
    print("🎉 Extracción inicial completada.")

if __name__ == "__main__":
    main()