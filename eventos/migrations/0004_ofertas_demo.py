from decimal import Decimal

from django.db import migrations


def cargar_ofertas_demo(apps, schema_editor):
    CategoriaOferta = apps.get_model('eventos', 'CategoriaOferta')
    Empresa = apps.get_model('eventos', 'Empresa')
    OfertaLaboral = apps.get_model('eventos', 'OfertaLaboral')

    empresa, _ = Empresa.objects.get_or_create(
        nombre='Avisos de demostracion',
        defaults={
            'descripcion': 'Empleador ficticio usado solo para demostrar el portal.',
            'ubicacion': 'La Serena',
            'activa': True,
        },
    )
    informatica, _ = CategoriaOferta.objects.get_or_create(
        nombre='Informatica',
        defaults={'descripcion': 'Desarrollo, soporte y tecnologia.'},
    )
    practicas, _ = CategoriaOferta.objects.get_or_create(
        nombre='Practicas universitarias',
        defaults={'descripcion': 'Pasantias y practicas profesionales.'},
    )

    ofertas = [
        {
            'titulo': 'Practica profesional en desarrollo web',
            'categoria': practicas,
            'descripcion': 'Aviso de demostracion para estudiantes de Informatica o carreras afines, con acompanamiento de un equipo de desarrollo.',
            'requisitos': 'Estudiante con practica profesional pendiente; conocimientos basicos de HTML, CSS, JavaScript y Git.',
            'ubicacion': 'La Serena',
            'modalidad': 'hibrida',
            'salario_minimo': Decimal('250000'),
            'salario_maximo': Decimal('350000'),
        },
        {
            'titulo': 'Practica profesional en soporte TI y redes',
            'categoria': practicas,
            'descripcion': 'Aviso de demostracion para apoyar tareas de soporte tecnico, inventario y configuracion de redes.',
            'requisitos': 'Estudiante de Informatica o conectividad; conocimientos basicos de Windows, Linux y redes.',
            'ubicacion': 'La Serena',
            'modalidad': 'presencial',
            'salario_minimo': Decimal('250000'),
            'salario_maximo': Decimal('300000'),
        },
        {
            'titulo': 'Desarrollador backend Python junior',
            'categoria': informatica,
            'descripcion': 'Aviso de demostracion para desarrollar y mantener servicios web con Python y Django.',
            'requisitos': 'Python, Django, SQL, Git y fundamentos de APIs REST; experiencia laboral inicial o proyectos academicos.',
            'ubicacion': 'La Serena o remoto en Chile',
            'modalidad': 'remota',
            'salario_minimo': Decimal('900000'),
            'salario_maximo': Decimal('1300000'),
        },
        {
            'titulo': 'Analista QA junior',
            'categoria': informatica,
            'descripcion': 'Aviso de demostracion para apoyar pruebas funcionales, documentacion de incidencias y validacion de aplicaciones.',
            'requisitos': 'Conocimientos de pruebas de software, SQL basico y herramientas de seguimiento de incidencias.',
            'ubicacion': 'La Serena',
            'modalidad': 'hibrida',
            'salario_minimo': Decimal('850000'),
            'salario_maximo': Decimal('1200000'),
        },
    ]

    for datos in ofertas:
        titulo = datos.pop('titulo')
        categoria = datos.pop('categoria')
        OfertaLaboral.objects.get_or_create(
            titulo=titulo,
            defaults={
                **datos,
                'categoria': categoria,
                'empresa': empresa,
                'estado': 'publicada',
            },
        )


class Migration(migrations.Migration):
    dependencies = [('eventos', '0003_categoriaoferta_empresa_ofertalaboral_postulacion_and_more')]
    operations = [migrations.RunPython(cargar_ofertas_demo, migrations.RunPython.noop)]
