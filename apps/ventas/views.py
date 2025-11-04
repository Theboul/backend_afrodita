from decimal import Decimal
import logging

from django.db import connections
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.autenticacion.utils.helpers import obtener_ip_cliente
from apps.autenticacion.utils.payments_security import (
    validate_amount,
    validate_currency,
    generate_reference,
    sign_payment_token,
    verify_payment_token,
    build_qr_payload,
    sanitize_text,
)
from core.constants import APIResponse, Messages
from .serializers import (
    MetodoPagoSerializer,
    IniciarPagoSerializer,
    ConfirmarPagoSerializer,
)
from .models import MetodoPago, PaymentTransaction, PaymentState, Venta

# Alias para compatibilidad con vistas antiguas no publicadas
PaymentStatus = PaymentState

logger = logging.getLogger(__name__)


def index(request):
    return JsonResponse({"message": "API de ventas funcionando"})


def _fetch_payment_methods():
    """
    Intenta leer métodos de pago desde la base Neon.
    Si falla, retorna fallback con QR.
    Estructura: [{"codigo": str, "nombre": str}]
    """
    # 1) Intentar mediante ORM (tabla existente, managed=False)
    try:
        methods = list(
            MetodoPago.objects.filter(activo=True).order_by('orden', 'nombre').values('codigo', 'nombre')
        )
        if methods:
            # Normalizar keys y upper en código
            return [{"codigo": m["codigo"].upper(), "nombre": m["nombre"]} for m in methods]
    except Exception as e:
        logger.debug(f"ORM MetodoPago no disponible: {e}")

    # 2) Fallback a SQL directo (si el modelo no coincide)
    try:
        with connections["default"].cursor() as cursor:
            # Intento 1: columnas (codigo, nombre, activo, orden)
            try:
                cursor.execute(
                    """
                    SELECT codigo, nombre
                    FROM metodo_pago
                    WHERE activo = TRUE
                    ORDER BY orden ASC NULLS LAST, nombre ASC
                    """
                )
                rows = cursor.fetchall()
                methods = []
                for row in rows:
                    codigo, nombre = row[0], row[1]
                    if not codigo:
                        continue
                    methods.append({"codigo": str(codigo).upper(), "nombre": str(nombre) if nombre else str(codigo)})
                if methods:
                    return methods
            except Exception:
                pass

            # Intento 2: columnas (id, nombre) y sin filtro activo
            try:
                cursor.execute(
                    """
                    SELECT id, nombre
                    FROM metodo_pago
                    ORDER BY nombre ASC
                    """
                )
                rows = cursor.fetchall()
                methods = []
                for row in rows:
                    codigo, nombre = row[0], row[1]
                    if not codigo:
                        continue
                    methods.append({"codigo": str(codigo).upper(), "nombre": str(nombre) if nombre else str(codigo)})
                if methods:
                    return methods
            except Exception:
                pass

            # Intento 3: tabla alternativa payment_method(code, name, active)
            try:
                cursor.execute(
                    """
                    SELECT code, name
                    FROM payment_method
                    WHERE active = TRUE
                    ORDER BY name ASC
                    """
                )
                rows = cursor.fetchall()
                methods = []
                for row in rows:
                    codigo, nombre = row[0], row[1]
                    if not codigo:
                        continue
                    methods.append({"codigo": str(codigo).upper(), "nombre": str(nombre) if nombre else str(codigo)})
                if methods:
                    return methods
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"No se pudo obtener métodos desde Neon (SQL), usando fallback QR: {e}")

    # Fallback
    return [{"codigo": "QR", "nombre": "QR"}]


def _fetch_payment_methods_v2():
    """
    Versión alineada al esquema real de Neon.
    Retorna: [{id_metodo_pago, tipo, categoria, requiere_pasarela}]
    """
    try:
        methods = list(
            MetodoPago.objects.filter(activo=True)
            .order_by('id_metodo_pago')
            .values('id_metodo_pago', 'tipo', 'categoria', 'requiere_pasarela')
        )
        if methods:
            return methods
    except Exception as e:
        logger.debug(f"ORM MetodoPago no disponible: {e}")

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute(
                """
                SELECT id_metodo_pago, tipo, categoria, requiere_pasarela
                FROM metodo_pago
                WHERE activo = TRUE
                ORDER BY id_metodo_pago ASC
                """
            )
            rows = cursor.fetchall()
            methods = []
            for row in rows:
                id_mp, tipo, categoria, req = row[0], row[1], row[2], row[3]
                methods.append({
                    "id_metodo_pago": int(id_mp),
                    "tipo": str(tipo),
                    "categoria": str(categoria),
                    "requiere_pasarela": bool(req),
                })
            if methods:
                return methods
    except Exception as e:
        logger.warning(f"No se pudo obtener métodos desde Neon (SQL): {e}")

    return [{"id_metodo_pago": 0, "tipo": "QR_FISICO", "categoria": "FISICO", "requiere_pasarela": False}]


