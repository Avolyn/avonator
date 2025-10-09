@echo off
echo 🔐 Generated Secure Secrets for GitHub Repository
echo ============================================================
echo.
echo 📋 Copy these values to your GitHub Secrets:
echo.

REM Generate API Key
set /a "rand1=%random%"
set /a "rand2=%random%"
set /a "rand3=%random%"
set /a "rand4=%random%"
set API_KEY=gr_%rand1%%rand2%%rand3%%rand4%

REM Generate JWT Secret
set /a "jwt1=%random%"
set /a "jwt2=%random%"
set /a "jwt3=%random%"
set /a "jwt4=%random%"
set JWT_SECRET=%jwt1%%jwt2%%jwt3%%jwt4%

REM Generate Grafana Password
set /a "graf1=%random%"
set /a "graf2=%random%"
set GRAFANA_PASSWORD=%graf1%%graf2%

echo GUARDRAILS_API_KEY = %API_KEY%
echo JWT_SECRET = %JWT_SECRET%
echo GRAFANA_PASSWORD = %GRAFANA_PASSWORD%
echo GRAFANA_SECRET_KEY = %JWT_SECRET%
echo.
echo 🐳 Docker Hub Credentials:
echo (You need to provide these manually)
echo DOCKER_USERNAME = your-dockerhub-username
echo DOCKER_PASSWORD = your-dockerhub-password-or-token
echo.
echo 📝 Instructions:
echo 1. Go to your GitHub repository settings
echo 2. Navigate to 'Secrets and variables' ^> 'Actions'
echo 3. Click 'New repository secret' for each value above
echo 4. Use the generated values as the secret values
echo.
echo ⚠️  Important Security Notes:
echo - Never commit these secrets to your repository
echo - Use strong, unique passwords
echo - Rotate secrets regularly
echo - Consider using GitHub's encrypted secrets for sensitive data
pause
