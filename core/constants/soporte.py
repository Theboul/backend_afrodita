"""
Constantes para el módulo de soporte/tickets.
Centraliza estados y tipos de tickets para evitar hardcoding.
"""


class TicketStatus:
    """Estados posibles de un ticket de soporte."""
    PENDIENTE = 'PENDIENTE'
    EN_PROCESO = 'EN_PROCESO'
    RESPONDIDO = 'RESPONDIDO'
    CERRADO = 'CERRADO'
    
    @classmethod
    def choices(cls):
        """Retorna tuplas para usar en choices de Django."""
        return [
            (cls.PENDIENTE, 'Pendiente'),
            (cls.EN_PROCESO, 'En proceso'),
            (cls.RESPONDIDO, 'Respondido'),
            (cls.CERRADO, 'Cerrado'),
        ]
    
    @classmethod
    def all(cls):
        """Retorna lista de todos los estados válidos."""
        return [cls.PENDIENTE, cls.EN_PROCESO, cls.RESPONDIDO, cls.CERRADO]
    
    @classmethod
    def is_valid(cls, estado):
        """Valida si un estado es válido."""
        return estado in cls.all()


class TicketType:
    """Tipos de consulta en tickets de soporte."""
    RECLAMO = 'RECLAMO'
    DUDA = 'DUDA'
    PEDIDO = 'PEDIDO'
    SUGERENCIA = 'SUGERENCIA'
    OTRO = 'OTRO'
    
    @classmethod
    def choices(cls):
        """Retorna tuplas para usar en choices de Django."""
        return [
            (cls.RECLAMO, 'Reclamo'),
            (cls.DUDA, 'Duda sobre producto'),
            (cls.PEDIDO, 'Problema con pedido'),
            (cls.SUGERENCIA, 'Sugerencia'),
            (cls.OTRO, 'Otro'),
        ]
    
    @classmethod
    def all(cls):
        """Retorna lista de todos los tipos válidos."""
        return [cls.RECLAMO, cls.DUDA, cls.PEDIDO, cls.SUGERENCIA, cls.OTRO]
    
    @classmethod
    def is_valid(cls, tipo):
        """Valida si un tipo es válido."""
        return tipo in cls.all()
