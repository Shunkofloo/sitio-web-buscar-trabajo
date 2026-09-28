from django.test import TestCase
from django.contrib import admin

from .models import CategoriaNoticia, Noticia


class NoticiaListadoTests(TestCase):
	def setUp(self):
		categoria = CategoriaNoticia.objects.create(nombre='Empleo')
		self.noticia = Noticia.objects.create(
			categoria=categoria,
			titulo='NoticiaBusquedaUnicaXYZ',
			resumen='Nuevas oportunidades en la región.',
			fecha='2026-09-20',
		)

	def test_lista_muestra_noticias_y_categoria(self):
		response = self.client.get('/noticias/lista/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.noticia.titulo)
		self.assertContains(response, self.noticia.categoria.nombre)

	def test_busqueda_filtra_por_titulo(self):
		response = self.client.get('/noticias/lista/', {'q': 'BusquedaUnicaXYZ'})

		self.assertContains(response, self.noticia.titulo)
		self.assertEqual(len(response.context['noticias']), 1)

	def test_entidades_estan_registradas_en_admin(self):
		self.assertIn(CategoriaNoticia, admin.site._registry)
		self.assertIn(Noticia, admin.site._registry)
