# Deploy pbstation_be en Dokploy

## Variables de Entorno

Configurar en Dokploy → Environment:

```env
MONGODB_URL=mongodb://mongo:27017
SECRET_KEY=P7InT3r8o&
FACTURAMA_USER=printerboy
FACTURAMA_PASS=DIOE860426
```

> **Nota:** `mongo` es el nombre del contenedor/servicio de MongoDB en la red Docker de Dokploy.

## Volúmenes (Persistencia)

Configurar en Dokploy → Volumes/Mounts:

| Tipo | Volume/Host Path | Container Path |
|------|-----------------|----------------|
| Volume | `pbstation-uploads` | `/app/uploads` |
| Bind | archivo local o Volume | `/app/configuracion.json` |

### Opción recomendada para `configuracion.json`

Usar un **bind mount** a un archivo en el host:

```
Host: /etc/dokploy/pbstation/configuracion.json
Container: /app/configuracion.json
```

O usar un named volume montado en un solo archivo (depende de la versión de Dokploy).

## Red Docker

El servicio debe estar en la **misma red Docker** que el contenedor de MongoDB.
En Dokploy esto se configura automáticamente si ambos servicios están en el mismo proyecto.

## Puerto

El backend expone el puerto **8000**. Configurar el proxy/dominio en Dokploy para apuntar a este puerto.

## Primer Deploy

1. Crear el servicio en Dokploy (tipo: Docker, apuntando al repo de `pbstation_be`)
2. Configurar las variables de entorno
3. Configurar los volúmenes
4. Verificar que esté en la misma red que MongoDB
5. Deploy
6. Verificar con: `https://tu-dominio/helloworld`
