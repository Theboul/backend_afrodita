import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from apps.bitacora.signals import vista_visitada
from apps.autenticacion.utils import obtener_ip_cliente
from core.constants import SecurityConstants

logger = logging.getLogger(__name__)

class AuditoriaMiddleware(MiddlewareMixin):
    """
    Middleware que registra automáticamente el acceso de usuarios autenticados
    a cualquier vista del sistema mediante la señal `vista_visitada`.
    
    IMPORTANTE: Debe estar DESPUÉS de JWTCookieAuthenticationMiddleware en settings.py
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Registra acceso tanto de usuarios autenticados como anónimos.
        Para anónimos, solo registra vistas importantes (productos, categorías, etc.)
        """
        path = request.path.lower()
        
        # Ignorar endpoints administrativos y estáticos siempre
        if any(excluido in path for excluido in SecurityConstants.RUTAS_ADMINISTRATIVAS):
            return None

        try:
            ip = obtener_ip_cliente(request)
            
            # CRÍTICO: Verificar que el usuario esté autenticado correctamente
            # hasattr previene errores si request.user no existe
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Usuario autenticado - registrar todas las vistas importantes
                if not any(excluido in path for excluido in SecurityConstants.RUTAS_EXCLUIDAS_AUDITORIA):
                    # DEBUG: Loguear para verificar que el usuario está autenticado
                    logger.debug(
                        f"Registrando vista para usuario autenticado: "
                        f"{request.user.nombre_usuario} -> {request.path}"
                    )
                    
                    vista_visitada.send(
                        sender=self.__class__,
                        usuario=request.user,
                        ip=ip,
                        ruta=request.path
                    )
            else:
                # Usuario anónimo - solo registrar vistas importantes para analytics
                if self._es_vista_importante_para_anonimos(path):
                    logger.debug(f"Registrando vista anónima: {request.path}")
                    
                    from apps.bitacora.signals import vista_anonima_visitada
                    vista_anonima_visitada.send(
                        sender=self.__class__,
                        ip=ip,
                        ruta=request.path,
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
        except Exception as e:
            # Nunca debe romper el flujo de la vista
            logger.error(f"Error en AuditoriaMiddleware: {str(e)}")
            logger.exception(e)  # Esto loguea el stacktrace completo

        return None

    def _es_vista_importante_para_anonimos(self, path):
        """
        Determina si una vista es importante para trackear en usuarios anónimos.
        Solo rastrea vistas que aporten valor al negocio.
        """
        return any(ruta in path for ruta in SecurityConstants.RUTAS_IMPORTANTES_ANALYTICS)
