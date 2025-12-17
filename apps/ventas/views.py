from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view
from rest_framework import status
from decimal import Decimal
from stripe import StripeError
import base64
import hashlib
import hmac
import json
import secrets
import stripe

from rest_framework.decorators import action, api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets, status

from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from .models import Venta, DetalleVenta, PaymentTransaction, PaymentState
from apps.pagos.models import MetodoPago
from apps.usuarios.models import Cliente, Vendedor, DireccionCliente
from apps.productos.models import Producto
from apps.envio.models import Envio, TipoEnvio
from apps.autenticacion.utils import obtener_ip_cliente
from apps.bitacora.signals import venta_creada, venta_anulada
from .serializers import (
    VentaPresencialSerializer,
    VentaOnlineSerializer,
    VentaSerializer,
    PaymentTransactionSerializer,
)


stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
def create_payment_intent(request):
    try:
        data = request.data
        amount = data.get('amount')  # en centavos
        currency = data.get('currency', 'usd')

        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Crear el PaymentIntent en Stripe
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            automatic_payment_methods={"enabled": True},
        )

        return Response({
            "clientSecret": intent.client_secret
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

def index(request):
    return JsonResponse({"message": "API de ventas funcionando"})


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload: dict) -> str:
    secret = (getattr(settings, "PAYMENTS_SIGNING_KEY", None) or settings.SECRET_KEY).encode()
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret, blob, hashlib.sha256).digest()
    return f"{_b64url(blob)}.{_b64url(sig)}"


def _verify(token: str) -> dict | None:
    try:
        raw, sig = token.split(".")
        payload = json.loads(_b64url_decode(raw).decode())
        expected = _sign(payload).split(".")[1]
        if not hmac.compare_digest(sig, expected):
            return None
        if "exp" in payload and int(payload["exp"]) < int(timezone.now().timestamp()):
            return None
        return payload
    except Exception:
        return None

# Stripe (opcional)
try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None


class PaymentMethodsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            methods = list(
                MetodoPago.objects.filter(activo=True)
                .values("id_metodo_pago", "tipo", "categoria", "requiere_pasarela")
            )
            return JsonResponse({
                "success": True,
                "message": "Métodos obtenidos",
                "data": {"methods": methods},
            }, status=200)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error al obtener métodos: {e}",
                "data": None,
            }, status=500)


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            body = request.data if hasattr(request, "data") else {}
        except Exception:
            body = {}

        # Validaciones mínimas
        id_venta = body.get("id_venta")
        monto = body.get("monto")
        moneda = (body.get("moneda") or "BOB").upper()
        descripcion = body.get("descripcion") or None
        id_metodo_pago = body.get("id_metodo_pago")
        metodo_nombre = body.get("metodo")  # p.ej. 'QR_FISICO'

        if not id_venta or not monto:
            return JsonResponse({
                "success": False,
                "message": "id_venta y monto son requeridos",
                "data": None,
            }, status=400)

        try:
            venta = Venta.objects.filter(pk=int(id_venta)).first()
            if not venta:
                return JsonResponse({
                    "success": False,
                    "message": "La venta no existe",
                    "data": None,
                }, status=404)

            metodo = None
            if id_metodo_pago:
                metodo = MetodoPago.objects.filter(pk=int(id_metodo_pago), activo=True).first()
            elif metodo_nombre:
                metodo = MetodoPago.objects.filter(tipo=metodo_nombre, activo=True).first()
            if not metodo:
                # Fallback a QR_FISICO si existe, sino primer método activo
                metodo = (
                    MetodoPago.objects.filter(tipo="QR_FISICO", activo=True).first()
                    or MetodoPago.objects.filter(activo=True).first()
                )
            if not metodo:
                return JsonResponse({
                    "success": False,
                    "message": "No hay métodos de pago activos",
                    "data": None,
                }, status=400)

            reference = body.get("referencia") or f"PAY-{id_venta}-{secrets.token_hex(6).upper()}"

            # Reglas de negocio: evitar pagos sobreventa
            total_venta = Decimal(str(venta.monto_total or 0))
            total_pagado = (
                PaymentTransaction.objects.filter(id_venta=int(id_venta), estado_transaccion=PaymentState.COMPLETADO)
                .aggregate(total=Sum("monto"))
                .get("total")
                or Decimal("0")
            )
            saldo = total_venta - total_pagado
            req_monto = Decimal(str(monto))

            if total_venta > 0 and saldo <= 0:
                return JsonResponse({
                    "success": False,
                    "message": "La venta ya está completamente pagada",
                    "data": {"order_total": str(total_venta), "paid_total": str(total_pagado), "remaining": "0"},
                }, status=409)

            if total_venta > 0 and req_monto > saldo:
                return JsonResponse({
                    "success": False,
                    "message": "El monto excede el saldo pendiente",
                    "data": {"order_total": str(total_venta), "paid_total": str(total_pagado), "remaining": str(saldo)},
                }, status=400)

            trans = PaymentTransaction.objects.create(
                id_venta=int(id_venta),
                id_metodo_pago=int(metodo.id_metodo_pago),
                monto=Decimal(str(monto)),
                fecha_transaccion=timezone.now(),
                estado_transaccion=PaymentState.PENDIENTE,
                referencia_externa=reference,
                descripcion=descripcion,
                procesado_por=(getattr(request.user, "id", None) if not request.user.is_anonymous else None),
            )

            exp_ts = int(timezone.now().timestamp()) + int(getattr(settings, "PAYMENTS_TOKEN_TTL", 15 * 60))
            payload = {"ref": reference, "exp": exp_ts, "uid": getattr(request.user, "id", 0)}
            token = _sign(payload)

            data_resp = {
                "success": True,
                "message": "Pago iniciado",
                "data": {
                    "reference": reference,
                    "method": metodo.tipo,
                    "method_id": int(metodo.id_metodo_pago),
                    "status": trans.estado_transaccion,
                    "token": token,
                    "expires_at": exp_ts,
                    "order_total": str(total_venta),
                    "paid_total": str(total_pagado),
                    "remaining": str((saldo - req_monto) if total_venta > 0 else Decimal("0")),
                },
            }

            # Solo incluir QR si el método es QR
            if metodo.tipo and "QR" in str(metodo.tipo).upper():
                data_resp["data"]["qr"] = {
                    "payload": f"QR|REF={reference}|AMT={monto}|CUR={moneda}",
                    "hint": "Escanea para pagar o usa referencia",
                }

            return JsonResponse(data_resp, status=201)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error al iniciar pago: {e}",
                "data": None,
            }, status=500)


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, referencia: str):
        try:
            trans = PaymentTransaction.objects.filter(referencia_externa=referencia).first()
            if not trans:
                return JsonResponse({
                    "success": False,
                    "message": "Referencia no encontrada",
                    "data": None,
                }, status=404)
            return JsonResponse({
                "success": True,
                "message": "Estado obtenido",
                "data": {
                    "reference": referencia,
                    "status": trans.estado_transaccion,
                    "method_id": int(trans.id_metodo_pago),
                    "amount": str(trans.monto),
                    "description": trans.descripcion,
                    "processed_by": trans.procesado_por,
                    "date": trans.fecha_transaccion.isoformat() if trans.fecha_transaccion else None,
                },
            }, status=200)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error al consultar estado: {e}",
                "data": None,
            }, status=500)


class PaymentTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("page_size", 20))
        queryset = PaymentTransaction.objects.all()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PaymentTransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ConfirmarPagoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            body = request.data if hasattr(request, "data") else {}
        except Exception:
            body = {}

        token = body.get("token")
        if not token:
            return JsonResponse({
                "success": False,
                "message": "Token requerido",
                "data": None,
            }, status=400)

        payload = _verify(token)
        if not payload:
            return JsonResponse({
                "success": False,
                "message": "Token inválido o expirado",
                "data": None,
            }, status=401)

        referencia = payload.get("ref")
        try:
            trans = PaymentTransaction.objects.filter(referencia_externa=referencia).first()
            if not trans:
                return JsonResponse({
                    "success": False,
                    "message": "Referencia no encontrada",
                    "data": None,
                }, status=404)

            if trans.estado_transaccion == PaymentState.COMPLETADO:
                return JsonResponse({
                    "success": True,
                    "message": "Pago ya estaba completado",
                    "data": {"reference": referencia, "status": trans.estado_transaccion},
                }, status=200)

            trans.estado_transaccion = PaymentState.COMPLETADO
            # Registrar quién confirmó si hay usuario
            if request.user and not request.user.is_anonymous:
                trans.procesado_por = getattr(request.user, "id", trans.procesado_por)
            trans.save(update_fields=["estado_transaccion", "procesado_por"])

            # Si la venta tiene total y ya se alcanzó o superó, marcarla como COMPLETADA
            venta = Venta.objects.filter(pk=trans.id_venta).first()
            if venta and venta.monto_total is not None:
                total_venta = Decimal(str(venta.monto_total or 0))
                total_pagado = (
                    PaymentTransaction.objects.filter(id_venta=trans.id_venta, estado_transaccion=PaymentState.COMPLETADO)
                    .aggregate(total=Sum("monto"))
                    .get("total")
                    or Decimal("0")
                )
                if total_pagado >= total_venta and getattr(venta, "estado", None) is not None:
                    try:
                        # Update directo sin cargar todos los campos
                        Venta.objects.filter(pk=trans.id_venta).update(estado="COMPLETADO")
                    except Exception:
                        pass

            return JsonResponse({
                "success": True,
                "message": "Pago confirmado",
                "data": {
                    "reference": referencia,
                    "status": trans.estado_transaccion,
                    "method_id": int(trans.id_metodo_pago),
                },
            }, status=200)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error al confirmar pago: {e}",
                "data": None,
            }, status=500)


# Alias de compatibilidad para rutas *DBView
PaymentMethodsDBView = PaymentMethodsView
InitiatePaymentDBView = InitiatePaymentView
PaymentStatusDBView = PaymentStatusView
ConfirmarPagoDBView = ConfirmarPagoView


class VentaPaymentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_venta: int):
        try:
            venta = Venta.objects.filter(pk=int(id_venta)).first()
            if not venta:
                return JsonResponse({
                    "success": False,
                    "message": "Venta no encontrada",
                    "data": None,
                }, status=404)

            total_venta = Decimal(str(venta.monto_total or 0))
            total_pagado = (
                PaymentTransaction.objects.filter(id_venta=int(id_venta), estado_transaccion=PaymentState.COMPLETADO)
                .aggregate(total=Sum("monto"))
                .get("total")
                or Decimal("0")
            )
            remaining = total_venta - total_pagado
            if remaining < 0:
                remaining = Decimal("0")

            txs = list(
                PaymentTransaction.objects.filter(id_venta=int(id_venta))
                .order_by("-fecha_transaccion")
                .values(
                    "id_transaccion",
                    "monto",
                    "estado_transaccion",
                    "id_metodo_pago",
                    "referencia_externa",
                    "fecha_transaccion",
                )
            )

            # Normalizar montos y fechas para el frontend
            for t in txs:
                t["amount"] = str(t.pop("monto"))
                if t.get("fecha_transaccion"):
                    t["date"] = t["fecha_transaccion"].isoformat()
                t.pop("fecha_transaccion", None)

            status = getattr(venta, "estado", None)
            if status is None:
                status = "COMPLETADO" if total_pagado >= total_venta > 0 else "PENDIENTE"

            return JsonResponse({
                "success": True,
                "message": "Resumen de pago",
                "data": {
                    "order_id": int(id_venta),
                    "order_total": str(total_venta),
                    "paid_total": str(total_pagado),
                    "remaining": str(remaining),
                    "status": status,
                    "transactions": txs,
                },
            }, status=200)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error al obtener resumen: {e}",
                "data": None,
            }, status=500)


class StripeCreateIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if stripe is None:
            return JsonResponse({
                "success": False,
                "message": "Stripe SDK no instalado en el backend. Ejecuta: pip install stripe",
                "data": None,
            }, status=501)

        secret_key = getattr(settings, "STRIPE_SECRET_KEY", None)
        currency = getattr(settings, "STRIPE_CURRENCY", "usd").lower()
        if not secret_key:
            return JsonResponse({
                "success": False,
                "message": "Stripe no está configurado (falta STRIPE_SECRET_KEY)",
                "data": None,
            }, status=503)

        try:
            body = request.data if hasattr(request, "data") else {}
        except Exception:
            body = {}

        id_venta = body.get("id_venta")
        monto = body.get("monto")  # Decimal o float
        descripcion = body.get("descripcion") or None
        if not id_venta or not monto:
            return JsonResponse({
                "success": False,
                "message": "id_venta y monto son requeridos",
                "data": None,
            }, status=400)

        try:
            venta = Venta.objects.filter(pk=int(id_venta)).first()
            if not venta:
                return JsonResponse({
                    "success": False,
                    "message": "La venta no existe",
                    "data": None,
                }, status=404)

            # Políticas de saldo
            total_venta = Decimal(str(venta.monto_total or 0))
            total_pagado = (
                PaymentTransaction.objects.filter(id_venta=int(id_venta), estado_transaccion=PaymentState.COMPLETADO)
                .aggregate(total=Sum("monto"))
                .get("total")
                or Decimal("0")
            )
            saldo = total_venta - total_pagado
            req_monto = Decimal(str(monto))
            if total_venta > 0 and saldo <= 0:
                return JsonResponse({
                    "success": False,
                    "message": "La venta ya está completamente pagada",
                    "data": {"order_total": str(total_venta), "paid_total": str(total_pagado), "remaining": "0"},
                }, status=409)
            if total_venta > 0 and req_monto > saldo:
                return JsonResponse({
                    "success": False,
                    "message": "El monto excede el saldo pendiente",
                    "data": {"order_total": str(total_venta), "paid_total": str(total_pagado), "remaining": str(saldo)},
                }, status=400)

            # Resolver método Stripe
            metodo = (
                MetodoPago.objects.filter(requiere_pasarela=True, codigo_pasarela__iexact="STRIPE", activo=True).first()
                or MetodoPago.objects.filter(tipo__iexact="TARJETA", activo=True).first()
                or MetodoPago.objects.filter(tipo__icontains="CARD", activo=True).first()
            )
            metodo_id = int(metodo.id_metodo_pago) if metodo else None

            # Crear transacción PENDIENTE (referencia será el PaymentIntent id)
            trans = PaymentTransaction.objects.create(
                id_venta=int(id_venta),
                id_metodo_pago=int(metodo_id or 0),
                monto=req_monto,
                fecha_transaccion=timezone.now(),
                estado_transaccion=PaymentState.PENDIENTE,
                referencia_externa=None,
                descripcion=descripcion,
                procesado_por=(getattr(request.user, "id", None) if not request.user.is_anonymous else None),
            )

            # Crear PaymentIntent en centavos/unidad mínima
            stripe.api_key = secret_key
            amount_minor = int(Decimal(str(req_monto)) * 100)
            intent = stripe.PaymentIntent.create(
                amount=amount_minor,
                currency=currency,
                description=descripcion or f"Venta {id_venta}",
                metadata={
                    "id_venta": str(id_venta),
                    "id_transaccion": str(trans.id_transaccion),
                },
                automatic_payment_methods={"enabled": True},
            )

            # Guardar referencia (PaymentIntent ID)
            trans.referencia_externa = intent.get("id")
            trans.save(update_fields=["referencia_externa"])

            return JsonResponse({
                "success": True,
                "message": "Stripe intent creado",
                "data": {
                    "reference": intent.get("id"),
                    "client_secret": intent.get("client_secret"),
                    "status": trans.estado_transaccion,
                    "method": "TARJETA",
                    "method_id": metodo_id,
                    "order_total": str(total_venta),
                    "paid_total": str(total_pagado),
                    "remaining": str((saldo - req_monto) if total_venta > 0 else Decimal("0")),
                },
            }, status=201)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error Stripe: {e}",
                "data": None,
            }, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if stripe is None:
            return JsonResponse({"success": False, "message": "Stripe SDK no instalado", "data": None}, status=501)

        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                event = json.loads(payload.decode())
        except Exception as e:
            return HttpResponse(status=400, content=str(e))

        try:
            if event.get("type") == "payment_intent.succeeded":
                intent = event["data"]["object"]
                pi_id = intent.get("id")
                metadata = intent.get("metadata") or {}
                trans = PaymentTransaction.objects.filter(referencia_externa=pi_id).first()
                if trans:
                    if trans.estado_transaccion != PaymentState.COMPLETADO:
                        trans.estado_transaccion = PaymentState.COMPLETADO
                        trans.save(update_fields=["estado_transaccion"])

                        # Cerrar venta si corresponde
                        venta = Venta.objects.filter(pk=trans.id_venta).first()
                        if venta and venta.monto_total is not None:
                            total_venta = Decimal(str(venta.monto_total or 0))
                            total_pagado = (
                                PaymentTransaction.objects.filter(id_venta=trans.id_venta, estado_transaccion=PaymentState.COMPLETADO)
                                .aggregate(total=Sum("monto"))
                                .get("total")
                                or Decimal("0")
                            )
                            if total_pagado >= total_venta and getattr(venta, "estado", None) is not None:
                                try:
                                    Venta.objects.filter(pk=trans.id_venta).update(estado="COMPLETADO")
                                except Exception:
                                    pass
            elif event.get("type") == "payment_intent.payment_failed":
                intent = event["data"]["object"]
                pi_id = intent.get("id")
                last_err = intent.get("last_payment_error") or {}
                code = last_err.get("code") or last_err.get("type") or "PAYMENT_FAILED"
                trans = PaymentTransaction.objects.filter(referencia_externa=pi_id).first()
                if trans and trans.estado_transaccion != PaymentState.COMPLETADO:
                    trans.estado_transaccion = PaymentState.FALLIDO
                    trans.codigo_error = code[:50]
                    trans.save(update_fields=["estado_transaccion", "codigo_error"])
        except Exception:
            # No arruinamos el webhook; Stripe reintentará si falla
            pass

        return HttpResponse(status=200)


