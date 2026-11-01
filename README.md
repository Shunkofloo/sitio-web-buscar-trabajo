# Buscar trabajo

Portal de ofertas laborales desarrollado con Django 5.2. Permite publicar y consultar ofertas, administrar empresas y usuarios, gestionar postulaciones y noticias, y controlar el acceso mediante autenticación y permisos de Django. La interfaz y los mantenedores usan plantillas Django y formularios Bootstrap.

## Perfiles y permisos

Los perfiles se asignan como grupos de Django. Los permisos del grupo controlan tanto los enlaces visibles como el acceso a cada operación.

| Perfil | Empresas | Ofertas laborales | Postulaciones | Usuarios y noticias |
| --- | --- | --- | --- | --- |
| **Administrador** | Ver, crear, editar y eliminar | Ver, crear, editar y eliminar | Ver, registrar y cambiar estado | Gestionar usuarios y grupos; todos los permisos de noticias |
| **Supervisor** | Ver, crear y editar | Ver, crear y editar | Ver, registrar y cambiar estado | Sin permisos de gestión de usuarios ni de noticias |
| **Administrativo** | Solo ver | Solo ver | Ver y registrar; no cambiar estado | Sin permisos de gestión de usuarios ni de noticias |

El acceso de edición o eliminación se controla en el servidor mediante permisos, no solo ocultando botones.

## Funcionalidades

- Listados públicos y de solo lectura de eventos y noticias, con búsqueda.
- Listado público de ofertas publicadas, con búsqueda por cargo, empresa, categoría y ubicación.
- Mantenedores de empresas y ofertas: búsqueda, filtros, paginación, validaciones y operaciones CRUD según permisos.
- Registro transaccional de postulaciones: crea o actualiza la ficha del candidato por correo y registra la postulación en una sola operación. Solo permite ofertas publicadas y vigentes, evita postulaciones duplicadas y valida la carta de presentación.
- Listado de postulaciones con filtros por estado y oferta, página de detalle y cambio de estado autorizado.
- Inicio y cierre de sesión con el sistema de autenticación de Django y redirección al dashboard del grupo.
- Gestión de usuarios: búsqueda, paginación, altas, edición, asignación de grupo y activación/desactivación.
- Recuperación de contraseña por correo, con enlaces seguros de duración limitada.
- Mensajes y formularios Bootstrap en español.

## Requisitos

- Python 3.11 o posterior.
- Dependencias de `requirements.txt`.
- SQLite para desarrollo local. MySQL también está soportado para despliegues.

## Ejecutar en local (Windows)

Desde la raíz del proyecto, en PowerShell:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env`: cambia `SECRET_KEY` por una clave local propia y establece una contraseña de demostración no compartida para `DEMO_PASSWORD`. Para uso local, deja `DEBUG=True`, `DB_ENGINE=django.db.backends.sqlite3` y el nombre de base de datos vacío.

Prepara la base de datos y ejecuta la aplicación:

```powershell
python manage.py migrate
python manage.py crear_roles
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. El comando `crear_roles` es idempotente para grupos y usuarios demo; sincroniza los permisos y grupos, y establece la contraseña de los usuarios demo a partir de `DEMO_PASSWORD` cada vez que se ejecuta. No uses cuentas demo en producción.

Para que la recuperación de contraseña funcione fuera de pruebas, configura el correo SMTP en `.env`. El backend predeterminado es la consola, que imprime los mensajes en la terminal y no los envía por Internet.

## Variables de entorno

`.env.example` documenta los nombres de las variables. Sus valores son ejemplos, no credenciales. No subas `.env` al repositorio.

| Variable | Propósito |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Django; obligatoria cuando `DEBUG=False`. |
| `DEBUG` | Activa o desactiva el modo de depuración. Desactivarlo en producción. |
| `ALLOWED_HOSTS` | Lista de IPs o dominios permitidos, separada por comas. |
| `DB_ENGINE` | Motor de base de datos; SQLite por defecto o el backend MySQL. |
| `DB_NAME` | Archivo SQLite o nombre de la base MySQL. |
| `DB_USER`, `DB_PASSWORD` | Credenciales de la base MySQL. |
| `DB_HOST`, `DB_PORT` | Host y puerto de MySQL. |
| `DEMO_PASSWORD` | Contraseña exigida por `python manage.py crear_roles`; nunca incluir una contraseña real en el repositorio. |
| `EMAIL_BACKEND` | Backend de correo; por defecto usa la consola de Django. |
| `EMAIL_HOST`, `EMAIL_PORT` | Servidor SMTP y puerto. |
| `EMAIL_USE_TLS` | Indica si SMTP usa TLS. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Credenciales SMTP. |
| `DEFAULT_FROM_EMAIL` | Dirección remitente de los correos de la aplicación. |

## Pruebas y verificaciones

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

El conjunto de pruebas cubre autenticación, permisos, mantenedores, postulaciones y recuperación de contraseña. Las pruebas de correo usan el backend local de memoria de Django.

## Despliegue en una instancia EC2

1. Crea una instancia Linux compatible, restringe los puertos del Security Group y prepara acceso SSH. Para tráfico público, usa HTTPS en el dominio del proyecto.
2. Instala Python, `venv`, Git y los paquetes del sistema requeridos por el motor de base de datos. Clona el repositorio y entra en la raíz del proyecto.
3. Crea un entorno virtual e instala las dependencias:

   ```bash
   python3 -m venv venv
   . venv/bin/activate
   pip install -r requirements.txt
   ```

4. Configura un archivo `.env` fuera del control de versiones. Define una `SECRET_KEY` larga y privada, `DEBUG=False`, el dominio/IP en `ALLOWED_HOSTS`, y los valores `DB_*` adecuados. Para MySQL, crea previamente una base y un usuario con privilegios limitados para esa base. No reutilices las credenciales de ejemplo.
5. Configura el correo SMTP mediante las variables `EMAIL_*` si la aplicación debe enviar recuperación de contraseña. Mantén privados los datos de acceso SMTP.
6. Aplica migraciones, crea/sincroniza grupos y usuarios demo con una contraseña segura mediante `DEMO_PASSWORD`, y recopila los estáticos:

   ```bash
   python manage.py check --deploy
   python manage.py migrate
   python manage.py crear_roles
   python manage.py collectstatic
   ```

   Los usuarios demo son solo para demostración; en una instalación real, crea las cuentas necesarias con credenciales individuales y elimina o desactiva las cuentas de demostración si no se requieren.
7. Ejecuta Django con un servidor WSGI de producción, como Gunicorn (incluido en dependencias para sistemas Unix), administrado por `systemd`. Coloca Nginx u otro proxy inverso delante para servir HTTPS y los archivos estáticos desde `STATIC_ROOT`.
8. Para un despliegue exclusivamente HTTPS, configura la redirección a TLS y las opciones de seguridad de cookies y HSTS de acuerdo con la topología del proxy. Revisa cada advertencia de `check --deploy`; no actives HSTS hasta confirmar que todo el sitio y subdominios previstos usan HTTPS.
9. Verifica el sitio, la conexión a la base y el envío de correo. Mantén `.env`, copias de seguridad y claves fuera del repositorio y limita su acceso en el servidor.

La creación de recursos AWS, el registro de dominio, los certificados TLS, el proxy inverso y el servicio `systemd` dependen de la infraestructura elegida y deben configurarse con sus propios valores.
