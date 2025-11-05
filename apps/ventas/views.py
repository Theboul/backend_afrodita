from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view
from rest_framework import status
from decimal import Decimal
import base64
import hashlib
import hmac
import json
import secrets
import stripe

from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import viewsets, status

from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from .models import MetodoPago, PaymentTransaction, Venta, PaymentState

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
