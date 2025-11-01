from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from .models import Permiso, Rol, RolPermiso, UsuarioPermiso
from .serializers import (
    PermisoSerializer, PermisoListSerializer,
    RolSerializer, RolDetailSerializer, RolListSerializer,
    RolPermisoSerializer,
    UsuarioPermisoSerializer, UsuarioPermisoListSerializer,
    AsignarPermisosRolSerializer,
    PermisosEfectivosSerializer
)
from apps.usuarios.models import Usuario
from core.constants import APIResponse, Messages

# Importar señales desde bitácora
from apps.bitacora.signals import (
    rol_creado, rol_actualizado, rol_eliminado,
    permiso_creado, permiso_actualizado, permiso_eliminado,
    permiso_asignado_a_rol, permiso_removido_de_rol,
    permiso_concedido_a_usuario, permiso_revocado_a_usuario
)

# =====================================================
# VIEWSET DE PERMISOS
# =====================================================

class PermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar permisos del sistema.
    
    Operaciones:
    - list: Listar todos los permisos (con filtros opcionales)
    - retrieve: Obtener detalle de un permiso
    - create: Crear nuevo permiso
    - update/partial_update: Actualizar permiso
    - destroy: Eliminar permiso (soft delete - marcar como inactivo)
    - por_modulo: Listar permisos agrupados por módulo
    """
    queryset = Permiso.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'id_permiso'
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listados"""
        if self.action == 'list':
            return PermisoListSerializer
        return PermisoSerializer
    
    def get_queryset(self):
        """Permitir filtrado por módulo, activo, búsqueda"""
        queryset = Permiso.objects.all()
        
        # Filtrar por módulo
        modulo = self.request.query_params.get('modulo', None)
        if modulo:
            queryset = queryset.filter(modulo__iexact=modulo)
        
        # Filtrar por estado activo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)
        
        # Búsqueda por nombre o código
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo__icontains=search) |
                Q(descripcion__icontains=search)
            )
        
        return queryset.order_by('modulo', 'nombre')
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo permiso con respuesta personalizada"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            permiso = serializer.save()
            
            # Disparar señal de permiso creado
            permiso_creado.send(
                sender=Permiso,
                permiso=permiso,
                usuario=request.user
            )
            
            return APIResponse.created(
                data=serializer.data,
                message='Permiso creado exitosamente.'
            )
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )
    
    def update(self, request, *args, **kwargs):
        """Actualizar permiso completo"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            permiso = serializer.save()
            
            # Disparar señal de permiso actualizado
            permiso_actualizado.send(
                sender=Permiso,
                permiso=permiso,
                usuario=request.user
            )
            
            return APIResponse.success(
                data=serializer.data,
                message='Permiso actualizado exitosamente.'
            )
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete - marcar como inactivo en lugar de eliminar"""
        instance = self.get_object()
        
        # Verificar si el permiso está en uso
        roles_con_permiso = instance.roles.filter(activo=True).count()
        if roles_con_permiso > 0:
            return APIResponse.bad_request(
                message=f'No se puede eliminar el permiso. Está asignado a {roles_con_permiso} rol(es) activo(s).'
            )
        
        # Guardar nombre antes de marcar como inactivo
        permiso_nombre = instance.nombre
        
        # Marcar como inactivo
        instance.activo = False
        instance.save()
        
        # Disparar señal de permiso eliminado
        permiso_eliminado.send(
            sender=Permiso,
            permiso_nombre=permiso_nombre,
            usuario=request.user
        )
        
        return APIResponse.success(
            message='Permiso marcado como inactivo exitosamente.'
        )
    
    @action(detail=False, methods=['get'], url_path='por-modulo')
    def por_modulo(self, request):
        """Listar permisos agrupados por módulo"""
        permisos = Permiso.objects.filter(activo=True).order_by('modulo', 'nombre')
        
        # Agrupar por módulo
        modulos = {}
        for permiso in permisos:
            if permiso.modulo not in modulos:
                modulos[permiso.modulo] = []
            modulos[permiso.modulo].append(PermisoListSerializer(permiso).data)
        
        return APIResponse.success(
            data=modulos,
            message='Permisos agrupados por módulo obtenidos exitosamente.'
        )


