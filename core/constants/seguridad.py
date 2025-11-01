"""
Constantes de seguridad centralizadas.
Incluye configuración de rutas, patrones sospechosos y límites de seguridad.
"""


class SecurityConstants:
    """Constantes de seguridad y validación del sistema."""
    
    # =====================================================
    # RUTAS EXCLUIDAS DE AUDITORÍA
    # =====================================================
    RUTAS_EXCLUIDAS_AUDITORIA = [
        '/api/auth/login',      # Ya se registra en views.py
        '/api/auth/logout',     # Ya se registra en views.py
        '/api/auth/refresh',    # Token refresh no es relevante
        '/api/auth/verificar'   # Verificación de sesión no es relevante
    ]
    
    RUTAS_ADMINISTRATIVAS = [
        '/admin',
        '/static',
        '/media',
        '/favicon.ico'
    ]
    
    # =====================================================
    # RUTAS PÚBLICAS (Sin autenticación requerida)
    # =====================================================
    RUTAS_PUBLICAS_API = [
        '/api/auth/',
        '/api/auth/login/',
        '/api/auth/refresh/',
        '/api/auth/logout/',
        '/api/auth/verificar-sesion/',
        '/api/productos/productos-imagen/',
        '/api/usuarios/register/cliente/step1/',
        '/api/usuarios/register/cliente/step2/',
        '/api/catalogo/',
    ]
    
    # =====================================================
    # RUTAS IMPORTANTES PARA ANALYTICS ANÓNIMOS
    # =====================================================
    RUTAS_IMPORTANTES_ANALYTICS = [
        '/api/productos',       # Vista de productos
        '/api/categoria',       # Vista de categorías  
        '/dashboard',           # Dashboard
        '/preview',             # Preview
        '/',                    # Página principal
    ]
    
    # =====================================================
    # PATRONES DE USER-AGENT SOSPECHOSOS
    # =====================================================
    PATRONES_USER_AGENT_SOSPECHOSOS = [
        (r'<script', 'Contiene tag script'),
        (r'javascript:', 'Contiene javascript:'),
        (r'onerror=', 'Contiene evento onerror'),
        (r'onclick=', 'Contiene evento onclick'),
        (r'eval\(', 'Contiene función eval'),
        (r'sqlmap', 'Herramienta de hacking SQL'),
        (r'nikto', 'Scanner de vulnerabilidades'),
        (r'nmap', 'Scanner de puertos'),
        (r'metasploit', 'Framework de explotación'),
        (r'burp', 'Burp Suite - herramienta de pentesting'),
        (r'acunetix', 'Scanner de vulnerabilidades web'),
        (r'havij', 'Herramienta de SQL injection'),
        (r'masscan', 'Scanner de puertos masivo'),
    ]
    
    # =====================================================
    # CONFIGURACIÓN DE BRUTE FORCE PROTECTION
    # =====================================================
    MAX_INTENTOS_LOGIN = 10         # Máximo de intentos fallidos
    VENTANA_TIEMPO_MINUTOS = 30     # Ventana de tiempo en minutos
    
    # =====================================================
    # CONFIGURACIÓN DE DETECCIÓN DE FUERZA BRUTA
    # =====================================================
    DETECCION_FUERZA_BRUTA_VENTANA = 5  # Ventana en minutos para detección
    DETECCION_FUERZA_BRUTA_MAX = 5       # Máximo de intentos en ventana
    
    # =====================================================
    # LÍMITES DE LONGITUD PARA SANITIZACIÓN
    # =====================================================
    MAX_LENGTH_USER_AGENT = 200
    MAX_LENGTH_DESCRIPCION = 1000
    MAX_LENGTH_TEXTO_GENERICO = 500
    
    # =====================================================
    # CONFIGURACIÓN DE PROXIES CONFIABLES
    # =====================================================
    # Estos valores se obtienen de settings.py normalmente
    # pero aquí están los defaults
    DEFAULT_TRUSTED_PROXY_COUNT = 0
    DEFAULT_LOG_SUSPICIOUS_IPS = True
