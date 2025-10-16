import logging
from apps.bitacora.models import Bitacora

logger = logging.getLogger(__name__)

class AuditoriaLogger:
    """
    Clase de servicio para registrar eventos en la bitácora de forma centralizada.
    Maneja casos donde IP o usuario pueden ser None.
    """
    
    @staticmethod
    def registrar_evento(accion, descripcion, ip=None, usuario=None):
        """
        Registra un evento en la bitácora.
        
        Args:
            accion (str): Tipo de acción (debe estar en ACCIONES del modelo)
            descripcion (str): Descripción detallada del evento
            ip (str, optional): Dirección IP del cliente
            usuario (Usuario, optional): Usuario que realizó la acción
        """
        try:
            # Validar que la acción sea válida
            acciones_validas = [choice[0] for choice in Bitacora.ACCIONES]
            if accion not in acciones_validas:
                logger.warning(f"Acción no válida en bitácora: {accion}")
                return False
            
            # Crear el registro
            Bitacora.objects.create(
                accion=accion,
                descripcion=descripcion or "",
                ip=ip,
                id_usuario=usuario
            )
            
            logger.debug(f"Evento registrado en bitácora: {accion} - {usuario or 'Anónimo'}")
            return True
            
        except Exception as e:
            # Evita que un fallo en la bitácora rompa el flujo principal
            logger.error(f"Error al registrar en bitácora: {str(e)}")
            logger.error(f"Datos: accion={accion}, usuario={usuario}, ip={ip}")
            return False
    
    @staticmethod
    def registrar_evento_anonimo(accion, descripcion, ip=None):
        """
        Método específico para eventos de usuarios anónimos.
        
        Args:
            accion (str): Tipo de acción (preferiblemente ANONYMOUS_*)
            descripcion (str): Descripción del evento
            ip (str, optional): IP del visitante anónimo
        """
        return AuditoriaLogger.registrar_evento(
            accion=accion,
            descripcion=descripcion,
            ip=ip,
            usuario=None
        )