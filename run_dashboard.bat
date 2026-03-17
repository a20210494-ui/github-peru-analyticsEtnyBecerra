@echo off
echo Iniciando el Dashboard de Streamlit...
call venv\Scripts\activate.bat
streamlit run app/main.py
pause
