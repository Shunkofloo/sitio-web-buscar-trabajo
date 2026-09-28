from datetime import date

from django.db import migrations


def cargar_eventos(apps, schema_editor):
    Evento = apps.get_model('eventos', 'Evento')
    eventos = [
        (1, 'Feria de Innovación Tecnológica', 'Centro de Convenciones', date(2026, 9, 10), 'img/eventos/foto1.jpg'),
        (2, 'Encuentro de Desarrolladores Django', 'Auditorio Central', date(2026, 9, 15), 'img/eventos/foto1.jpg'),
    ]
    for evento_id, nombre, lugar, fecha, imagen in eventos:
        Evento.objects.update_or_create(
            id=evento_id,
            defaults={
                'nombre': nombre,
                'lugar': lugar,
                'fecha': fecha,
                'imagen': imagen,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('eventos', '0001_initial')]
    operations = [migrations.RunPython(cargar_eventos, migrations.RunPython.noop)]
