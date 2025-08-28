from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.exceptions import HTTPException as FastAPI_HTTPException
from models.usuario import Usuario
from core.database import db_client
from schemas.usuario import usuario_schema
from passlib.context import CryptContext
from validar_token import validar_token 

router = APIRouter(prefix="/login", tags=["login"])

# Configuración para hashing de contraseñas
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except AttributeError:
    # Suprimir el error relacionado con bcrypt
    pwd_context = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@router.post('', include_in_schema=False)
async def login(credentials: dict, token: str = Depends(validar_token)):
    identificador = credentials.get("correo", "").strip().lower()
    psw = credentials.get("psw", "")

    if not identificador or not psw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario (correo o teléfono) y contraseña son obligatorios"
        )
    try:
        query = {}
        if identificador.isdigit():
            # Es un teléfono
            query = {"telefono": int(identificador)}
        else:
            # Es un correo
            query = {"correo": identificador}
        usuario = db_client.local.usuarios.find_one(query)
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
        del usuario_dict["psw"]
        return usuario_dict
    except FastAPI_HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el login: {str(e)}"
        )


# @router.post('', include_in_schema=False)
# async def login(credentials: dict, token: str = Depends(validar_token)):
#     correo = credentials.get("correo", "").lower()  # Convertir correo a minúsculas
#     psw = credentials.get("psw", "")

#     if not correo or not psw:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Correo y contraseña son obligatorios"
#         )

#     try:
#         usuario = db_client.local.usuarios.find_one({'correo': correo})
#         if not usuario:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Credenciales incorrectas",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )

#         loginUser = Usuario(**usuario_schema(usuario))

#         if not verify_password(psw, loginUser.psw):
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Credenciales incorrectas",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#         usuario_dict = dict(loginUser) 
#         del usuario_dict["psw"] #Evitar retornar la contraseña encriptada
#         return usuario_dict
#     except FastAPI_HTTPException as http_exc:
#         raise http_exc  # Re-lanzar excepciones HTTP tal como están
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al procesar el login: {str(e)}"
#         )