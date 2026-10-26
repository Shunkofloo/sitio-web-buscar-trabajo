from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import PerfilPostulante


class AutenticacionDjangoTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_user(
			username='estudiante',
			password='clave-segura',
			first_name='Estudiante de prueba',
		)

	def test_login_autentica_usuario_de_django(self):
		response = self.client.post('/usuarios/login/', {
			'usuario': 'estudiante',
			'password': 'clave-segura',
		})

		self.assertRedirects(response, '/usuarios/perfil/')
		self.assertIn('_auth_user_id', self.client.session)

	def test_perfil_requiere_autenticacion_django(self):
		response = self.client.get('/usuarios/perfil/')

		self.assertRedirects(response, '/usuarios/login/?next=/usuarios/perfil/')

	def test_perfil_muestra_usuario_y_grupo_de_django(self):
		self.client.force_login(self.usuario)
		self.usuario.groups.create(name='Supervisor')

		response = self.client.get('/usuarios/perfil/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['nombre_usuario'], 'Estudiante de prueba')
		self.assertEqual(response.context['usuario'], 'estudiante')
		self.assertEqual(response.context['rol_usuario'], 'Supervisor')


class PerfilPostulanteTests(TestCase):
	def test_perfil_es_independiente_del_usuario_de_autenticacion(self):
		perfil = PerfilPostulante.objects.create(
			nombre_completo='Candidata de prueba',
			correo='candidata@example.com',
			telefono='+56 9 1234 5678',
			profesion='Desarrolladora',
			resumen_profesional='Experiencia en desarrollo web.',
			habilidades='Python, Django',
			curriculum_url='https://example.com/cv',
		)

		self.assertEqual(str(perfil), 'Candidata de prueba')
		self.assertNotIn('usuario', {field.name for field in PerfilPostulante._meta.fields})
