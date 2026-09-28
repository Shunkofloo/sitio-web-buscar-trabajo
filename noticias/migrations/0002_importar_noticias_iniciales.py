from datetime import date

from django.db import migrations


def cargar_noticias(apps, schema_editor):
    CategoriaNoticia = apps.get_model('noticias', 'CategoriaNoticia')
    Noticia = apps.get_model('noticias', 'Noticia')
    categoria, _ = CategoriaNoticia.objects.get_or_create(nombre='General')
    noticias = [
        (1, 'Nuevas empresas priorizan talento digital y habilidades prácticas', 'La demanda por perfiles técnicos y resolución de problemas crece en sectores clave del mercado laboral.', date(2026, 8, 20), 'img/noticias/parte1.jpg'),
        (2, 'Avances en inteligencia artificial mejoran para ambientes laborales', 'Las herramientas de IA están optimizando la productividad, la coordinación y el análisis del trabajo actual.', date(2026, 8, 25), 'img/noticias/parte2.jpg'),
        (3, 'Más empresas ofrecen trabajo híbrido y mayor flexibilidad', 'Los profesionales buscan opciones con mejor equilibrio entre desempeño, bienestar y autonomía laboral.', date(2026, 8, 28), 'img/noticias/parte3.jpg'),
        (4, 'La capacitación continua se convierte en ventaja competitiva', 'Cursos, certificaciones y actualización técnica ayudan a reforzar la empleabilidad en un mercado dinámico.', date(2026, 9, 1), 'img/noticias/parte4.jpg'),
    ]
    for noticia_id, titulo, resumen, fecha, imagen in noticias:
        Noticia.objects.update_or_create(
            id=noticia_id,
            defaults={
                'categoria_id': categoria.pk,
                'titulo': titulo,
                'resumen': resumen,
                'fecha': fecha,
                'imagen': imagen,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('noticias', '0001_initial')]
    operations = [migrations.RunPython(cargar_noticias, migrations.RunPython.noop)]
