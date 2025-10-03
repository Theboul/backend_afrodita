# apps/bitacora/utils.py
import logging
import traceback
from django.db import connection, transaction

logger = logging.getLogger(__name__)

def _execute_insert(params):
    
    sql = "INSERT INTO bitacora (accion, descripcion, ip, id_usuario) VALUES (%s, %s, %s, %s)"
    try:
        # normalizar a tupla (psycopg2 acepta lista también, pero por precaución)
        params_tuple = tuple(params)
        with connection.cursor() as cur:
            cur.execute(sql, params_tuple)
    except Exception as exc:
        # registramos el SQL + params para debugging
        logger.error("Error al insertar en bitacora: %s", exc)
        logger.error("SQL: %s", sql)
        logger.error("Params: %r", params)
        logger.error("Traceback:\n%s", traceback.format_exc())
        # No volver a lanzar la excepción para que la vista no devuelva 500 por este fallo.
        # Si prefieres que falle para detectarlo en desarrollo, puedes re-raise aquí.
        return

def log_activity(accion: str, descripcion: str = None, request=None, user_id=None):
    
    # extraer IP (si existe)
    ip = None
    if request is not None:
        try:
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = (xff.split(',')[0].strip()) if xff else request.META.get('REMOTE_ADDR')
        except Exception:
            ip = None

    # normalizar descripcion a str (evita pasar objetos raros)
    if descripcion is not None:
        try:
            descripcion = str(descripcion)
        except Exception:
            descripcion = None

    params = [accion, descripcion, ip, user_id]

    # Insertar después del commit (si hay transaction), con manejo de excepción dentro de _execute_insert
    try:
        transaction.on_commit(lambda: _execute_insert(params))
    except Exception:
        # En raros casos (si no hay transacción o falló on_commit) intentamos insertar inmediatamente
        _execute_insert(params)
