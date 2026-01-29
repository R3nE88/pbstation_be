from dotenv import load_dotenv
import os
import hmac
import hashlib
import time
from fastapi import HTTPException, status, Header

dotenv_path = os.path.join(os.path.dirname(__file__), "config.env")
load_dotenv(dotenv_path=dotenv_path)
SECRET_KEY = os.getenv("SECRET_KEY")

if SECRET_KEY is None:
    raise ValueError("SECRET_KEY no encontrada en las variables de entorno. Verifica tu archivo config.env")

SECRET_KEY = SECRET_KEY.strip()

# Tolerancia de tiempo en segundos (60 segundos = 1 minuto)
TIMESTAMP_TOLERANCE_SECONDS = 60

def validar_token(
    x_timestamp: str = Header(None, description="Timestamp de la petición en milisegundos"),
    x_signature: str = Header(None, description="Firma HMAC-SHA256")
):
    """
    Valida la autenticación usando HMAC-SHA256 con timestamp.
    
    El cliente debe enviar:
    - x-timestamp: Tiempo Unix en milisegundos cuando se hizo la petición
    - x-signature: HMAC-SHA256(timestamp, secret_key)
    
    Beneficios:
    - El secret nunca viaja por la red
    - Cada request tiene un signature único
    - Los requests capturados expiran en 60 segundos
    """
    # Validar que los headers existen
    if not x_timestamp or not x_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Headers de autenticación faltantes (x-timestamp, x-signature)"
        )
    
    # Validar que el timestamp no haya expirado
    try:
        request_time = int(x_timestamp) / 1000  # Convertir de milisegundos a segundos
        current_time = time.time()
        time_difference = abs(current_time - request_time)
        
        if time_difference > TIMESTAMP_TOLERANCE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Request expirado (diferencia: {time_difference:.1f}s, máximo: {TIMESTAMP_TOLERANCE_SECONDS}s)"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timestamp inválido"
        )
    
    # Recalcular la firma esperada
    expected_signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        x_timestamp.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Comparar firmas de forma segura (previene timing attacks)
    if not hmac.compare_digest(expected_signature, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación inválida"
        )