"""
Constantes para el módulo de reseñas de productos (CU26).
Centraliza estados y políticas de moderación.
"""


class ReviewStatus:
    """Estados posibles de una reseña."""
    PENDIENTE = 'PENDIENTE'
    PUBLICADA = 'PUBLICADA'
    RECHAZADA = 'RECHAZADA'
    OCULTA = 'OCULTA'

    @classmethod
    def choices(cls):
        """Tuplas para usar en choices de Django."""
        return [
            (cls.PENDIENTE, 'Pendiente de revisión'),
            (cls.PUBLICADA, 'Publicada'),
            (cls.RECHAZADA, 'Rechazada'),
            (cls.OCULTA, 'Oculta'),
        ]

    @classmethod
    def visibles_publico(cls):
        """Estados visibles para catálogo público."""
        return [cls.PUBLICADA]

    @classmethod
    def all(cls):
        return [cls.PENDIENTE, cls.PUBLICADA, cls.RECHAZADA, cls.OCULTA]

    @classmethod
    def is_valid(cls, estado):
        return estado in cls.all()


class ReviewPolicy:
    """Configuraciones de moderación."""
    # Si True, reseñas nuevas se publican directo; si False quedan PENDIENTE.
    AUTO_PUBLICAR = False
