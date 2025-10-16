import re
from django.core.exceptions import ValidationError


def validar_fuerza_contraseña(password):
    """
    Valida que la contraseña cumpla con requisitos de seguridad:
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un carácter especial
    """
    if len(password) < 8:
        raise ValidationError(
            "La contraseña debe tener al menos 8 caracteres."
        )
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError(
            "La contraseña debe contener al menos una letra mayúscula."
        )
    
    if not re.search(r'[a-z]', password):
        raise ValidationError(
            "La contraseña debe contener al menos una letra minúscula."
        )
    
    if not re.search(r'\d', password):
        raise ValidationError(
            "La contraseña debe contener al menos un número."
        )
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(
            "La contraseña debe contener al menos un carácter especial (!@#$%^&*...)."
        )
    
    # Verificar contraseñas comunes
    contraseñas_comunes = [
        'password', '12345678', 'qwerty123', 'admin123',
        'password123', '123456789', 'contraseña'
    ]
    
    if password.lower() in contraseñas_comunes:
        raise ValidationError(
            "Esta contraseña es demasiado común. Elige una más segura."
        )


def validar_nombre_usuario(username):
    """
    Valida el formato del nombre de usuario.
    - Solo letras, números, guiones bajos y puntos
    - Entre 3 y 30 caracteres
    """
    if len(username) < 3 or len(username) > 30:
        raise ValidationError(
            "El nombre de usuario debe tener entre 3 y 30 caracteres."
        )
    
    if not re.match(r'^[a-zA-Z0-9._]+$', username):
        raise ValidationError(
            "El nombre de usuario solo puede contener letras, números, puntos y guiones bajos."
        )
    
    # Prevenir nombres reservados
    nombres_reservados = ['admin', 'root', 'system', 'api', 'test']
    if username.lower() in nombres_reservados:
        raise ValidationError(
            "Este nombre de usuario no está disponible."
        )
