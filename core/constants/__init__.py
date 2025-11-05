"""
Constantes centralizadas para el módulo core.
"""

from .estados import UserStatus, ProductStatus, CategoryStatus, ImageStatus
from .responses import APIResponse
from .mensajes import Messages
from .acciones import BitacoraActions
from .seguridad import SecurityConstants
from .catalogo import CatalogConfig, ProductConfig
from .soporte import TicketStatus, TicketType

__all__ = [
    'UserStatus',
    'ProductStatus',
    'CategoryStatus',
    'ImageStatus',
    'APIResponse',
    'Messages',
    'BitacoraActions',
    'SecurityConstants',
    'CatalogConfig',
    'ProductConfig',
    'TicketStatus',
    'TicketType',
]