# apps/ventas/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404
from datetime import date


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def crear_venta_presencial(request):
    """
    Registrar una venta presencial manual, SIN carrito y SIN búsqueda interna de cliente.
    El cliente debe venir como ID (opcional).
    """

    # 1. Validar que el usuario sea vendedor o admin con perfil de vendedor
    vendedor = None
    try:
        vendedor = Vendedor.objects.get(id_vendedor=request.user.id_usuario)
    except Vendedor.DoesNotExist:
        es_admin = request.user.is_superuser or request.user.is_staff
        if es_admin:
            return Response(
                {"error": "Este usuario administrador no tiene un perfil de vendedor asociado para registrar la venta."},
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            return Response(
                {"error": "Solo un vendedor puede registrar ventas."},
                status=status.HTTP_403_FORBIDDEN
            )

    # 2. Validar datos recibidos
    serializer = VentaPresencialSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    cliente_id = data.get("cliente_id")
    metodo_pago_id = data["metodo_pago"]
    productos_data = data["productos"]

    # 3. Cliente (opcional)
    cliente = None
    if cliente_id:
        cliente = Cliente.objects.filter(id_cliente=cliente_id).first()
        if not cliente:
            return Response(
                {"error": "El cliente enviado no existe."},
                status=400
            )

    # 4. Verificar método de pago
    metodo_pago = MetodoPago.objects.filter(id_metodo_pago=metodo_pago_id).first()
    if not metodo_pago:
        return Response(
            {"error": "Método de pago inválido."},
            status=400
        )

    # 5. Validar productos + stock y calcular total
    items_validos = []
    monto_total = 0

    for item in productos_data:
        id_producto = item.get("id_producto")
        cantidad = item.get("cantidad")

        producto = Producto.objects.filter(id_producto=id_producto).first()
        if not producto:
            return Response({"error": f"El producto {id_producto} no existe."}, status=400)

        if producto.stock < cantidad:
            return Response({"error": f"Stock insuficiente para {producto.nombre}"}, status=400)

        sub_total = producto.precio * cantidad
        monto_total += sub_total

        items_validos.append({
            "producto": producto,
            "cantidad": cantidad,
            "precio": producto.precio,
            "sub_total": sub_total
        })

    # 6. Crear Venta
    venta = Venta.objects.create(
        fecha=date.today(),
        monto_total=monto_total,
        estado="COMPLETADO",   # venta presencial siempre se cierra
        id_metodo_pago=metodo_pago,
        id_cliente=cliente,
        id_vendedor=vendedor,
        id_promocion=None,
        cod_envio=None
    )

    # 7. Crear Detalles + descontar stock
    for item in items_validos:
        DetalleVenta.objects.create(
            id_venta=venta,
            id_producto=item["producto"],
            cantidad=item["cantidad"],
            precio=item["precio"],
            sub_total=item["sub_total"],
            id_lote=None
        )

        # Actualizar stock del producto
        p = item["producto"]
        p.stock -= item["cantidad"]
        p.save()

    # 8. Registrar bitácora
    ip = obtener_ip_cliente(request)
    venta_creada.send(
        sender=Venta,
        venta=venta,
        usuario=request.user,
        ip=ip
    )

    # 9. Respuesta final
    from apps.ventas.serializers import VentaSerializer
    return Response(
        {
            "message": "Venta presencial registrada correctamente.",
            "venta": VentaSerializer(venta).data
        },
        status=201
    )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def anular_venta(request, id_venta):

    # 1 Verificar si es vendedor o admin
    es_admin = request.user.is_superuser or request.user.is_staff
    es_vendedor = Vendedor.objects.filter(id_vendedor=request.user.id_usuario).exists()

    if not (es_admin or es_vendedor):
        return Response(
            {"error": "No tiene permisos para anular una venta."},
            status=status.HTTP_403_FORBIDDEN
        )

    # 2 Obtener la venta
    venta = get_object_or_404(Venta, id_venta=id_venta)

    # 3 Validar si ya está anulada
    if venta.estado == "ANULADA":
        return Response(
            {"error": "La venta ya se encuentra anulada."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 4 Validar estados permitidos
    if venta.estado not in ["PENDIENTE", "COMPLETADO"]:
        return Response(
            {"error": f"No se puede anular una venta con estado {venta.estado}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 5 Revertir stock
    detalles = venta.detalles.all()

    for det in detalles:
        producto = det.id_producto
        producto.stock += det.cantidad
        producto.save()

    # 6 Cambiar estado de venta
    venta.estado = "ANULADA"
    venta.save()

    ip= obtener_ip_cliente(request)
    venta_anulada.send(
        sender=Venta,
        venta=venta,
        usuario=request.user,
        ip=ip
    )

    return Response(
        {
            "message": "Venta anulada correctamente",
            "venta": {
                "id_venta": venta.id_venta,
                "estado": venta.estado
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_venta(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    serializer = VentaSerializer(venta)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_ventas(request):

    # Verificar acceso (admin o vendedor)
    es_admin = request.user.is_superuser or request.user.is_staff
    es_vendedor = Vendedor.objects.filter(id_vendedor=request.user.id_usuario).exists()

    if not (es_admin or es_vendedor):
        return Response(
            {"error": "No tiene permisos para ver las ventas."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Configuración de la paginación
    paginator = PageNumberPagination()
    paginator.page_size = 15  # Puedes ajustar este número según tus necesidades

    ventas = Venta.objects.all().order_by('-id_venta')
    paginated_ventas = paginator.paginate_queryset(ventas, request)

    serializer = VentaSerializer(paginated_ventas, many=True)

    # La respuesta paginada ya incluye 'count', 'next', 'previous' y 'results'
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def confirmar_pago_manual(request, id_venta):

    # Verificar permisos (admin o vendedor)
    es_admin = request.user.is_superuser or request.user.is_staff
    es_vendedor = Vendedor.objects.filter(id_vendedor=request.user.id_usuario).exists()

    if not (es_admin or es_vendedor):
        return Response(
            {"error": "No tiene permisos para confirmar el pago."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Obtener venta
    venta = get_object_or_404(Venta, id_venta=id_venta)

    # Validar estados
    if venta.estado == "ANULADA":
        return Response({"error": "No se puede confirmar pago de una venta anulada."},
                        status=status.HTTP_400_BAD_REQUEST)

    if venta.estado == "COMPLETADO":
        return Response({"error": "La venta ya está completada."},
                        status=status.HTTP_400_BAD_REQUEST)

    # Marcar como completado
    venta.estado = "COMPLETADO"
    venta.save()

    return Response({
        "success": True,
        "message": "Pago confirmado correctamente.",
        "venta": VentaSerializer(venta).data
    }, status=200)
    
class VentaOnlineView(APIView):
    """
    Vista para gestionar la creación de ventas desde el carrito del cliente (online).
    """
    permission_classes = [IsAuthenticated]
 
    @transaction.atomic
    def post(self, request):
        print("🔍 [DEBUG] === INICIO VentaOnlineView ===")
        print(f"🔍 [DEBUG] Request data recibido: {request.data}")
        
        serializer = VentaOnlineSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ [ERROR] Validación del serializer falló: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        productos_data = data["productos"]
        id_direccion = data["id_direccion"]
        
        print(f"✅ [DEBUG] Datos validados - Productos: {len(productos_data)}, Dirección: {id_direccion}")

        # 1. Validar que el usuario sea un cliente
        try:
            cliente = Cliente.objects.get(id_cliente=request.user.id_usuario)
            print(f"✅ [DEBUG] Cliente encontrado: {cliente.id_cliente}")
        except Cliente.DoesNotExist:
            print(f"❌ [ERROR] Usuario {request.user.id_usuario} no es un cliente")
            return Response({"error": "El usuario no es un cliente válido."}, status=status.HTTP_403_FORBIDDEN)

        # 2. Validar dirección
        direccion = DireccionCliente.objects.filter(id_direccion=id_direccion, id_cliente=cliente).first()
        if not direccion:
            print(f"❌ [ERROR] Dirección {id_direccion} no encontrada para cliente {cliente.id_cliente}")
            return Response({"error": "La dirección de envío no es válida o no pertenece a este cliente."}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"✅ [DEBUG] Dirección validada: {direccion.id_direccion}")

        # 3. Validar productos, stock y calcular total
        monto_total = Decimal('0')
        detalles_para_crear = []
        
        print(f"🔍 [DEBUG] Validando {len(productos_data)} productos...")
        
        for idx, item in enumerate(productos_data):
            print(f"🔍 [DEBUG] Producto {idx+1}: ID={item['id_producto']}, Cantidad={item['cantidad']}")
            
            try:
                producto = Producto.objects.get(id_producto=item['id_producto'])
                print(f"✅ [DEBUG] Producto encontrado: {producto.nombre}, Stock: {producto.stock}, Precio: {producto.precio}")
            except Producto.DoesNotExist:
                print(f"❌ [ERROR] Producto {item['id_producto']} no existe")
                return Response({"error": f"El producto {item['id_producto']} no existe."}, status=status.HTTP_400_BAD_REQUEST)
            
            if producto.stock < item['cantidad']:
                print(f"❌ [ERROR] Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}, Requerido: {item['cantidad']}")
                return Response({"error": f"Stock insuficiente para el producto: {producto.nombre}"}, status=status.HTTP_400_BAD_REQUEST)
            
            subtotal = producto.precio * item['cantidad']
            monto_total += subtotal
            
            print(f"✅ [DEBUG] Subtotal calculado: {subtotal}, Total acumulado: {monto_total}")
            
            detalles_para_crear.append({
                "producto": producto,
                "cantidad": item['cantidad'],
                "precio": producto.precio,
                "subtotal": subtotal
            })

        print(f"✅ [DEBUG] Monto total de la venta: {monto_total}")

        # Obtener el método de pago para ventas online (ID 5)
        try:
            metodo_pago_online = MetodoPago.objects.get(id_metodo_pago=5)
            print(f"✅ [DEBUG] Método de pago encontrado: {metodo_pago_online.tipo}")
        except MetodoPago.DoesNotExist:
            print("❌ [ERROR] Método de pago con ID 5 no existe")
            return Response({"error": "El método de pago no está configurado correctamente."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Obtener el vendedor por defecto (ID 3)
        try:
            vendedor_online = Vendedor.objects.get(id_vendedor=3)
            print(f"✅ [DEBUG] Vendedor online encontrado: {vendedor_online.id_vendedor}")
        except Vendedor.DoesNotExist:
            print("❌ [ERROR] Vendedor con ID 3 no existe")
            return Response({"error": "El vendedor del sistema no está configurado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Crear el registro de Envío
        try:
            tipo_envio_domicilio = TipoEnvio.objects.get(cod_tipo_envio=1)
            print(f"✅ [DEBUG] Tipo de envío encontrado: {tipo_envio_domicilio.cod_tipo_envio}")
        except TipoEnvio.DoesNotExist:
            print("❌ [ERROR] TipoEnvio con cod_tipo_envio=1 no existe")
            return Response({"error": "El tipo de envío no está configurado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        print("🔍 [DEBUG] Creando registro de envío...")
        nuevo_envio = Envio.objects.create(
            cod_tipo_envio=tipo_envio_domicilio,
            estado_envio='EN PREPARACION',
            id_direccion=direccion,
            fecha_envio=date.today(),
            costo=Decimal('0.00')
        )
        print(f"✅ [DEBUG] Envío creado con ID: {nuevo_envio.cod_envio}")

        # 5. Crear la venta
        print("🔍 [DEBUG] Creando venta...")
        venta = Venta.objects.create(
            fecha=date.today(),
            id_cliente=cliente,
            monto_total=monto_total,
            estado='PENDIENTE',
            id_vendedor=vendedor_online,
            id_promocion=None,
            cod_envio=nuevo_envio,
            id_metodo_pago=metodo_pago_online, 
        )
        print(f"✅ [DEBUG] Venta creada con ID: {venta.id_venta}")

        # 6. Crear detalles y descontar stock
        print("🔍 [DEBUG] Creando detalles de venta...")
        for detalle_data in detalles_para_crear:
            DetalleVenta.objects.create(
                id_venta=venta,
                id_producto=detalle_data['producto'],
                cantidad=detalle_data['cantidad'],
                precio=detalle_data['precio'],
                sub_total=detalle_data['subtotal']
            )
            detalle_data['producto'].stock -= detalle_data['cantidad']
            detalle_data['producto'].save()
            print(f"✅ [DEBUG] Detalle creado para producto: {detalle_data['producto'].nombre}")

        # 7. Iniciar el pago con Stripe
        print("🔍 [DEBUG] Iniciando proceso de pago con Stripe...")
        try:
            # Verificar que la API key esté configurada
            if not settings.STRIPE_SECRET_KEY:
                print("❌ [ERROR] STRIPE_SECRET_KEY no está configurada en settings.py")
                return Response(
                    {"error": "El sistema de pagos no está configurado. Contacta al administrador."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Crear la transacción de pago pendiente
            trans = PaymentTransaction.objects.create(
                id_venta=venta.id_venta,
                id_metodo_pago=metodo_pago_online.id_metodo_pago,
                monto=monto_total,
                fecha_transaccion=timezone.now(),
                estado_transaccion=PaymentState.PENDIENTE,
                descripcion=f"Intento de pago para Venta #{venta.id_venta}",
            )
            print(f"✅ [DEBUG] Transacción creada con ID: {trans.id_transaccion}")

            # Configurar Stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            currency = getattr(settings, "STRIPE_CURRENCY", "usd").lower()
            
            # Convertir correctamente el monto a centavos
            amount_cents = int(float(monto_total) * 100)
            print(f"🔍 [DEBUG] Monto en centavos: {amount_cents}, Moneda: {currency}")
            
            # Crear el PaymentIntent en Stripe
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                description=f"Pago de orden #{venta.id_venta}",
                metadata={
                    "id_venta": str(venta.id_venta),
                    "id_transaccion": str(trans.id_transaccion),
                },
                automatic_payment_methods={"enabled": True},
            )
            print(f"✅ [DEBUG] PaymentIntent creado: {intent.get('id')}")

            # Guardar la referencia de Stripe
            trans.referencia_externa = intent.get("id")
            trans.save(update_fields=["referencia_externa"])
            print(f"✅ [DEBUG] Referencia guardada en transacción")

        except StripeError as e:  # ← CORREGIDO
            print(f"❌ [ERROR] Error de Stripe: {str(e)}")
            return Response(
                {"error": f"Error al procesar el pago con Stripe: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            print(f"❌ [ERROR] Error inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Ocurrió un error inesperado al iniciar el pago: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 8. Respuesta exitosa
        print(f"✅ [DEBUG] Proceso completado exitosamente")
        return Response({
            "client_secret": intent.get("client_secret"),
            "reference": intent.get("id"),
            "id_venta": venta.id_venta
        }, status=status.HTTP_201_CREATED)
