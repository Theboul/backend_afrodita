"""
Constantes específicas para promociones.
"""


class PromotionStatus:
    """Estados posibles para una promoción."""

    ACTIVA = 'ACTIVA'
    INACTIVA = 'INACTIVA'

    @classmethod
    def choices(cls):
        return [
            (cls.ACTIVA, 'Activa'),
            (cls.INACTIVA, 'Inactiva'),
        ]

    @classmethod
    def all(cls):
        return [cls.ACTIVA, cls.INACTIVA]

    @classmethod
    def is_valid(cls, estado):
        return estado in cls.all()


class PromotionType:
    """Tipos de promoción soportados."""

    PORCENTAJE = 'DESCUENTO_PORCENTAJE'
    MONTO = 'DESCUENTO_MONTO'
    COMBO = 'COMBO'
    DOS_POR_UNO = 'DOS_X_UNO'

    @classmethod
    def choices(cls):
        return [
            (cls.PORCENTAJE, 'Descuento porcentaje'),
            (cls.MONTO, 'Descuento monto'),
            (cls.COMBO, 'Combo'),
            (cls.DOS_POR_UNO, '2x1'),
        ]

    @classmethod
    def requires_value(cls, tipo):
        return tipo in [cls.PORCENTAJE, cls.MONTO]
