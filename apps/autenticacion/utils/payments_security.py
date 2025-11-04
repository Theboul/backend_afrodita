"""
Utilidades de seguridad para pagos.
Incluye validaciones, firmado/verificación de tokens y generación de referencias.
"""

import base64
import hmac
import hashlib
import json
import re
import time
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings


ALLOWED_CURRENCIES = {"BOB", "USD"}


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def _get_secret_key() -> bytes:
    secret = getattr(settings, "JWT_SECRET_KEY", None) or getattr(settings, "SECRET_KEY", "")
    return str(secret).encode("utf-8")


def sanitize_text(value: str, max_len: int = 120) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9 .,_\-]", "", value)
    return value[:max_len]


def validate_amount(amount) -> Decimal:
    try:
        dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if dec <= Decimal("0.00"):
            raise ValueError("El monto debe ser mayor a 0")
        return dec
    except (InvalidOperation, ValueError):
        raise ValueError("Monto inválido")


def validate_currency(currency: str) -> str:
    if not currency:
        raise ValueError("Moneda requerida")
    cur = currency.upper().strip()
    if cur not in ALLOWED_CURRENCIES:
        raise ValueError("Moneda no soportada")
    return cur


def generate_reference(prefix: str = "PAY") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def sign_payment_token(payload: dict, expires_minutes: int = 15) -> dict:
    """
    Firma un token simple (tipo JWT minimalista) con HMAC-SHA256.
    Retorna dict con token y exp (epoch seconds).
    """
    now = int(time.time())
    exp = now + int(expires_minutes * 60)
    body = dict(payload)
    body.update({
        "iat": now,
        "exp": exp,
        "nonce": uuid.uuid4().hex,
    })

    body_json = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body_b64 = _b64url_encode(body_json)
    secret = _get_secret_key()
    sig = hmac.new(secret, body_json, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    token = f"{body_b64}.{sig_b64}"
    return {"token": token, "exp": exp}


def verify_payment_token(token: str) -> dict:
    """
    Verifica token firmado y retorna el payload si es válido.
    Lanza ValueError si es inválido o expirado.
    """
    try:
        body_b64, sig_b64 = token.split(".")
    except ValueError:
        raise ValueError("Token inválido")

    body_json = _b64url_decode(body_b64)
    expected_sig = hmac.new(_get_secret_key(), body_json, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
        raise ValueError("Firma inválida")

    body = json.loads(body_json.decode("utf-8"))
    if int(body.get("exp", 0)) < int(time.time()):
        raise ValueError("Token expirado")
    return body


def build_qr_payload(reference: str, amount: Decimal, currency: str) -> str:
    """Genera un payload de texto simple para QR (simulado)."""
    return f"QR|REF={reference}|AMT={amount}|CUR={currency}"