class PaymentMethodsView(APIView):
    # Público para pruebas sin BD
    permission_classes = [IsAuthenticated]

    def get(self, request):
        methods = _fetch_payment_methods_v2()
        serializer = MetodoPagoSerializer(methods, many=True)
        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={"methods": serializer.data}
        )


class InitiatePaymentView(APIView):
    # Público para pruebas sin BD
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IniciarPagoSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(Messages.INVALID_DATA, errors=serializer.errors)

        data = serializer.validated_data
        try:
            amount = validate_amount(data.get("monto"))
            currency = validate_currency(data.get("moneda"))
        except ValueError as e:
            return APIResponse.bad_request(Messages.INVALID_DATA, errors={"monto": [str(e)]})

        description = sanitize_text(data.get("descripcion") or "")
        requested_method = (data.get("metodo") or "").upper().strip()

        methods = _fetch_payment_methods()
        codes = [m["codigo"] for m in methods]
        method = requested_method if requested_method in codes else (codes[0] if codes else "QR")

        reference = sanitize_text(data.get("referencia") or "") or generate_reference()
        ip = obtener_ip_cliente(request)

        token_info = sign_payment_token({
            "ref": reference,
            "amt": str(amount),
            "cur": currency,
            "mtd": method,
            "uid": getattr(request.user, "id_usuario", getattr(request.user, "id", None)),
            "ip": ip,
            "desc": description,
        }, expires_minutes=15)

        response = {
            "reference": reference,
            "method": method,
            "status": PaymentStatus.PENDING,
            "token": token_info["token"],
            "expires_at": token_info["exp"],
        }

        # Incluir datos QR si aplica
        if method == "QR":
            response["qr"] = {
                "payload": build_qr_payload(reference, Decimal(str(amount)), currency),
                "hint": "Escanea con tu app bancaria para completar el pago"
            }

        # Persistir intento de pago en la BD
        try:
            PaymentTransaction.objects.create(
                referencia=reference,
                metodo=method,
                monto=amount,
                moneda=currency,
                descripcion=description,
                estado=PaymentStatus.PENDING,
                ip=ip,
                usuario=request.user if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False) else None,
            )
        except Exception as e:
            logger.error(f"No se pudo persistir la transacción de pago: {e}")

        return APIResponse.created(
            message=Messages.OPERATION_SUCCESS,
            data=response
        )


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, referencia: str):
        # Con persistencia: consultar estado por referencia
        try:
            tx = PaymentTransaction.objects.filter(referencia=referencia).first()
            if tx:
                return APIResponse.success(
                    message=Messages.OPERATION_SUCCESS,
                    data={
                        "reference": tx.referencia,
                        "status": tx.estado,
                        "method": tx.metodo,
                        "amount": str(tx.monto),
                        "currency": tx.moneda,
                        "description": tx.descripcion,
                        "updated_at": tx.actualizado_en,
                    }
                )
        except Exception as e:
            logger.error(f"Error consultando estado de pago: {e}")

        # Fallback si no existe en BD
        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={"reference": referencia, "status": PaymentStatus.PENDING}
        )


class ConfirmarPagoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConfirmarPagoSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(Messages.INVALID_DATA, errors=serializer.errors)

        token = serializer.validated_data.get("token")
        try:
            payload = verify_payment_token(token)
        except ValueError as e:
            return APIResponse.unauthorized(str(e))

        ref = payload.get("ref")
        method = payload.get("mtd")

        # Actualizar en BD si existe, sino crear como completado
        try:
            rows = PaymentTransaction.objects.filter(referencia=ref).update(estado=PaymentStatus.COMPLETED)
            if rows == 0:
                PaymentTransaction.objects.create(
                    referencia=ref,
                    metodo=method or "QR",
                    monto=Decimal(payload.get("amt", "0")),
                    moneda=str(payload.get("cur", "BOB")),
                    descripcion=str(payload.get("desc", ""))[:120],
                    estado=PaymentStatus.COMPLETED,
                    ip=str(payload.get("ip", ""))[:45],
                    usuario=request.user if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False) else None,
                )
        except Exception as e:
            logger.error(f"No se pudo actualizar/crear transacción al confirmar: {e}")

        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={"reference": ref, "status": PaymentStatus.COMPLETED, "method": method}
        )


# =============== Vistas alineadas al esquema Neon (con autenticación) ===============

class PaymentMethodsDBView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        methods = _fetch_payment_methods_v2()
        serializer = MetodoPagoSerializer(methods, many=True)
        return APIResponse.success(message=Messages.OPERATION_SUCCESS, data={"methods": serializer.data})


