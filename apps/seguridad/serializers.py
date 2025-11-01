from rest_framework import serializers
from django.utils import timezone
from .models import Permiso, Rol, RolPermiso, UsuarioPermiso
from apps.usuarios.models import Usuario

# =====================================================
# SERIALIZER DE PERMISOS
# =====================================================

class PermisoSerializer(serializers.ModelSerializer):
    """Serializer completo para permisos"""
    
    class Meta:
        model = Permiso
        fields = [
            'id_permiso', 
            'nombre', 
            'codigo', 
            'descripcion', 
            'modulo', 
            'activo',
            'fecha_creacion',
            'fecha_modificacion'  # ✅ Corregido: era fecha_actualizacion
        ]
        read_only_fields = ['id_permiso', 'fecha_creacion', 'fecha_modificacion']
    
    def validate_codigo(self, value):
        """Validar que el código sea en mayúsculas y formato válido"""
        if not value.isupper():
            raise serializers.ValidationError("El código debe estar en mayúsculas.")
        if not value.replace('_', '').replace('.', '').isalnum():
            raise serializers.ValidationError("El código solo puede contener letras, números, puntos y guiones bajos.")
        return value


class PermisoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    
    class Meta:
        model = Permiso
        fields = ['id_permiso', 'nombre', 'codigo', 'modulo', 'activo']


# =====================================================
# SERIALIZER DE ROL-PERMISO (Tabla Intermedia)
# =====================================================

class RolPermisoSerializer(serializers.ModelSerializer):
    """Serializer para asignación de permisos a roles"""
    permiso_nombre = serializers.CharField(source='permiso.nombre', read_only=True)
    permiso_codigo = serializers.CharField(source='permiso.codigo', read_only=True)
    asignado_por_nombre = serializers.CharField(source='asignado_por.nombre_completo', read_only=True)
    
    class Meta:
        model = RolPermiso
        fields = [
            'id',
            'rol',
            'permiso',
            'permiso_nombre',
            'permiso_codigo',
            'asignado_por',
            'asignado_por_nombre',
            'fecha_asignacion'
        ]
        read_only_fields = ['id', 'fecha_asignacion']


# =====================================================
# SERIALIZER DE ROLES
# =====================================================

class RolSerializer(serializers.ModelSerializer):
    """Serializer completo para roles"""
    cantidad_permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = Rol
        fields = [
            'id_rol',
            'nombre',
            'descripcion',
            'es_sistema',
            'activo',
            'cantidad_permisos',
            'fecha_creacion',
            'fecha_modificacion'
        ]
        read_only_fields = ['id_rol', 'fecha_creacion', 'fecha_modificacion']
    
    def get_cantidad_permisos(self, obj):
        """Retorna la cantidad de permisos asignados al rol"""
        return obj.permisos.count()
    
    def validate_nombre(self, value):
        """Validar unicidad del nombre (case-insensitive)"""
        nombre_upper = value.upper()
        
        # Si es actualización, excluir el rol actual
        if self.instance:
            if Rol.objects.filter(nombre__iexact=nombre_upper).exclude(id_rol=self.instance.id_rol).exists():
                raise serializers.ValidationError("Ya existe un rol con este nombre.")
        else:
            if Rol.objects.filter(nombre__iexact=nombre_upper).exists():
                raise serializers.ValidationError("Ya existe un rol con este nombre.")
        
        return nombre_upper
    
    def validate_es_sistema(self, value):
        """No permitir modificar roles de sistema en edición"""
        if self.instance and self.instance.es_sistema and not value:
            raise serializers.ValidationError("No se puede cambiar un rol de sistema a rol personalizado.")
        return value


class RolDetailSerializer(RolSerializer):
    """Serializer detallado con permisos anidados"""
    permisos = PermisoListSerializer(many=True, read_only=True)
    permisos_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Permiso.objects.filter(activo=True),
        source='permisos',
        write_only=True,
        required=False
    )
    
    class Meta(RolSerializer.Meta):
        fields = RolSerializer.Meta.fields + ['permisos', 'permisos_ids']
    
    def create(self, validated_data):
        """Crear rol con permisos asignados"""
        permisos = validated_data.pop('permisos', [])
        rol = Rol.objects.create(**validated_data)
        
        if permisos:
            rol.permisos.set(permisos)
        
        return rol
    
    def update(self, instance, validated_data):
        """Actualizar rol y sus permisos"""
        permisos = validated_data.pop('permisos', None)
        
        # Actualizar campos del rol
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar permisos si se proporcionaron
        if permisos is not None:
            instance.permisos.set(permisos)
        
        return instance


class RolListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    cantidad_permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = Rol
        fields = ['id_rol', 'nombre', 'descripcion', 'es_sistema', 'activo', 'cantidad_permisos']
    
    def get_cantidad_permisos(self, obj):
        return obj.permisos.count()


# =====================================================
# SERIALIZER DE PERMISOS INDIVIDUALES DE USUARIO
# =====================================================

class UsuarioPermisoSerializer(serializers.ModelSerializer):
    """Serializer para permisos individuales de usuarios"""
    usuario_nombre = serializers.CharField(source='usuario.nombre_completo', read_only=True)
    permiso_nombre = serializers.CharField(source='permiso.nombre', read_only=True)
    permiso_codigo = serializers.CharField(source='permiso.codigo', read_only=True)
    asignado_por_nombre = serializers.CharField(source='asignado_por.nombre_completo', read_only=True)
    tipo_permiso = serializers.SerializerMethodField()
    
    class Meta:
        model = UsuarioPermiso
        fields = [
            'id_usuario_permiso',  # ✅ Corregido: era 'id'
            'usuario',
            'usuario_nombre',
            'permiso',
            'permiso_nombre',
            'permiso_codigo',
            'concedido',
            'tipo_permiso',
            'fecha_expiracion',
            'motivo',
            'asignado_por',  # ✅ Corregido: era 'otorgado_por'
            'asignado_por_nombre',  # ✅ Corregido: era 'otorgado_por_nombre'
            'fecha_asignacion',  # ✅ Corregido: era 'fecha_otorgado'
            'activo'
        ]
        read_only_fields = ['id_usuario_permiso', 'fecha_asignacion', 'activo']
    
    def get_tipo_permiso(self, obj):
        """Retorna si es una concesión o revocación"""
        return "CONCEDIDO" if obj.concedido else "REVOCADO"
    
    def validate(self, data):
        """Validar lógica de permisos individuales"""
        usuario = data.get('usuario')
        permiso = data.get('permiso')
        concedido = data.get('concedido')
        fecha_expiracion = data.get('fecha_expiracion', None)
        
        # Validar fecha de expiración en el futuro
        if fecha_expiracion and fecha_expiracion <= timezone.now():
            raise serializers.ValidationError({
                'fecha_expiracion': 'La fecha de expiración debe ser futura.'
            })
        
        # Si es revocación, validar que el usuario tenga el permiso por rol
        if not concedido:
            if not usuario.id_rol.tiene_permiso(permiso.codigo):
                raise serializers.ValidationError({
                    'permiso': f'No se puede revocar el permiso "{permiso.nombre}" porque el usuario no lo tiene en su rol.'
                })
        
        # Validar que el permiso esté activo
        if not permiso.activo:
            raise serializers.ValidationError({
                'permiso': 'No se puede asignar un permiso inactivo.'
            })
        
        return data
    
    def validate_motivo(self, value):
        """Validar que el motivo no esté vacío"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("El motivo es obligatorio.")
        return value


class UsuarioPermisoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar permisos de usuario"""
    permiso_nombre = serializers.CharField(source='permiso.nombre', read_only=True)
    permiso_codigo = serializers.CharField(source='permiso.codigo', read_only=True)
    tipo_permiso = serializers.SerializerMethodField()
    
    class Meta:
        model = UsuarioPermiso
        fields = [
            'id_usuario_permiso',  # ✅ Corregido: era 'id'
            'permiso_codigo',
            'permiso_nombre',
            'concedido',
            'tipo_permiso',
            'fecha_expiracion',
            'activo'
        ]
    
    def get_tipo_permiso(self, obj):
        return "CONCEDIDO" if obj.concedido else "REVOCADO"


# =====================================================
# SERIALIZER PARA ASIGNAR MÚLTIPLES PERMISOS A ROL
# =====================================================

class AsignarPermisosRolSerializer(serializers.Serializer):
    """Serializer para asignar múltiples permisos a un rol de una vez"""
    permisos_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )
    
    def validate_permisos_ids(self, value):
        """Validar que todos los permisos existan y estén activos"""
        permisos = Permiso.objects.filter(id_permiso__in=value, activo=True)
        
        if permisos.count() != len(value):
            raise serializers.ValidationError("Uno o más permisos no existen o están inactivos.")
        
        return value


# =====================================================
# SERIALIZER PARA OBTENER PERMISOS EFECTIVOS DE USUARIO
# =====================================================

class PermisosEfectivosSerializer(serializers.Serializer):
    """Serializer para mostrar los permisos efectivos de un usuario"""
    permisos_rol = PermisoListSerializer(many=True, read_only=True)
    permisos_concedidos = PermisoListSerializer(many=True, read_only=True)
    permisos_revocados = PermisoListSerializer(many=True, read_only=True)
    permisos_finales = PermisoListSerializer(many=True, read_only=True)
