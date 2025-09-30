from dotenv import load_dotenv
import os
from fastapi import HTTPException, status, Header

dotenv_path = os.path.join(os.path.dirname(__file__), "config.env")
load_dotenv(dotenv_path=dotenv_path)
SECRET_KEY = os.getenv("SECRET_KEY")

if SECRET_KEY is None:
    raise ValueError("SECRET_KEY no encontrada en las variables de entorno. Verifica tu archivo config.env")

SECRET_KEY = SECRET_KEY.strip()

def validar_token(tkn: str = Header(None, description="El token de autorización es obligatorio")):
    if tkn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sin Authorizacion"
        )
    if tkn != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorizacion inválida"
        )