from django.test import TestCase
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from .models import PerfilPostulante, UsuarioSitio


class LoginUsuarioSitioTests(TestCase):
	def setUp(self):
		self.usuario = UsuarioSitio.objects.create(
			usuario='estudiante',
			password=make_password('clave-segura'),
			nombre='Estudiante de prueba',
			rol='invitado',
		)

	def test_login_consulta_usuario_en_base_de_datos(self):
		response = self.client.post('/usuarios/login/', {
			'usuario': 'ESTUDIANTE',
			'password': 'clave-segura',
		})

		self.assertRedirects(response, '/usuarios/perfil/')
		self.assertEqual(
			self.client.session['usuario_autenticado'],
			self.usuario.usuario,
		)

	def test_usuario_esta_registrado_en_admin(self):
		self.assertIn(UsuarioSitio, admin.site._registry)

	def test_perfil_postulante_esta_registrado_en_admin(self):
		self.assertIn(PerfilPostulante, admin.site._registry)

	def test_superusuario_ingresa_desde_el_login_del_sitio_al_admin(self):
		administrador = get_user_model().objects.create_superuser(
			username='superadmin',
			email='superadmin@example.com',
			password='clave-admin-segura',
		)

		response = self.client.post('/usuarios/login/', {
			'usuario': administrador.username,
			'password': 'clave-admin-segura',
		})

		self.assertRedirects(response, '/admin/')
		self.assertEqual(self.client.get('/admin/').status_code, 200)

	def test_rol_administrador_del_sitio_no_es_superusuario_django(self):
		usuario_admin_sitio = UsuarioSitio.objects.create(
			usuario='admin_portal',
			password=make_password('clave-portal'),
			nombre='Administrador del portal',
			rol='administrador',
		)

		response = self.client.post('/usuarios/login/', {
			'usuario': usuario_admin_sitio.usuario,
			'password': 'clave-portal',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'cuenta creada con createsuperuser')
		self.assertNotIn('usuario_autenticado', self.client.session)