# =====================================================
# VIEWSET DE ROLES
# =====================================================

class RolViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar roles del sistema.
    
    Operaciones:
    - list: Listar todos los roles
    - retrieve: Obtener detalle de un rol con sus permisos
    - create: Crear nuevo rol
    - update/partial_update: Actualizar rol
    - destroy: Eliminar rol (con validaciones)
    - asignar_permisos: Asignar múltiples permisos a un rol
    - remover_permiso: Remover un permiso de un rol
    - usuarios_con_rol: Listar usuarios que tienen este rol
    """
    queryset = Rol.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'id_rol'
    
    def get_serializer_class(self):
        """Usar serializer detallado para retrieve, simplificado para list"""
        if self.action == 'retrieve':
            return RolDetailSerializer
        elif self.action == 'list':
            return RolListSerializer
        return RolSerializer
    
    def get_queryset(self):
        """Permitir filtrado por activo, búsqueda"""
        queryset = Rol.objects.annotate(cantidad_usuarios=Count('usuarios'))
        
        # Filtrar por estado activo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)
        
        # Búsqueda por nombre o descripción
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )
        
        # Filtrar roles de sistema o personalizados
        es_sistema = self.request.query_params.get('es_sistema', None)
        if es_sistema is not None:
            es_sistema_bool = es_sistema.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(es_sistema=es_sistema_bool)
        
        return queryset.order_by('nombre')
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo rol con permisos"""
        serializer = RolDetailSerializer(data=request.data)
        if serializer.is_valid():
            rol = serializer.save()
            
            # Disparar señal de rol creado
            rol_creado.send(
                sender=Rol,
                rol=rol,
                usuario=request.user
            )
            
            return APIResponse.created(
                data=RolDetailSerializer(rol).data,
                message='Rol creado exitosamente.'
            )
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )
    
    def update(self, request, *args, **kwargs):
        """Actualizar rol"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Validar que no sea un rol de sistema si se intenta modificar campos críticos
        if instance.es_sistema and not partial:
            if request.data.get('nombre') != instance.nombre:
                return APIResponse.bad_request(
                    message='No se puede cambiar el nombre de un rol de sistema.'
                )
        
        serializer = RolDetailSerializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            rol = serializer.save()
            
            # Disparar señal de rol actualizado
            rol_actualizado.send(
                sender=Rol,
                rol=rol,
                usuario=request.user
            )
            
            return APIResponse.success(
                data=RolDetailSerializer(rol).data,
                message='Rol actualizado exitosamente.'
            )
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar rol con validaciones"""
        instance = self.get_object()
        
        # No permitir eliminar roles de sistema
        if instance.es_sistema:
            return APIResponse.bad_request(
                message='No se pueden eliminar roles de sistema.'
            )
        
        # No permitir eliminar roles con usuarios activos
        usuarios_activos = instance.usuarios.filter(
            estado_usuario='ACTIVO'
        ).count()
        
        if usuarios_activos > 0:
            return APIResponse.bad_request(
                message=f'No se puede eliminar el rol. Tiene {usuarios_activos} usuario(s) activo(s) asignado(s).'
            )
        
        # Eliminar rol
        nombre_rol = instance.nombre
        instance.delete()
        
        # Disparar señal de rol eliminado
        rol_eliminado.send(
            sender=Rol,
            rol_nombre=nombre_rol,
            usuario=request.user
        )
        
        return APIResponse.success(
            message=f'Rol "{nombre_rol}" eliminado exitosamente.'
        )
    
    @action(detail=True, methods=['post'], url_path='asignar-permisos')
    def asignar_permisos(self, request, id_rol=None):
        """Asignar múltiples permisos a un rol"""
        rol = self.get_object()
        serializer = AsignarPermisosRolSerializer(data=request.data)
        
        if serializer.is_valid():
            permisos_ids = serializer.validated_data['permisos_ids']
            permisos = Permiso.objects.filter(id_permiso__in=permisos_ids, activo=True)
            
            # Asignar permisos
            permisos_nuevos = []
            for permiso in permisos:
                if not rol.permisos.filter(id_permiso=permiso.id_permiso).exists():
                    rol.permisos.add(permiso)
                    permisos_nuevos.append(permiso.nombre)
                    
                    # Disparar señal de permiso asignado
                    permiso_asignado_a_rol.send(
                        sender=RolPermiso,
                        rol=rol,
                        permiso=permiso,
                        usuario=request.user
                    )
            
            if permisos_nuevos:
                return APIResponse.success(
                    data={'permisos_asignados': permisos_nuevos},
                    message=f'{len(permisos_nuevos)} permiso(s) asignado(s) al rol "{rol.nombre}".'
                )
            else:
                return APIResponse.success(
                    message='Todos los permisos ya estaban asignados al rol.'
                )
        
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )
    
    @action(detail=True, methods=['delete'], url_path='remover-permiso/(?P<permiso_id>[^/.]+)')
    def remover_permiso(self, request, id_rol=None, permiso_id=None):
        """Remover un permiso de un rol"""
        rol = self.get_object()
        
        try:
            permiso = Permiso.objects.get(id_permiso=permiso_id)
        except Permiso.DoesNotExist:
            return APIResponse.not_found(message='Permiso no encontrado.')
        
        if rol.permisos.filter(id_permiso=permiso.id_permiso).exists():
            rol.permisos.remove(permiso)
            
            # Disparar señal de permiso removido
            permiso_removido_de_rol.send(
                sender=RolPermiso,
                rol=rol,
                permiso=permiso,
                usuario=request.user
            )
            
            return APIResponse.success(
                message=f'Permiso "{permiso.nombre}" removido del rol "{rol.nombre}".'
            )
        else:
            return APIResponse.bad_request(
                message='El permiso no estaba asignado a este rol.'
            )
    
    @action(detail=True, methods=['get'], url_path='usuarios')
    def usuarios_con_rol(self, request, id_rol=None):
        """Listar usuarios que tienen este rol"""
        rol = self.get_object()
        usuarios = Usuario.objects.filter(id_rol=rol).values(
            'id_usuario',
            'nombre_completo',
            'nombre_usuario',
            'correo',
            'estado_usuario'
        )
        
        return APIResponse.success(
            data={'usuarios': list(usuarios), 'total': usuarios.count()},  # ✅ Corregido: envolver en diccionario
            message=f'Usuarios con rol "{rol.nombre}" obtenidos exitosamente.'
        )


