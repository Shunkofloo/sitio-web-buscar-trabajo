from django.db import migrations


def cargar_usuarios(apps, schema_editor):
    UsuarioSitio = apps.get_model('usuarios', 'UsuarioSitio')
    usuarios = [
        ('admin', 'pbkdf2_sha256$1000000$o9RxzEZr0D0KuvjF6Iwql3$3yJexCNOMT2tf15D7yVggEl40Zt0BYRU1geUZly7h4I=', 'Administrador del Sitio', 'administrador'),
        ('invitado', 'pbkdf2_sha256$1000000$XCoyoqnLdnydyewRIv5zPa$o8FOkVf9plJMa1q3Gixre3mVZ3FxvHmKxaVTfIW23iU=', 'Usuario Invitado', 'invitado'),
    ]
    for usuario, password, nombre, rol in usuarios:
        UsuarioSitio.objects.update_or_create(
            usuario=usuario,
            defaults={
                'password': password,
                'nombre': nombre,
                'rol': rol,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0001_initial')]
    operations = [migrations.RunPython(cargar_usuarios, migrations.RunPython.noop)]
