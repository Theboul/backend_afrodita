# core/constants/catalogo.py
"""
Constantes de configuración para el módulo de catálogo público.
"""


class CatalogConfig:
    """Configuración del catálogo público"""
    
    # Paginación
    PAGE_SIZE_DEFAULT = 12
    PAGE_SIZE_MAX = 100
    PAGE_MIN = 1
    
    # Opciones de ordenamiento
    SORT_NOMBRE = 'nombre'
    SORT_PRECIO_ASC = 'precio_asc'
    SORT_PRECIO_DESC = 'precio_desc'
    SORT_RECIENTES = 'recientes'
    
    SORT_OPTIONS = [
        SORT_NOMBRE,
        SORT_PRECIO_ASC,
        SORT_PRECIO_DESC,
        SORT_RECIENTES
    ]
    
    @classmethod
    def is_valid_sort(cls, sort_option):
        """Verifica si la opción de ordenamiento es válida"""
        return sort_option in cls.SORT_OPTIONS
    
    @classmethod
    def get_default_sort(cls):
        """Retorna el ordenamiento por defecto"""
        return cls.SORT_NOMBRE


class ProductConfig:
    """Configuración para el módulo de productos"""
    
    # Paginación
    PRODUCTS_PAGE_SIZE = 9
    PRODUCTS_PAGE_SIZE_MAX = 50
    
    # Stock
    STOCK_LOW_THRESHOLD = 10
    
    # Tipos de ajuste de stock
    STOCK_INCREMENT = 'INCREMENTO'
    STOCK_DECREMENT = 'DECREMENTO'
    STOCK_CORRECTION = 'CORRECCION'
    
    STOCK_ADJUSTMENT_TYPES = [
        STOCK_INCREMENT,
        STOCK_DECREMENT,
        STOCK_CORRECTION
    ]
    
    @classmethod
    def is_valid_adjustment(cls, adjustment_type):
        """Verifica si el tipo de ajuste es válido"""
        return adjustment_type in cls.STOCK_ADJUSTMENT_TYPES
