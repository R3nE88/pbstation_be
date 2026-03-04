"""
Inicialización de la base de datos con usuario admin y cliente por defecto
"""
from core.database import db

def crear_configuracion_defecto():
    """
    Crea la configuración por defecto si no existe en la base de datos.
    Solo se ejecuta si la colección de configuracion está vacía.
    """
    try:
        config = db.configuracion.find_one()
        if config is None:
            config_defecto = {
                "precio_dolar": 18.4,
                "iva": 8,
                "last_version": "0.8.8"
            }
            db.configuracion.insert_one(config_defecto)
            print("✓ Configuración por defecto creada con éxito.")
            return True
        else:
            print("✓ Configuración ya existe en la base de datos.")
            return False
    except Exception as e:
        print(f"✗ Error al crear configuración por defecto: {e}")
        return False

def crear_usuario_admin_defecto():
    """
    Crea un usuario admin por defecto si no hay usuarios en la base de datos.
    Solo se ejecuta si la colección de usuarios está vacía.
    """
    try:
        # Verificar si hay usuarios en la base de datos
        usuarios_count = db.usuarios.count_documents({})
        
        if usuarios_count == 0:
            # Usuario admin por defecto
            usuario_admin = {
                "nombre": "admin",
                "correo": "admin",
                "telefono": 1000000000,
                "psw": "$2b$12$chIGKdLyCa3bMrFooDyKeeea46pj9FARL9P91u89AOW7AHNiTwPPe",
                "rol": "administrativo",
                "permisos": "admin",
                "activo": True
            }
            
            # Insertar el usuario admin
            resultado = db.usuarios.insert_one(usuario_admin)
            print(f"✓ Usuario admin creado con éxito. ID: {resultado.inserted_id}")
            return True
        else:
            print(f"✓ Base de datos ya contiene {usuarios_count} usuario(s). No se crea admin por defecto.")
            return False
            
    except Exception as e:
        print(f"✗ Error al crear usuario admin por defecto: {e}")
        return False


def crear_cliente_defecto():
    """
    Crea un cliente 'Público General' por defecto si no hay clientes en la base de datos.
    Solo se ejecuta si la colección de clientes está vacía.
    """
    try:
        # Verificar si hay clientes en la base de datos
        clientes_count = db.clientes.count_documents({})
        
        if clientes_count == 0:
            # Cliente público general por defecto
            cliente_publico = {
                "nombre": "Publico General",
                "correo": None,
                "telefono": None,
                "razon_social": None,
                "rfc": "XAXX010101000",
                "regimen_fiscal": "616",
                "codigo_postal": None,
                "direccion": None,
                "no_ext": None,
                "no_int": None,
                "colonia": None,
                "localidad": None,
                "adeudos": [],
                "protegido": True,
                "activo": True
            }
            
            # Insertar el cliente
            resultado = db.clientes.insert_one(cliente_publico)
            print(f"✓ Cliente 'Público General' creado con éxito. ID: {resultado.inserted_id}")
            return True
        else:
            print(f"✓ Base de datos ya contiene {clientes_count} cliente(s). No se crea cliente por defecto.")
            return False
            
    except Exception as e:
        print(f"✗ Error al crear cliente por defecto: {e}")
        return False

