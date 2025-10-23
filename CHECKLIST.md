# ✅ Checklist de Despliegue en Render

## Archivos Creados/Actualizados
- [x] `Procfile` - Comando para ejecutar la aplicación
- [x] `build.sh` - Script de construcción
- [x] `runtime.txt` - Versión de Python
- [x] `requirements.txt` - Dependencias actualizadas (dj-database-url, whitenoise)
- [x] `settings.py` - Configuración para producción
- [x] `.env.example` - Ejemplo de variables de entorno
- [x] `DEPLOYMENT.md` - Guía completa de despliegue
- [x] `.gitignore` - Ya existía y está correctamente configurado

## Antes de Desplegar

### 1. Verificar Variables de Entorno Locales
Asegúrate de tener un archivo `.env` local con:
```env
SECRET_KEY=tu-clave-local
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=nombre_bd
DB_USER=usuario_bd
DB_PASSWORD=contraseña_bd
DB_HOST=localhost
DB_PORT=5432
CLOUDINARY_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret
```

### 2. Probar Localmente con Configuración de Producción
```bash
# En PowerShell
$env:DEBUG="False"
python manage.py collectstatic --no-input
python manage.py check --deploy
gunicorn afrodita.wsgi:application
```

### 3. Preparar Repositorio Git
```bash
git add .
git commit -m "Preparar para despliegue en Render"
git push origin main
```

## Durante el Despliegue en Render

### 1. Base de Datos

**SI USAS NEON (Recomendado):**
- [ ] Obtener connection string desde Neon dashboard
- [ ] Verificar que incluya `?sslmode=require`
- [ ] Verificar que el proyecto Neon esté activo
- [ ] Copiar connection string completa

**SI USAS RENDER POSTGRESQL:**
- [ ] Crear base de datos PostgreSQL en Render
- [ ] Copiar la Internal Database URL
- [ ] Guardar credenciales de forma segura

### 2. Crear Web Service
- [ ] Conectar repositorio GitHub
- [ ] Configurar Build Command: `./build.sh`
- [ ] Configurar Start Command: `gunicorn afrodita.wsgi:application`
- [ ] Seleccionar región (preferiblemente la misma que la BD)

### 3. Configurar Variables de Entorno en Render
- [ ] `SECRET_KEY` - Generar nueva clave segura
- [ ] `JWT_SECRET_KEY` - Generar clave JWT diferente
- [ ] `DEBUG` - Establecer en `False`
- [ ] `ALLOWED_HOSTS` - Agregar dominio de Render
- [ ] `DATABASE_URL` - **Copiar desde Neon** (o Render PostgreSQL si aplica)
- [ ] `CLOUDINARY_NAME` - De tu cuenta Cloudinary
- [ ] `CLOUDINARY_API_KEY` - De tu cuenta Cloudinary
- [ ] `CLOUDINARY_API_SECRET` - De tu cuenta Cloudinary
- [ ] `CLOUDINARY_SECURE` - Establecer en `True`
- [ ] `PYTHON_VERSION` - `3.11.9` (opcional)

### 4. Configurar Cloudinary
- [ ] Crear cuenta en Cloudinary
- [ ] Copiar credenciales del dashboard
- [ ] Agregar a variables de entorno en Render

## Después del Despliegue

### 1. Verificar el Despliegue
- [ ] Abrir URL de Render
- [ ] Verificar que la API responde
- [ ] Revisar logs en Render
- [ ] Probar endpoint de salud/health check

### 2. Configurar CORS (si tienes frontend)
- [ ] Agregar URL del frontend a `CORS_ALLOWED_ORIGINS` en `settings.py`
- [ ] Hacer commit y push

### 3. Crear Superusuario
```bash
# En el Shell de Render
python manage.py createsuperuser
```

### 4. Verificar Accesos
- [ ] Acceder a `/admin/`
- [ ] Acceder a `/api/schema/swagger-ui/`
- [ ] Probar autenticación JWT
- [ ] Verificar subida de imágenes a Cloudinary

## Monitoreo y Mantenimiento

### Revisar Regularmente
- [ ] Logs en Render (pestaña Logs)
- [ ] Uso de base de datos (plan gratuito tiene límites)
- [ ] Rendimiento de la aplicación
- [ ] Seguridad (actualizaciones de Django y dependencias)

### Actualizaciones
- [ ] Configurar auto-deploy desde GitHub
- [ ] Probar cambios en staging antes de main
- [ ] Revisar logs después de cada deploy

## Comandos Útiles para Render Shell

```bash
# Ver migraciones pendientes
python manage.py showmigrations

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Verificar configuración
python manage.py check --deploy

# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Ver logs de Django
tail -f logs/auth.log
```

## Solución Rápida de Problemas

### La aplicación no inicia
1. Revisa logs en Render
2. Verifica que todas las variables de entorno estén configuradas
3. Asegúrate de que `ALLOWED_HOSTS` incluya tu dominio de Render

### Error de base de datos
1. Verifica `DATABASE_URL` en variables de entorno
2. Asegúrate de que PostgreSQL esté activo
3. Revisa que las migraciones se hayan ejecutado

### Error 502 Bad Gateway
1. Revisa que gunicorn esté en requirements.txt
2. Verifica el comando de inicio en Render
3. Revisa los logs para errores de Python

### Archivos estáticos no cargan
1. Verifica que `whitenoise` esté instalado
2. Ejecuta `python manage.py collectstatic`
3. Revisa `STATIC_ROOT` y `STATICFILES_STORAGE`

## 🎉 ¡Listo para Producción!

Una vez completados todos los items de este checklist, tu aplicación estará lista para ser desplegada en Render de forma segura y confiable.
