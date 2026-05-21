import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.database import db_client
from schemas.usuario import usuario_public_schema

dotenv_path = os.path.join(os.path.dirname(__file__), "config.env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY no encontrada en variables de entorno")

JWT_SECRET_KEY = JWT_SECRET_KEY.strip()
JWT_ALGORITHM = "HS256"
SESSION_HOURS = 12
PERMISSION_LEVELS = {"normal": 1, "elevado": 2, "admin": 3}

security = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _json_default(value):
    if isinstance(value, datetime):
        return int(value.timestamp())
    raise TypeError(f"Tipo no serializable: {type(value)!r}")


def crear_jwt(payload: dict) -> str:
    header = {"typ": "JWT", "alg": JWT_ALGORITHM}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), default=_json_default).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decodificar_jwt(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        supplied = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected, supplied):
            raise _auth_error("TOKEN_INVALID", "Token invalido")
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != JWT_ALGORITHM:
            raise _auth_error("TOKEN_INVALID", "Algoritmo invalido")
        payload = json.loads(_b64url_decode(payload_b64))
    except HTTPException:
        raise
    except Exception:
        raise _auth_error("TOKEN_INVALID", "Token invalido")

    exp = payload.get("exp")
    if exp is None or _utc_now().timestamp() > float(exp):
        raise _auth_error("TOKEN_EXPIRED", "Sesion expirada")
    return payload


def crear_sesion(usuario: dict) -> dict:
    now = _utc_now()
    expires_at = now + timedelta(hours=SESSION_HOURS)
    session_id = secrets.token_urlsafe(32)
    user_id = str(usuario["_id"])

    db_client.pbstation.sesiones.insert_one(
        {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": _naive_utc(now),
            "expires_at": _naive_utc(expires_at),
            "revoked": False,
        }
    )

    token = crear_jwt(
        {
            "sub": user_id,
            "sid": session_id,
            "permisos": usuario.get("permisos", "normal"),
            "rol": usuario.get("rol", "vendedor"),
            "exp": int(expires_at.timestamp()),
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": _naive_utc(expires_at).isoformat(),
        "usuario": usuario_public_schema(usuario),
    }


def revocar_sesion(session_id: str) -> None:
    db_client.pbstation.sesiones.update_one(
        {"session_id": session_id},
        {"$set": {"revoked": True, "revoked_at": _naive_utc(_utc_now())}},
    )


def revocar_sesiones_usuario(user_id: str) -> None:
    db_client.pbstation.sesiones.update_many(
        {"user_id": user_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": _naive_utc(_utc_now())}},
    )


def _auth_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def validar_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _auth_error("TOKEN_MISSING", "Token requerido")

    payload = decodificar_jwt(credentials.credentials)
    user_id = payload.get("sub")
    session_id = payload.get("sid")
    if not user_id or not session_id:
        raise _auth_error("TOKEN_INVALID", "Token incompleto")

    session = db_client.pbstation.sesiones.find_one({"session_id": session_id})
    if not session or session.get("revoked"):
        raise _auth_error("SESSION_REVOKED", "Sesion revocada")

    expires_at = session.get("expires_at")
    if expires_at and datetime.utcnow() > expires_at:
        revocar_sesion(session_id)
        raise _auth_error("TOKEN_EXPIRED", "Sesion expirada")

    try:
        usuario = db_client.pbstation.usuarios.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise _auth_error("TOKEN_INVALID", "Usuario invalido")
    if not usuario or not usuario.get("activo", True):
        raise _auth_error("USER_INACTIVE", "Usuario inactivo")

    usuario["session_id"] = session_id
    return usuario


def require_permission(required: str) -> Callable:
    required_level = PERMISSION_LEVELS[required]

    def dependency(usuario: dict = Depends(validar_token)) -> dict:
        current_level = PERMISSION_LEVELS.get(usuario.get("permisos", "normal"), 0)
        if current_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {required}",
            )
        return usuario

    return dependency
