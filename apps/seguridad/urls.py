from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PermisoViewSet, RolViewSet, UsuarioPermisoViewSet

# =====================================================
# CONFIGURACIÓN DEL ROUTER
# =====================================================

router = DefaultRouter()
router.register(r'permisos', PermisoViewSet, basename='permiso')
router.register(r'roles', RolViewSet, basename='rol')
router.register(r'usuario-permisos', UsuarioPermisoViewSet, basename='usuario-permiso')

# =====================================================
# URLS DE LA APP SEGURIDAD
# =====================================================

urlpatterns = [
    path('', include(router.urls)),
]

"""
RUTAS DISPONIBLES:
=================

PERMISOS:
---------
GET    /api/seguridad/permisos/                    - Listar permisos
POST   /api/seguridad/permisos/                    - Crear permiso
GET    /api/seguridad/permisos/{id}/               - Detalle permiso
PUT    /api/seguridad/permisos/{id}/               - Actualizar permiso
PATCH  /api/seguridad/permisos/{id}/               - Actualizar parcial
DELETE /api/seguridad/permisos/{id}/               - Eliminar permiso (soft delete)
GET    /api/seguridad/permisos/por-modulo/         - Permisos agrupados por módulo

ROLES:
------
GET    /api/seguridad/roles/                       - Listar roles
POST   /api/seguridad/roles/                       - Crear rol
GET    /api/seguridad/roles/{id}/                  - Detalle rol con permisos
PUT    /api/seguridad/roles/{id}/                  - Actualizar rol
PATCH  /api/seguridad/roles/{id}/                  - Actualizar parcial
DELETE /api/seguridad/roles/{id}/                  - Eliminar rol (con validaciones)
POST   /api/seguridad/roles/{id}/asignar-permisos/ - Asignar múltiples permisos
DELETE /api/seguridad/roles/{id}/remover-permiso/{permiso_id}/ - Remover permiso
GET    /api/seguridad/roles/{id}/usuarios/         - Usuarios con este rol

PERMISOS INDIVIDUALES:
----------------------
GET    /api/seguridad/usuario-permisos/            - Listar permisos individuales
POST   /api/seguridad/usuario-permisos/            - Conceder/Revocar permiso individual
DELETE /api/seguridad/usuario-permisos/{id}/       - Eliminar asignación individual
GET    /api/seguridad/usuario-permisos/usuario/{usuario_id}/ - Permisos de usuario
GET    /api/seguridad/usuario-permisos/efectivos/{usuario_id}/ - Permisos efectivos

QUERY PARAMS:
-------------
Permisos:
  - modulo: Filtrar por módulo
  - activo: true/false - Filtrar por estado
  - search: Buscar en nombre/código/descripción

Roles:
  - activo: true/false - Filtrar por estado
  - es_sistema: true/false - Filtrar roles de sistema
  - search: Buscar en nombre/descripción

Usuario-Permisos:
  - usuario: ID del usuario
  - tipo: concedido/revocado
  - activos: true/false - Solo permisos no expirados
"""
