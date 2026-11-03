# Recuperación de contraseña con código por correo (Amazon SES)

## Cómo funciona

1. En **¿Olvidaste tu contraseña?** la persona escribe su correo.
2. El sitio genera un código de **6 dígitos**, guarda solo su hash y lo envía por correo mediante Amazon SES.
3. El código **vence a los 15 minutos** (configurable con `CODIGO_DURACION_MINUTOS`, se recomienda entre 10 y 15) y solo sirve una vez.
4. La persona ingresa el código y su nueva contraseña en la pantalla siguiente. Si todo es correcto, la contraseña cambia.

Protecciones incluidas: máximo 5 intentos por código, un código nuevo cada 60 segundos y 5 por hora por cuenta, el código anterior queda invalidado al pedir otro, y la respuesta es idéntica exista o no la cuenta (no se puede averiguar qué correos están registrados).

En el código no hay nada específico de AWS: Django envía por SMTP y SES recibe ese SMTP. Por eso todo se configura en `.env`.

## Paso a paso en AWS

### 1. Elegir la región

SES funciona por región; todo lo siguiente debe hacerse en la misma. Si tu EC2 está en `us-east-1`, usa esa. Anota el nombre: lo necesitas para el endpoint `email-smtp.<región>.amazonaws.com`.

### 2. Verificar el remitente

En **SES → Identities → Create identity**:

- **Domain** (recomendado si tienes dominio): SES te da 3 registros CNAME de DKIM para pegar en tu DNS. Con eso los correos llegan mucho menos a spam.
- **Email address**: sirve para pruebas. AWS envía un correo con un enlace de confirmación.

La dirección que uses en `DEFAULT_FROM_EMAIL` tiene que pertenecer a una identidad verificada (por ejemplo `no-reply@tu-dominio.cl` si verificaste `tu-dominio.cl`).

### 3. Crear las credenciales SMTP

En **SES → SMTP settings → Create SMTP credentials**. Se abre IAM y crea un usuario con su usuario y contraseña SMTP. **Descarga las credenciales en ese momento**: la contraseña no se vuelve a mostrar.

> Estas credenciales **no son** la Access Key / Secret de IAM, y valen solo para la región donde las creaste. Si usas las de IAM, SES responde `535 Authentication Credentials Invalid`.

### 4. Salir del sandbox (imprescindible para correos reales)

Las cuentas nuevas de SES están en **sandbox**: solo pueden enviar a direcciones verificadas, hasta 200 correos por día y 1 por segundo. Para que cualquier persona reciba su código:

1. **SES → Account dashboard → Request production access**.
2. Tipo de correo: **Transactional**. Indica la URL de tu sitio y describe el uso (códigos de recuperación de contraseña enviados solo a quien los solicita; manejas rebotes y quejas).
3. AWS responde normalmente dentro de 96 horas. Verificar antes el dominio ayuda a que lo aprueben.

Mientras esperas puedes probar todo el flujo verificando en SES tu propio correo de destino (**Identities → Create identity → Email address**).

### 5. Configurar el servidor (EC2)

En el `.env` de la instancia:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<usuario SMTP de SES>
EMAIL_HOST_PASSWORD=<contraseña SMTP de SES>
DEFAULT_FROM_EMAIL=no-reply@tu-dominio.cl
EMAIL_TIMEOUT=10
CODIGO_DURACION_MINUTOS=15
```

- Cambia la región del `EMAIL_HOST` por la tuya.
- Se usa el puerto **587** (STARTTLS). El puerto 25 está limitado por defecto en EC2.
- El Security Group de la instancia debe permitir tráfico **saliente** al puerto 587 (por defecto lo permite).
- Reinicia el servicio para que lea el `.env` (por ejemplo `sudo systemctl restart gunicorn`).

### 6. Probar

1. Abre `/usuarios/recuperar/` y escribe el correo de una cuenta activa.
2. Revisa la bandeja (y spam): llega "Código para recuperar tu contraseña".
3. Ingresa el código y una contraseña nueva; luego inicia sesión con ella.

## Si no llega el correo

El sitio muestra un mensaje genérico, pero el motivo real queda en el log del servidor:

```bash
sudo journalctl -u gunicorn -n 100 --no-pager   # ajusta el nombre al de tu servicio systemd
```

| Mensaje en el log | Causa probable |
| --- | --- |
| `535 Authentication Credentials Invalid` | Usaste la Access Key de IAM, o las credenciales SMTP son de otra región. |
| `554 Message rejected: Email address is not verified` | El remitente (`DEFAULT_FROM_EMAIL`) no está verificado o sigues en sandbox y el destinatario tampoco. |
| `Connection timed out` | Algo bloquea el puerto 587 saliente, o el `EMAIL_HOST` tiene una región equivocada. |
| No hay error pero no llega | Revisa spam y la **Suppression list** de SES; si no verificaste el dominio con DKIM, es probable que lo marquen como spam. |

Si una cuenta no existe o está inactiva no se envía nada, a propósito, y el sitio responde igual que si existiera.

## Extras recomendados

- Configura un destino para **rebotes y quejas** (SES → Configuration sets → SNS), para no dañar tu reputación de envío.
- Revisa los límites de envío en **SES → Account dashboard** si esperas mucho tráfico.
- Alternativa sin contraseñas SMTP: con `django-ses` y un rol de IAM asignado a la EC2 no hay que guardar credenciales en `.env`. Requiere agregar la dependencia y cambiar `EMAIL_BACKEND`; el resto del flujo no cambia.
