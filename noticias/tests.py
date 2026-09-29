from django.test import TestCase
from django.contrib import admin
from django.contrib.auth import get_user_model

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

	def test_visitante_no_ve_ni_puede_abrir_acciones_de_admin(self):
		response = self.client.get('/noticias/lista/')

		self.assertNotContains(response, 'Modificar')
		self.assertNotContains(response, 'Eliminar')
		self.assertNotContains(response, 'Agregar noticia')
		edit_response = self.client.get(
			f'/admin/noticias/noticia/{self.noticia.pk}/change/'
		)
		self.assertEqual(edit_response.status_code, 302)

	def test_superusuario_ve_enlaces_reales_de_edicion_de_noticias(self):
		administrador = get_user_model().objects.create_superuser(
			username='admin_noticias',
			email='admin-noticias@example.com',
			password='clave-admin-segura',
		)
		self.client.force_login(administrador)

		response = self.client.get('/noticias/lista/')

		self.assertContains(
			response,
			f'/admin/noticias/noticia/{self.noticia.pk}/change/',
		)
		self.assertContains(response, '/admin/noticias/noticia/add/')
		self.assertContains(response, f'/admin/noticias/noticia/{self.noticia.pk}/delete/')
