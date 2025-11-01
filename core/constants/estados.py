"""
Constantes para estados de usuarios y otros recursos del sistema.
Centraliza todos los estados hardcodeados para evitar typos y facilitar mantenimiento.
"""


class UserStatus:
    """Estados posibles de un usuario en el sistema."""
    ACTIVO = 'ACTIVO'
    INACTIVO = 'INACTIVO'
    
    @classmethod
    def choices(cls):
        """Retorna tuplas para usar en choices de Django."""
        return [
            (cls.ACTIVO, 'Activo'),
            (cls.INACTIVO, 'Inactivo'),
        ]
    
    @classmethod
    def all(cls):
        """Retorna lista de todos los estados válidos."""
        return [cls.ACTIVO, cls.INACTIVO]
    
    @classmethod
    def is_valid(cls, estado):
        """Valida si un estado es válido."""
        return estado in cls.all()


class ProductStatus:
    """Estados posibles de un producto (para futuro uso)."""
    DISPONIBLE = 'DISPONIBLE'
    AGOTADO = 'AGOTADO'
    DESCONTINUADO = 'DESCONTINUADO'
    
    @classmethod
    def choices(cls):
        return [
            (cls.DISPONIBLE, 'Disponible'),
            (cls.AGOTADO, 'Agotado'),
            (cls.DESCONTINUADO, 'Descontinuado'),
        ]


class CategoryStatus:
    """Estados posibles para categorías."""
    ACTIVA = 'ACTIVA'
    INACTIVA = 'INACTIVA'
    
    @classmethod
    def choices(cls):
        """Retorna tuplas para usar en choices de Django."""
        return [
            (cls.ACTIVA, 'Activa'),
            (cls.INACTIVA, 'Inactiva'),
        ]
    
    @classmethod
    def all(cls):
        """Retorna lista de todos los estados válidos."""
        return [cls.ACTIVA, cls.INACTIVA]
    
    @classmethod
    def is_valid(cls, estado):
        """Valida si un estado es válido."""
        return estado in cls.all()


class ImageStatus:
    """Estados posibles para imágenes de productos."""
    ACTIVA = 'ACTIVA'
    INACTIVA = 'INACTIVA'
    
    @classmethod
    def choices(cls):
        """Retorna tuplas para usar en choices de Django."""
        return [
            (cls.ACTIVA, 'Activa'),
            (cls.INACTIVA, 'Inactiva'),
        ]
    
    @classmethod
    def all(cls):
        """Retorna lista de todos los estados válidos."""
        return [cls.ACTIVA, cls.INACTIVA]
    
    @classmethod
    def is_valid(cls, estado):
        """Valida si un estado es válido."""
        return estado in cls.all()
