from pydantic import BaseModel

class CambiarPassword(BaseModel):
    id: str
    nueva_psw: str