"""
Script para generar claves secretas seguras para Django y JWT
Ejecuta este script y copia las claves generadas a tus variables de entorno en Render
"""

import secrets

print("=" * 70)
print("🔐 GENERADOR DE CLAVES SECRETAS PARA RENDER")
print("=" * 70)
print()

print("📋 Copia estas claves y agrégalas a las variables de entorno en Render:")
print()

print("1️⃣  SECRET_KEY para Django:")
print("-" * 70)
secret_key = secrets.token_urlsafe(50)
print(secret_key)
print()

print("2️⃣  JWT_SECRET_KEY para JWT:")
print("-" * 70)
jwt_key = secrets.token_urlsafe(50)
print(jwt_key)
print()

print("=" * 70)
print("⚠️  IMPORTANTE:")
print("   - NO compartas estas claves públicamente")
print("   - NO las subas a GitHub")
print("   - Úsalas SOLO en las variables de entorno de Render")
print("   - Genera claves DIFERENTES para desarrollo y producción")
print("=" * 70)
