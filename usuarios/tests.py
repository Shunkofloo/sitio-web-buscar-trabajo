from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command, CommandError
from io import StringIO
from unittest.mock import patch

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


class CrearRolesCommandTests(TestCase):
	def setUp(self):
		self.password = 'demo-password-segura'

	def ejecutar_comando(self):
		salida = StringIO()
		with patch.dict('os.environ', {'DEMO_PASSWORD': self.password}):
			call_command('crear_roles', stdout=salida)
		return salida.getvalue()

	def permisos(self, grupo):
		return set(
			grupo.permissions.values_list(
				'content_type__app_label',
				'content_type__model',
				'codename',
			)
		)

	def test_crea_grupos_usuarios_y_permisos_solicitados(self):
		salida = self.ejecutar_comando()

		administrador = Group.objects.get(name='Administrador')
		supervisor = Group.objects.get(name='Supervisor')
		administrativo = Group.objects.get(name='Administrativo')
		permisos_admin = self.permisos(administrador)
		permisos_supervisor = self.permisos(supervisor)
		permisos_administrativo = self.permisos(administrativo)

		for app_label in ('eventos', 'noticias'):
			with self.subTest(app_label=app_label):
				permisos_modelos = Permission.objects.filter(
					content_type__app_label=app_label,
				).values_list('content_type__model', 'codename')
				self.assertTrue(set(permisos_modelos).issubset(
					{
						(model, codename)
						for app_label_db, model, codename in permisos_admin
						if app_label_db == app_label
					}
				))

		self.assertTrue({
			('auth', 'user', 'view_user'),
			('auth', 'user', 'add_user'),
			('auth', 'user', 'change_user'),
			('auth', 'user', 'delete_user'),
			('auth', 'group', 'view_group'),
		}.issubset(permisos_admin))

		self.assertEqual(permisos_supervisor, {
			('eventos', 'empresa', 'view_empresa'),
			('eventos', 'empresa', 'add_empresa'),
			('eventos', 'empresa', 'change_empresa'),
			('eventos', 'ofertalaboral', 'view_ofertalaboral'),
			('eventos', 'ofertalaboral', 'add_ofertalaboral'),
			('eventos', 'ofertalaboral', 'change_ofertalaboral'),
			('eventos', 'postulacion', 'view_postulacion'),
			('eventos', 'postulacion', 'add_postulacion'),
			('eventos', 'postulacion', 'change_postulacion'),
			('eventos', 'categoriaoferta', 'view_categoriaoferta'),
		})
		self.assertEqual(permisos_administrativo, {
			('eventos', 'empresa', 'view_empresa'),
			('eventos', 'ofertalaboral', 'view_ofertalaboral'),
			('eventos', 'postulacion', 'view_postulacion'),
			('eventos', 'postulacion', 'add_postulacion'),
		})

		User = get_user_model()
		for username, grupo, email in (
			('admin_demo', administrador, 'admin_demo@example.com'),
			('supervisor_demo', supervisor, 'supervisor_demo@example.com'),
			('administrativo_demo', administrativo, 'administrativo_demo@example.com'),
		):
			with self.subTest(username=username):
				usuario = User.objects.get(username=username)
				self.assertEqual(usuario.email, email)
				self.assertTrue(usuario.check_password(self.password))
				self.assertEqual(list(usuario.groups.all()), [grupo])

		self.assertIn('3 grupos nuevos', salida)
		self.assertIn('3 usuarios demo nuevos', salida)

	def test_es_idempotente_y_sincroniza_permisos(self):
		self.ejecutar_comando()
		Group.objects.get(name='Supervisor').permissions.clear()
		User = get_user_model()
		User.objects.get(username='supervisor_demo').groups.clear()

		salida = self.ejecutar_comando()

		self.assertEqual(Group.objects.count(), 3)
		self.assertEqual(User.objects.filter(username__endswith='_demo').count(), 3)
		self.assertEqual(
			self.permisos(Group.objects.get(name='Supervisor')),
			{
				('eventos', 'empresa', 'view_empresa'),
				('eventos', 'empresa', 'add_empresa'),
				('eventos', 'empresa', 'change_empresa'),
				('eventos', 'ofertalaboral', 'view_ofertalaboral'),
				('eventos', 'ofertalaboral', 'add_ofertalaboral'),
				('eventos', 'ofertalaboral', 'change_ofertalaboral'),
				('eventos', 'postulacion', 'view_postulacion'),
				('eventos', 'postulacion', 'add_postulacion'),
				('eventos', 'postulacion', 'change_postulacion'),
				('eventos', 'categoriaoferta', 'view_categoriaoferta'),
			},
		)
		self.assertEqual(
			list(User.objects.get(username='supervisor_demo').groups.values_list('name', flat=True)),
			['Supervisor'],
		)
		self.assertIn('0 grupos nuevos', salida)
		self.assertIn('0 usuarios demo nuevos', salida)

	def test_falla_con_error_claro_si_falta_demo_password(self):
		with patch.dict('os.environ', {}, clear=True):
			with self.assertRaisesMessage(CommandError, 'DEMO_PASSWORD'):
				call_command('crear_roles', stdout=StringIO())

		self.assertFalse(Group.objects.exists())
		self.assertFalse(
			get_user_model().objects.filter(username__endswith='_demo').exists()
		)
