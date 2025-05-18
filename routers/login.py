from fastapi import APIRouter, HTTPException, status, Depends
from models.usuario import Usuario
from core.database import db_client
from schemas.usuario import usuario_schema
from passlib.context import CryptContext

router = APIRouter(prefix="/login", tags=["login"])

# Configuración para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@router.get('/')
async def login(correo: str, psw: str):
    try:
        usuario = db_client.local.usuarios.find_one({'correo': correo})
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        loginUser = Usuario(**usuario_schema(usuario))

        if not verify_password(psw, loginUser.psw):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )
        usuario_dict = dict(loginUser) 
        del usuario_dict["psw"] #Evitar retornar la contraseña encriptada
        return usuario_dict

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el servidor: {str(e)}"
        )