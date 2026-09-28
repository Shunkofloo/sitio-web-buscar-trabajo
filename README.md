# Buscar trabajo

Aplicación Django modular para publicar vacantes, eventos y noticias laborales. Las entidades se almacenan mediante Django ORM y se administran desde Django Admin.

## Funcionalidades implementadas

- Listado de eventos y noticias consultados desde la base de datos.
- Listado público de ofertas en `/ofertas/`; muestra solo ofertas con estado `Publicada` y permite buscar por cargo, empresa, categoría o ubicación.
- Gestión de empresas, categorías de ofertas, ofertas, perfiles postulantes y postulaciones desde Django Admin.
- Búsqueda por nombre/lugar de evento y por título/resumen de noticia.
- Relación entre noticia y categoría.
- Administración CRUD de todas las entidades desde `/admin/`.
- Importación inicial de los registros que estaban en JSON mediante migraciones.
- Login del sitio validado contra usuarios almacenados y contraseñas con hash.
- Controles de interfaz Agregar, Modificar, Eliminar y Buscar en los listados. Los controles de modificación y eliminación son marcadores visuales, tal como permite esta evaluación.
- Configuración de secretos y base de datos mediante variables de entorno.

## Ejecutar localmente en Windows

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`. El panel está en `http://127.0.0.1:8000/admin/`.

Las cuentas con permisos `staff` de Django también pueden iniciar sesión desde `/usuarios/login/`; al autenticarse correctamente, el sitio las redirige al panel. Las cuentas normales del portal continúan ingresando a su perfil.

Para mostrar una vacante en la página pública, crea primero la empresa y la categoría desde Admin, crea la oferta asociada y cambia su estado a `Publicada`. Las ofertas en borrador, pendientes o rechazadas no son visibles para los visitantes.

Las migraciones importan los registros de eventos, noticias y usuarios del prototipo. Las credenciales del archivo `usuarios/data/usuarios.json` se conservan como hashes existentes. Para crear o modificar usuarios de este sitio, usar Django Admin.

## Base de datos

SQLite se usa por defecto para desarrollo local. La configuración también permite MySQL mediante `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` en `.env`. En una instancia EC2, crea la base y el usuario MySQL antes de ejecutar `python manage.py migrate`.

No subas `.env`, contraseñas ni claves privadas al repositorio. `.env.example` solo contiene nombres de variables y valores de ejemplo.

## Pruebas

```powershell
python manage.py check
python manage.py test eventos noticias usuarios
```

## Preparación para EC2 y GitHub

1. Crear una instancia Linux, instalar Python, Git y el servidor/base de datos elegidos.
2. Clonar el repositorio con `git clone URL_DEL_REPOSITORIO`.
3. Crear y activar un entorno virtual; instalar `requirements.txt`.
4. Configurar `.env` con `DEBUG=False`, la IP/dominio en `ALLOWED_HOSTS` y credenciales MySQL.
5. Ejecutar `python manage.py migrate` y `python manage.py createsuperuser`.
6. Ejecutar la aplicación detrás de un servidor web de producción y abrir únicamente los puertos requeridos en el Security Group.

El despliegue en AWS, la publicación del repositorio remoto, las capturas de evidencia y el documento técnico final deben completarse con las credenciales y recursos propios del estudiante.