# =====================================================
# VIEWSET DE PERMISOS INDIVIDUALES DE USUARIO
# =====================================================

class UsuarioPermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar permisos individuales de usuarios.
    
    Operaciones:
    - list: Listar permisos individuales
    - create: Conceder o revocar permiso a un usuario
    - destroy: Eliminar asignación individual
    - permisos_usuario: Obtener todos los permisos de un usuario específico
    - permisos_efectivos: Calcular permisos efectivos de un usuario
    """
    queryset = UsuarioPermiso.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listados"""
        if self.action == 'list':
            return UsuarioPermisoListSerializer
        return UsuarioPermisoSerializer
    
    def get_queryset(self):
        """Filtrar por usuario, permiso, tipo"""
        queryset = UsuarioPermiso.objects.select_related('usuario', 'permiso', 'asignado_por')  # ✅ Corregido: era otorgado_por
        
        # Filtrar por usuario
        usuario_id = self.request.query_params.get('usuario', None)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        
        # Filtrar por tipo (concedido/revocado)
        tipo = self.request.query_params.get('tipo', None)
        if tipo == 'concedido':
            queryset = queryset.filter(concedido=True)
        elif tipo == 'revocado':
            queryset = queryset.filter(concedido=False)
        
        # Filtrar solo activos (no expirados)
        solo_activos = self.request.query_params.get('activos', None)
        if solo_activos and solo_activos.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(activo=True)
        
        return queryset.order_by('-fecha_otorgado')
    
    def create(self, request, *args, **kwargs):
        """Conceder o revocar permiso individual a usuario"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Asignar el usuario que otorga el permiso
            usuario_permiso = serializer.save(asignado_por=request.user)  # ✅ Corregido: era otorgado_por
            
            # 🔥 Disparar señal según el tipo
            if usuario_permiso.concedido:
                permiso_concedido_a_usuario.send(
                    sender=UsuarioPermiso,
                    usuario_permiso=usuario_permiso,
                    otorgado_por=request.user  # ✅ MANTENER: la señal sí usa otorgado_por
                )
                mensaje = f'Permiso "{usuario_permiso.permiso.nombre}" concedido a {usuario_permiso.usuario.nombre_completo}.'
            else:
                permiso_revocado_a_usuario.send(
                    sender=UsuarioPermiso,
                    usuario_permiso=usuario_permiso,
                    revocado_por=request.user  # ✅ MANTENER: la señal usa revocado_por
                )
                mensaje = f'Permiso "{usuario_permiso.permiso.nombre}" revocado de {usuario_permiso.usuario.nombre_completo}.'
            
            return APIResponse.created(
                data=UsuarioPermisoSerializer(usuario_permiso).data,
                message=mensaje
            )
        
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar asignación individual de permiso"""
        instance = self.get_object()
        usuario_nombre = instance.usuario.nombre_completo
        permiso_nombre = instance.permiso.nombre
        tipo = "concesión" if instance.concedido else "revocación"
        
        instance.delete()
        
        return APIResponse.success(
            message=f'Se eliminó la {tipo} del permiso "{permiso_nombre}" para {usuario_nombre}.'
        )
    
    @action(detail=False, methods=['get'], url_path='usuario/(?P<usuario_id>[^/.]+)')
    def permisos_usuario(self, request, usuario_id=None):
        """Obtener todos los permisos individuales de un usuario"""
        try:
            usuario = Usuario.objects.get(id_usuario=usuario_id)
        except Usuario.DoesNotExist:
            return APIResponse.not_found(message='Usuario no encontrado.')
        
        permisos = UsuarioPermiso.objects.filter(usuario=usuario, activo=True)
        serializer = UsuarioPermisoListSerializer(permisos, many=True)
        
        return APIResponse.success(
            data={
                'usuario': usuario.nombre_completo,
                'rol': usuario.id_rol.nombre,
                'permisos_individuales': serializer.data
            },
            message='Permisos individuales del usuario obtenidos exitosamente.'
        )
    
    @action(detail=False, methods=['get'], url_path='efectivos/(?P<usuario_id>[^/.]+)')
    def permisos_efectivos(self, request, usuario_id=None):
        """Calcular y mostrar los permisos efectivos de un usuario"""
        try:
            usuario = Usuario.objects.get(id_usuario=usuario_id)
        except Usuario.DoesNotExist:
            return APIResponse.not_found(message='Usuario no encontrado.')
        
        # Obtener permisos del rol
        permisos_rol = usuario.id_rol.permisos.filter(activo=True)
        
        # Obtener permisos individuales activos
        permisos_individuales = UsuarioPermiso.objects.filter(
            usuario=usuario,
            activo=True
        )
        
        permisos_concedidos = [
            up.permiso for up in permisos_individuales if up.concedido
        ]
        
        permisos_revocados = [
            up.permiso for up in permisos_individuales if not up.concedido
        ]
        
        # Calcular permisos finales
        permisos_finales = usuario.obtener_todos_permisos()
        
        data = {
            'usuario': usuario.nombre_completo,
            'rol': usuario.id_rol.nombre,
            'permisos_rol': PermisoListSerializer(permisos_rol, many=True).data,
            'permisos_concedidos': PermisoListSerializer(permisos_concedidos, many=True).data,
            'permisos_revocados': PermisoListSerializer(permisos_revocados, many=True).data,
            'permisos_finales': [p.codigo for p in permisos_finales],
            'total_permisos': len(permisos_finales)
        }
        
        return APIResponse.success(
            data=data,
            message='Permisos efectivos calculados exitosamente.'
        )