class InitiatePaymentDBView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IniciarPagoSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(Messages.INVALID_DATA, errors=serializer.errors)

        data = serializer.validated_data
        try:
            amount = validate_amount(data.get("monto"))
            currency = validate_currency(data.get("moneda"))
        except ValueError as e:
            return APIResponse.bad_request(Messages.INVALID_DATA, errors={"monto": [str(e)]})

        description = sanitize_text(data.get("descripcion") or "")
        reference = sanitize_text(data.get("referencia") or "") or generate_reference()
        id_venta = int(data.get("id_venta"))

        # Validar existencia de la venta antes de insertar (evita FK fallida)
        try:
            if not Venta.objects.filter(id_venta=id_venta).exists():
                return APIResponse.bad_request(
                    message="Venta no encontrada",
                    errors={"id_venta": ["No existe en la base de datos"]}
                )
        except Exception as e:
            logger.error(f"Error validando venta {id_venta}: {e}")
            return APIResponse.server_error(Messages.SERVER_ERROR, detail=str(e))

        # Resolver método: por id o por tipo
        id_metodo_pago = data.get("id_metodo_pago")
        metodo_tipo = (data.get("metodo") or "").upper().strip()
        metodo_row = None
        try:
            if id_metodo_pago is not None:
                metodo_row = MetodoPago.objects.filter(id_metodo_pago=id_metodo_pago, activo=True).first()
            elif metodo_tipo:
                metodo_row = MetodoPago.objects.filter(tipo=metodo_tipo, activo=True).first()
            else:
                metodo_row = MetodoPago.objects.filter(tipo='QR_FISICO', activo=True).first() or \
                             MetodoPago.objects.filter(activo=True).order_by('id_metodo_pago').first()
        except Exception as e:
            logger.warning(f"Error consultando MetodoPago: {e}")
            metodo_row = None

        if not metodo_row:
            return APIResponse.bad_request(Messages.INVALID_DATA, errors={"metodo": ["Método de pago inválido o no disponible."]})

        ip = obtener_ip_cliente(request)

        token_info = sign_payment_token({
            "ref": reference,
            "amt": str(amount),
            "cur": currency,
            "mtd": metodo_row.tipo,
            "mtd_id": metodo_row.id_metodo_pago,
            "uid": getattr(request.user, "id_usuario", getattr(request.user, "id", None)),
            "ip": ip,
            "desc": description,
            "venta": id_venta,
        }, expires_minutes=15)

        response = {
            "reference": reference,
            "method": metodo_row.tipo,
            "method_id": metodo_row.id_metodo_pago,
            "status": PaymentState.PENDIENTE,
            "token": token_info["token"],
            "expires_at": token_info["exp"],
        }

        if 'QR' in metodo_row.tipo:
            response["qr"] = {
                "payload": build_qr_payload(reference, Decimal(str(amount)), currency),
                "hint": "Escanea con tu app bancaria para completar el pago"
            }

        # Insertar en transaccion_pago (usa defaults de BD)
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO transaccion_pago
                        (id_venta, id_metodo_pago, monto, estado_transaccion, referencia_externa, descripcion, procesado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        id_venta,
                        metodo_row.id_metodo_pago,
                        str(amount),
                        PaymentState.PENDIENTE,
                        reference,
                        description,
                        getattr(request.user, 'id_usuario', None),
                    ]
                )
        except Exception as e:
            logger.error(f"No se pudo crear transaccion_pago: {e}")
            return APIResponse.server_error(Messages.SERVER_ERROR, detail=str(e))

        return APIResponse.created(message=Messages.OPERATION_SUCCESS, data=response)


class PaymentStatusDBView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, referencia: str):
        try:
            tx = PaymentTransaction.objects.filter(referencia_externa=referencia).order_by('-fecha_transaccion').first()
            if tx:
                return APIResponse.success(
                    message=Messages.OPERATION_SUCCESS,
                    data={
                        "reference": tx.referencia_externa,
                        "status": tx.estado_transaccion,
                        "method_id": tx.id_metodo_pago,
                        "amount": str(tx.monto),
                        "description": tx.descripcion,
                        "processed_by": tx.procesado_por,
                        "date": tx.fecha_transaccion,
                    }
                )
        except Exception as e:
            logger.error(f"Error consultando estado de pago: {e}")

        return APIResponse.not_found(Messages.NOT_FOUND)


class ConfirmarPagoDBView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConfirmarPagoSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(Messages.INVALID_DATA, errors=serializer.errors)

        token = serializer.validated_data.get("token")
        try:
            payload = verify_payment_token(token)
        except ValueError as e:
            return APIResponse.unauthorized(str(e))

        ref = payload.get("ref")
        method = payload.get("mtd")
        method_id = payload.get("mtd_id")

        try:
            with connections['default'].cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE transaccion_pago
                    SET estado_transaccion = %s, procesado_por = %s
                    WHERE referencia_externa = %s
                    """,
                    [PaymentState.COMPLETADO, getattr(request.user, 'id_usuario', None), ref]
                )
                updated = cursor.rowcount
        except Exception as e:
            logger.error(f"No se pudo confirmar transaccion_pago: {e}")
            return APIResponse.server_error(Messages.SERVER_ERROR, detail=str(e))

        if not updated:
            return APIResponse.not_found(Messages.NOT_FOUND)

        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={"reference": ref, "status": PaymentState.COMPLETADO, "method": method, "method_id": method_id}
        )


