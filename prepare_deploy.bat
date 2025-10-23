@echo off
REM Script para dar permisos de ejecución al build.sh en Windows
REM Ejecuta este script antes de hacer push a GitHub

echo.
echo ========================================
echo   Preparando archivos para Render
echo ========================================
echo.

echo [1/3] Instalando dependencias actualizadas...
pip install -r requirements.txt

echo.
echo [2/3] Verificando archivos de despliegue...
if exist Procfile (
    echo ✓ Procfile encontrado
) else (
    echo ✗ ERROR: Falta Procfile
)

if exist build.sh (
    echo ✓ build.sh encontrado
) else (
    echo ✗ ERROR: Falta build.sh
)

if exist runtime.txt (
    echo ✓ runtime.txt encontrado
) else (
    echo ✗ ERROR: Falta runtime.txt
)

echo.
echo [3/3] Generando claves secretas...
python generate_secrets.py

echo.
echo ========================================
echo   ✓ Preparación completada
echo ========================================
echo.
echo Siguiente paso:
echo   git add .
echo   git commit -m "Preparar para despliegue en Render"
echo   git push origin main
echo.
pause
