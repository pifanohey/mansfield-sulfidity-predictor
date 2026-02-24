@echo off
echo Starting Sulfidity Predictor...
echo.
cd /d "%~dp0.."
python -m streamlit run sulfidity_predictor/app/streamlit_app.py --server.port 8501
pause
