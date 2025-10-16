from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate limiting para intentos de login.
    Permite 5 intentos por minuto para usuarios anónimos.
    """
    rate = '5/minute'
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """
    Rate limiting para registro de usuarios.
    Previene creación masiva de cuentas.
    """
    rate = '3/hour'
    scope = 'register'


class RefreshTokenRateThrottle(AnonRateThrottle):
    """
    Rate limiting para refresh de tokens.
    """
    rate = '10/minute'
    scope = 'refresh'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Rate limiting para solicitudes de reseteo de contraseña.
    """
    rate = '3/hour'
    scope = 'password_reset'