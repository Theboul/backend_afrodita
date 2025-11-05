"""
Django settings for afrodita project.
"""
from datetime import timedelta
from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.api
import dj_database_url
from corsheaders.defaults import default_headers, default_methods
from dotenv import load_dotenv
import os

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SEGURIDAD
# ==============================================================================

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ==============================================================================
# APLICACIONES
# ==============================================================================

INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',
    
    # Third party apps
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',

    # Local apps
    'apps.seguridad',       # Sistema de roles y permisos
    'apps.autenticacion',
    'apps.usuarios',
    'apps.productos',
    'apps.imagenes',
    'apps.ventas',
    'apps.compras',
    'apps.bitacora',
    'apps.categoria',
    'apps.catalogo',
    'apps.inventario',
    'apps.lotes',
    'apps.soporte',
]

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'usuarios.Usuario'

# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware
    'apps.autenticacion.middleware.seguridad.JWTCookieAuthenticationMiddleware',  # 1° Lee JWT
    'apps.autenticacion.middleware.seguridad.IPBlacklistMiddleware',              # 2° Bloquea IPs
    'apps.autenticacion.middleware.seguridad.BruteForceProtectionMiddleware',     # 3° Detecta ataques
    'apps.bitacora.middleware.AuditoriaMiddleware',                               # 4° DESPUÉS de JWT
    'apps.autenticacion.middleware.seguridad.SecurityHeadersMiddleware',          # 5° Headers finales
]

ROOT_URLCONF = 'afrodita.urls'

# ==============================================================================
# TEMPLATES
# ==============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'afrodita.wsgi.application'
ASGI_APPLICATION = 'afrodita.asgi.application'

# ==============================================================================
# BASE DE DATOS
# ==============================================================================

# Configuración para desarrollo y producción
if os.getenv('DATABASE_URL'):
    # Producción (Render proporciona DATABASE_URL automáticamente)
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Desarrollo (usando variables individuales)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
    'SECURE': os.getenv('CLOUDINARY_SECURE', 'True') == 'True'
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=os.getenv('CLOUDINARY_SECURE', 'True') == 'True'
)

# ==============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================================================
# INTERNACIONALIZACIÓN
# ==============================================================================

LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = False  # Desactivado porque usas TIME_ZONE local

# ==============================================================================
# ARCHIVOS ESTÁTICOS
# ==============================================================================

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Configuración de WhiteNoise para servir archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Directorios adicionales de archivos estáticos
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SPECTACULAR_SETTINGS = {
    'TITLE': '🌸 Sistema Afrodita',
    'DESCRIPTION': 'Documentación interactiva de todos los endpoints del sistema Afrodita.',
    'VERSION': '1.0.0',
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'SERVE_INCLUDE_SCHEMA': False,
}
# ==============================================================================
# REST FRAMEWORK & JWT
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",  # Requiere autenticación por defecto
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication"
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '10/minute',
        'register': '3/hour',
        'refresh': '10/minute',
        'password_reset': '3/hour',
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50
}


SIMPLE_JWT = {
    # Duración de los tokens
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
    
    # Rotar refresh tokens
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    
    # Algoritmo y firma
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'VERIFY_SIGNATURE': True,
    
    # Headers
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # Claims
    'USER_ID_FIELD': 'id_usuario',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',

    
}

# ==============================================================================
# CORS
# ==============================================================================

CORS_ALLOWED_ORIGINS = [
    "https://afroditastore.netlify.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
]

# Configuraciones críticas para CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = False  # Solo permitir orígenes especificados arriba

# Headers permitidos (incluir cookie)
CORS_ALLOW_HEADERS = list(default_methods) +[
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cookie',  # Importante para cookies
]

# Métodos HTTP permitidos
CORS_ALLOW_METHODS = list(default_headers) +[
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Headers que el frontend puede leer
CORS_EXPOSE_HEADERS = [
    'Content-Type',
    'X-CSRFToken',
]

# Preflight cache (24 horas)
CORS_PREFLIGHT_MAX_AGE = 86400

# Permitir orígenes confiables para CSRF
CSRF_TRUSTED_ORIGINS = [
    "https://afroditastore.netlify.app",
    "https://backend-afrodita.onrender.com",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# ==============================================================================
# SEGURIDAD DE COOKIES
# ==============================================================================

# Cookies de sesión
SESSION_COOKIE_SECURE = not DEBUG  # True en producción, False en desarrollo
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None' if not DEBUG else 'Lax'  # None para cross-domain
SESSION_COOKIE_DOMAIN = None  # Permite subir cookies a cualquier dominio

# Cookies CSRF
CSRF_COOKIE_SECURE = not DEBUG  # True en producción
CSRF_COOKIE_HTTPONLY = False  # JS debe leerlo
CSRF_COOKIE_SAMESITE = 'None' if not DEBUG else 'Lax'  # None para cross-domain
CSRF_COOKIE_DOMAIN = None  # Permite subir cookies a cualquier dominio

# Headers de seguridad
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS (solo en producción)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True

# ==============================================================================
# LOGGING
# ==============================================================================

# Crear directorio de logs si no existe
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'auth_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'auth.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'security.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps.autenticacion': {
            'handlers': ['auth_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

TRUSTED_PROXY_COUNT = 1