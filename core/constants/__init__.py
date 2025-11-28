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
from .promocion import PromotionStatus, PromotionType
from .resenas import ReviewStatus, ReviewPolicy

__all__ = [
    'UserStatus',
    'ProductStatus',
    'CategoryStatus',
    'ImageStatus',
    'PromotionStatus',
    'PromotionType',
    'APIResponse',
    'Messages',
    'BitacoraActions',
    'SecurityConstants',
    'CatalogConfig',
    'ProductConfig',
    'TicketStatus',
    'TicketType',
    'ReviewStatus',
    'ReviewPolicy',
]
