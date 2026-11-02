import re
import smtplib
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.management import call_command, CommandError
from django.urls import reverse
from django.test import override_settings
from django.utils import timezone
from io import StringIO
from unittest.mock import patch

from .models import CodigoVerificacion, PerfilPostulante
from .mixins import LoginYPermisoRequeridoMixin, grupo_principal


class AutenticacionDjangoTests(TestCase):
	def setUp(self):
		self.grupo = Group.objects.create(name='Supervisor')
		self.usuario = get_user_model().objects.create_user(
			username='estudiante',
			password='clave-segura',
			first_name='Estudiante de prueba',
		)
		self.usuario.groups.add(self.grupo)

	def test_login_autentica_usuario_de_django(self):
		response = self.client.post('/usuarios/login/', {
			'username': 'estudiante',
			'password': 'clave-segura',
		}, follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.redirect_chain, [
			('/usuarios/dashboard/', 302),
			('/usuarios/dashboard/supervisor/', 302),
		])
		self.assertContains(response, 'Dashboard Supervisor')
		self.assertIn('_auth_user_id', self.client.session)

	def test_login_redirige_al_dashboard_segun_grupo(self):
		for nombre_grupo, url_dashboard in (
			('Administrador', '/usuarios/dashboard/administrador/'),
			('Supervisor', '/usuarios/dashboard/supervisor/'),
			('Administrativo', '/usuarios/dashboard/administrativo/'),
		):
			with self.subTest(grupo=nombre_grupo):
				self.usuario.groups.set([Group.objects.get_or_create(name=nombre_grupo)[0]])
				self.client.logout()

				response = self.client.post('/usuarios/login/', {
					'username': 'estudiante',
					'password': 'clave-segura',
				}, follow=True)

				self.assertEqual(response.status_code, 200)
				self.assertEqual(response.request['PATH_INFO'], url_dashboard)
				self.assertContains(response, f'Dashboard {nombre_grupo}')

	def test_login_muestra_error_de_autenticacion(self):
		response = self.client.post('/usuarios/login/', {
			'username': 'estudiante',
			'password': 'incorrecta',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Usuario o contraseña incorrectos.')

	def test_login_de_usuario_sin_grupo_muestra_mensaje_claro(self):
		self.usuario.groups.clear()
		response = self.client.post('/usuarios/login/', {
			'username': 'estudiante',
			'password': 'clave-segura',
		}, follow=True)

		self.assertContains(
			response,
			'Tu cuenta no tiene asignado un grupo con un dashboard disponible.',
		)

	def test_dashboard_requiere_autenticacion_django(self):
		response = self.client.get('/usuarios/dashboard/supervisor/')

		self.assertRedirects(
			response,
			'/usuarios/login/?next=/usuarios/dashboard/supervisor/',
		)

	def test_dashboard_rechaza_usuario_de_otro_grupo_con_403_amigable(self):
		self.client.force_login(self.usuario)
		with override_settings(DEBUG=False):
			response = self.client.get('/usuarios/dashboard/administrador/')

		self.assertEqual(response.status_code, 403)
		self.assertContains(response, 'Tu cuenta no tiene permisos para acceder a esta página.', status_code=403)

	def test_cierre_de_sesion_requiere_post(self):
		self.client.force_login(self.usuario)

		response_get = self.client.get('/usuarios/logout/')
		self.assertEqual(response_get.status_code, 405)
		self.assertIn('_auth_user_id', self.client.session)

		response_post = self.client.post('/usuarios/logout/')
		self.assertRedirects(response_post, '/usuarios/login/')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_navbar_muestra_nombre_grupo_dashboard_y_logout_post(self):
		self.client.force_login(self.usuario)

		response = self.client.get('/')

		self.assertContains(response, 'Estudiante de prueba')
		self.assertContains(response, 'Supervisor')
		self.assertContains(response, '/usuarios/dashboard/supervisor/')
		self.assertContains(response, 'method="post" action="/usuarios/logout/"')

	def test_navbar_muestra_gestion_usuarios_segun_permiso_view(self):
		self.usuario.user_permissions.add(
			Permission.objects.get(content_type__app_label='eventos', codename='view_empresa'),
			Permission.objects.get(content_type__app_label='eventos', codename='view_ofertalaboral'),
			Permission.objects.get(content_type__app_label='auth', codename='view_user'),
		)
		self.client.force_login(self.usuario)

		response = self.client.get('/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Gestión de usuarios')
		self.assertNotContains(response, 'Crear usuario')

	def test_mixin_requiere_login_y_permiso_con_excepcion(self):
		self.assertTrue(issubclass(LoginYPermisoRequeridoMixin, LoginRequiredMixin))
		self.assertTrue(issubclass(LoginYPermisoRequeridoMixin, PermissionRequiredMixin))
		self.assertTrue(LoginYPermisoRequeridoMixin.raise_exception)

	def test_grupo_principal_devuelve_rol_prioritario_o_none(self):
		self.usuario.groups.add(Group.objects.create(name='Administrativo'))
		self.assertEqual(grupo_principal(self.usuario), 'Supervisor')

		self.usuario.groups.clear()
		self.assertIsNone(grupo_principal(self.usuario))


@override_settings(
	EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
	CODIGO_DURACION_MINUTOS=15,
)
class RecuperacionContrasenaTests(TestCase):
	NUEVA_CONTRASENA = 'Nueva-clave-segura-237!'

	def setUp(self):
		self.usuario = get_user_model().objects.create_user(
			username='recuperacion',
			email='recuperacion@example.com',
			password='Clave-inicial-segura-934!',
		)

	def solicitar_codigo(self, email=None):
		return self.client.post(
			reverse('usuarios_password_reset'),
			{'email': email or self.usuario.email},
		)

	@staticmethod
	def codigo_enviado(indice=0):
		return next(
			line.strip()
			for line in mail.outbox[indice].body.splitlines()
			if re.fullmatch(r'\d{6}', line.strip())
		)

	def confirmar(self, codigo, contrasena=None, email=None):
		contrasena = contrasena or self.NUEVA_CONTRASENA
		return self.client.post(
			reverse('usuarios_password_reset_codigo'),
			{
				'email': email or self.usuario.email,
				'codigo': codigo,
				'password1': contrasena,
				'password2': contrasena,
			},
		)

	def test_solicitud_existente_envia_codigo_de_seis_digitos(self):
		response = self.solicitar_codigo()

		self.assertRedirects(
			response,
			f'{reverse("usuarios_password_reset_codigo")}?email=recuperacion%40example.com',
		)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].to, [self.usuario.email])
		self.assertIn('código', mail.outbox[0].subject.lower())
		self.assertRegex(self.codigo_enviado(), r'^\d{6}$')
		self.assertIn('15 minutos', mail.outbox[0].body)
		self.assertNotIn('/usuarios/restablecer/', mail.outbox[0].body)

	def test_codigo_vence_a_los_minutos_configurados(self):
		antes = timezone.now()
		self.solicitar_codigo()

		codigo = self.usuario.codigos_verificacion.get()
		self.assertEqual(codigo.proposito, CodigoVerificacion.Proposito.RECUPERACION)
		vigencia = codigo.expira_en - antes
		self.assertGreaterEqual(vigencia, timedelta(minutes=14, seconds=55))
		self.assertLessEqual(vigencia, timedelta(minutes=15, seconds=5))

	@override_settings(CODIGO_DURACION_MINUTOS=10)
	def test_duracion_del_codigo_es_configurable(self):
		self.solicitar_codigo()

		self.assertIn('10 minutos', mail.outbox[0].body)
		self.assertContains(
			self.client.get(reverse('usuarios_password_reset_codigo')),
			'vence en 10 minutos',
		)

	def test_pantalla_del_codigo_muestra_seis_casillas(self):
		self.solicitar_codigo()

		response = self.client.get(reverse('usuarios_password_reset_codigo'))

		html = response.content.decode()
		self.assertEqual(len(re.findall(r'<input[^>]*data-code-digit', html)), 6)
		self.assertContains(response, 'código de 6 dígitos')

	def test_codigo_cambia_contrasena_y_permite_login(self):
		self.solicitar_codigo()

		response = self.confirmar(self.codigo_enviado())

		self.assertRedirects(response, reverse('usuarios_password_reset_complete'))
		self.usuario.refresh_from_db()
		self.assertTrue(self.usuario.check_password(self.NUEVA_CONTRASENA))
		self.assertTrue(
			self.usuario.codigos_verificacion.filter(usado_en__isnull=False).exists(),
		)

		response = self.client.post(
			reverse('usuarios_login'),
			{'username': self.usuario.username, 'password': self.NUEVA_CONTRASENA},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertIn('_auth_user_id', self.client.session)

	def test_codigo_solo_se_puede_usar_una_vez(self):
		self.solicitar_codigo()
		codigo = self.codigo_enviado()
		self.confirmar(codigo)

		response = self.confirmar(codigo, contrasena='Otra-clave-segura-555!')

		self.assertContains(response, 'no es válido o expiró')
		self.usuario.refresh_from_db()
		self.assertTrue(self.usuario.check_password(self.NUEVA_CONTRASENA))

	def test_codigo_expirado_no_cambia_la_contrasena(self):
		self.solicitar_codigo()
		codigo = self.codigo_enviado()
		self.usuario.codigos_verificacion.update(
			expira_en=timezone.now() - timedelta(seconds=1),
		)

		response = self.confirmar(codigo)

		self.assertContains(response, 'no es válido o expiró')
		self.usuario.refresh_from_db()
		self.assertTrue(self.usuario.check_password('Clave-inicial-segura-934!'))

	def test_codigo_incorrecto_se_bloquea_tras_cinco_intentos(self):
		self.solicitar_codigo()
		correcto = self.codigo_enviado()
		incorrecto = '000000' if correcto != '000000' else '111111'

		for _ in range(5):
			response = self.confirmar(incorrecto)
			self.assertContains(response, 'El código es incorrecto')

		response = self.confirmar(correcto)

		self.assertContains(response, 'no es válido o expiró')
		self.usuario.refresh_from_db()
		self.assertTrue(self.usuario.check_password('Clave-inicial-segura-934!'))

	def test_codigo_con_longitud_incorrecta_se_rechaza(self):
		self.solicitar_codigo()

		response = self.confirmar('1234')

		self.assertContains(response, 'Ingresa los 6 dígitos del código.')

	def test_contrasena_debil_no_consume_el_codigo(self):
		self.solicitar_codigo()
		codigo = self.codigo_enviado()

		response = self.confirmar(codigo, contrasena='12345678')

		self.assertEqual(response.status_code, 200)
		self.usuario.refresh_from_db()
		self.assertTrue(self.usuario.check_password('Clave-inicial-segura-934!'))
		self.assertFalse(
			self.usuario.codigos_verificacion.filter(usado_en__isnull=False).exists(),
		)
		self.assertRedirects(
			self.confirmar(codigo),
			reverse('usuarios_password_reset_complete'),
		)

	def test_codigo_de_registro_no_sirve_para_recuperar(self):
		CodigoVerificacion.objects.create(
			usuario=self.usuario,
			proposito=CodigoVerificacion.Proposito.REGISTRO,
			codigo_hash=make_password('123456'),
			expira_en=timezone.now() + timedelta(minutes=10),
		)

		response = self.confirmar('123456')

		self.assertContains(response, 'no es válido o expiró')

	def test_solicitud_con_correo_desconocido_no_revela_si_existe(self):
		response = self.solicitar_codigo('desconocido@example.com')

		self.assertRedirects(
			response,
			f'{reverse("usuarios_password_reset_codigo")}?email=desconocido%40example.com',
			fetch_redirect_response=False,
		)
		self.assertEqual(len(mail.outbox), 0)
		self.assertContains(
			self.client.get(response['Location']),
			'Si existe una cuenta activa con ese correo',
		)

	def test_usuario_inactivo_no_recibe_codigo(self):
		self.usuario.is_active = False
		self.usuario.save(update_fields=['is_active'])

		self.solicitar_codigo()

		self.assertEqual(len(mail.outbox), 0)
		self.assertFalse(self.usuario.codigos_verificacion.exists())

	def test_cuenta_desactivada_despues_de_pedir_codigo_no_puede_cambiar_clave(self):
		self.solicitar_codigo()
		codigo = self.codigo_enviado()
		self.usuario.is_active = False
		self.usuario.save(update_fields=['is_active'])

		response = self.confirmar(codigo)

		self.assertContains(response, 'no es válido o expiró')

	def test_reenvio_inmediato_no_envia_otro_correo(self):
		self.solicitar_codigo()

		response = self.solicitar_codigo()

		self.assertEqual(response.status_code, 302)
		self.assertEqual(len(mail.outbox), 1)

	def test_nuevo_codigo_invalida_el_anterior(self):
		self.solicitar_codigo()
		primero = self.codigo_enviado()
		self.usuario.codigos_verificacion.update(
			creado_en=timezone.now() - timedelta(minutes=5),
		)
		self.solicitar_codigo()
		segundo = self.codigo_enviado(1)

		if primero != segundo:
			response = self.confirmar(primero)
			self.assertContains(response, 'El código es incorrecto')
		self.assertRedirects(
			self.confirmar(segundo),
			reverse('usuarios_password_reset_complete'),
		)

	def test_fallo_de_envio_muestra_error_y_no_deja_codigo_guardado(self):
		with patch(
			'usuarios.views.send_mail',
			side_effect=smtplib.SMTPException('MessageRejected'),
		), self.assertLogs('usuarios.views', level='ERROR'):
			response = self.solicitar_codigo()

		self.assertEqual(response.status_code, 503)
		self.assertContains(response, 'No pudimos enviar el código', status_code=503)
		self.assertFalse(self.usuario.codigos_verificacion.exists())
		self.assertEqual(len(mail.outbox), 0)

	def test_el_enlace_olvidaste_tu_contrasena_lleva_al_formulario(self):
		response = self.client.get(reverse('usuarios_password_reset'))

		self.assertContains(response, 'Enviar código')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegistroPublicoTests(TestCase):
	@staticmethod
	def codigo_enviado():
		return next(
			line.strip()
			for line in mail.outbox[0].body.splitlines()
			if re.fullmatch(r'\d{4}', line.strip())
		)

	def datos_registro(self, **cambios):
		datos = {
			'nombre_completo': 'Candidata de prueba',
			'email': 'candidata@example.com',
			'comuna': 'La Serena',
			'tiene_experiencia': '',
			'experiencia': '',
		}
		datos.update(cambios)
		return datos

	def test_formulario_registro_aparece_junto_a_recuperacion(self):
		response = self.client.get(reverse('usuarios_login'))

		self.assertContains(response, 'Crear usuario')
		self.assertContains(response, '¿Olvidaste tu contraseña?')

	def test_registro_verifica_correo_guarda_perfil_y_crea_contrasena(self):
		response = self.client.post(
			reverse('usuarios_registro'),
			self.datos_registro(),
		)

		self.assertRedirects(
			response,
			f'{reverse("usuarios_registro_confirmar")}?email=candidata%40example.com',
		)
		usuario = get_user_model().objects.get(username='candidata@example.com')
		self.assertFalse(usuario.is_active)
		self.assertFalse(usuario.has_usable_password())
		perfil = PerfilPostulante.objects.get(correo='candidata@example.com')
		self.assertEqual(perfil.region, 'Región de Coquimbo')
		self.assertEqual(perfil.comuna, 'La Serena')
		self.assertFalse(perfil.tiene_experiencia)
		self.assertEqual(mail.outbox[0].to, ['candidata@example.com'])

		contrasena = 'Contrasena-segura-934!'
		response = self.client.post(
			reverse('usuarios_registro_confirmar'),
			{
				'email': usuario.email,
				'codigo': self.codigo_enviado(),
				'password1': contrasena,
				'password2': contrasena,
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Correo verificado.')
		usuario.refresh_from_db()
		self.assertTrue(usuario.is_active)
		self.assertTrue(usuario.check_password(contrasena))
		self.assertTrue(
			usuario.codigos_verificacion.filter(usado_en__isnull=False).exists(),
		)

	def test_verificacion_muestra_cuatro_casillas_para_el_codigo(self):
		self.client.post(
			reverse('usuarios_registro'),
			self.datos_registro(),
		)

		response = self.client.get(reverse('usuarios_registro_confirmar'))

		self.assertEqual(response.status_code, 200)
		html = response.content.decode()
		self.assertEqual(len(re.findall(r'<input[^>]*data-code-digit', html)), 4)
		self.assertEqual(html.count('placeholder="_"'), 4)

	def test_registro_solicita_experiencia_cuando_se_indica_que_si(self):
		response = self.client.post(
			reverse('usuarios_registro'),
			self.datos_registro(
				comuna='Copiapó',
				tiene_experiencia='on',
			),
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Cuéntanos brevemente tu experiencia laboral.')
		self.assertFalse(get_user_model().objects.filter(email='candidata@example.com').exists())

	def test_registro_guarda_experiencia_y_comuna_segun_region(self):
		response = self.client.post(
			reverse('usuarios_registro'),
			self.datos_registro(
				comuna='Santiago',
				tiene_experiencia='on',
				experiencia='Dos años en atención al cliente.',
			),
		)

		self.assertRedirects(
			response,
			f'{reverse("usuarios_registro_confirmar")}?email=candidata%40example.com',
		)
		perfil = PerfilPostulante.objects.get(correo='candidata@example.com')
		self.assertEqual(perfil.region, 'Región Metropolitana de Santiago')
		self.assertEqual(perfil.comuna, 'Santiago')
		self.assertTrue(perfil.tiene_experiencia)
		self.assertEqual(perfil.experiencia, 'Dos años en atención al cliente.')


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


class GestionUsuariosTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.grupo_administrador = Group.objects.create(name='Administrador')
		self.grupo_supervisor = Group.objects.create(name='Supervisor')
		self.grupo_administrativo = Group.objects.create(name='Administrativo')
		self.gestor = User.objects.create_user(
			username='gestor',
			password='clave-segura',
			email='gestor@example.com',
			is_staff=False,
		)
		self.gestor.groups.add(self.grupo_administrador)

	def conceder_permiso(self, codename):
		permiso = Permission.objects.get(
			content_type__app_label='auth',
			codename=codename,
		)
		self.gestor.user_permissions.add(permiso)
		permiso_listar = Permission.objects.get(
			content_type__app_label='auth',
			codename='view_user',
		)
		self.gestor.user_permissions.add(permiso_listar)
		self.client.force_login(self.gestor)

	def test_listado_exige_permiso_view_user(self):
		self.client.force_login(self.gestor)
		response = self.client.get(reverse('usuario_lista'))
		self.assertEqual(response.status_code, 403)

		self.conceder_permiso('view_user')
		response = self.client.get(reverse('usuario_lista'))
		self.assertEqual(response.status_code, 200)

	def test_listado_busca_por_usuario_nombre_apellido_y_correo(self):
		self.conceder_permiso('view_user')
		User = get_user_model()
		User.objects.create_user(
			username='candidata',
			first_name='Ana',
			last_name='Pérez',
			email='ana@example.com',
			password='clave-segura',
		)
		for consulta in ('candidata', 'Ana', 'Pérez', 'ana@example.com'):
			with self.subTest(consulta=consulta):
				response = self.client.get(reverse('usuario_lista'), {'q': consulta})
				self.assertContains(response, 'candidata')
				self.assertEqual(len(response.context['usuarios']), 1)

	def test_listado_pagina_resultados(self):
		self.conceder_permiso('view_user')
		User = get_user_model()
		User.objects.bulk_create([
			User(username=f'usuario_{numero}', email=f'u{numero}@example.com')
			for numero in range(12)
		])

		response = self.client.get(reverse('usuario_lista'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.context['usuarios']), 10)
		self.assertContains(response, 'Página 1 de 2')

	def test_crear_usuario_guarda_hash_correo_y_grupo(self):
		self.conceder_permiso('add_user')
		datos = {
			'username': 'nuevo',
			'first_name': 'Nombre',
			'last_name': 'Apellido',
			'email': 'nuevo@example.com',
			'grupo': self.grupo_supervisor.pk,
			'password1': 'Una-clave-fuerte-934!',
			'password2': 'Una-clave-fuerte-934!',
		}

		response = self.client.post(reverse('usuario_crear'), datos)

		self.assertRedirects(response, reverse('usuario_lista'))
		usuario = get_user_model().objects.get(username='nuevo')
		self.assertTrue(usuario.check_password(datos['password1']))
		self.assertEqual(usuario.email, datos['email'])
		self.assertEqual(list(usuario.groups.all()), [self.grupo_supervisor])

	def test_crear_usuario_rechaza_correo_repetido(self):
		self.conceder_permiso('add_user')
		datos = {
			'username': 'otro',
			'first_name': 'Otro',
			'last_name': 'Usuario',
			'email': self.gestor.email.upper(),
			'grupo': self.grupo_supervisor.pk,
			'password1': 'Una-clave-fuerte-934!',
			'password2': 'Una-clave-fuerte-934!',
		}

		response = self.client.post(reverse('usuario_crear'), datos)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ya existe un usuario con este correo electrónico.')
		self.assertFalse(get_user_model().objects.filter(username='otro').exists())
		self.assertContains(response, 'is-invalid')

	def test_editar_usuario_cambia_datos_grupo_y_estado(self):
		self.conceder_permiso('change_user')
		objetivo = get_user_model().objects.create_user(
			username='objetivo',
			password='clave-segura',
			email='objetivo@example.com',
		)
		datos = {
			'username': 'objetivo',
			'first_name': 'Editado',
			'last_name': 'Usuario',
			'email': 'editado@example.com',
			'grupo': self.grupo_administrativo.pk,
			'is_active': '',
		}

		response = self.client.post(reverse('usuario_editar', args=[objetivo.pk]), datos)

		self.assertRedirects(response, reverse('usuario_lista'))
		objetivo.refresh_from_db()
		self.assertEqual(objetivo.first_name, 'Editado')
		self.assertEqual(objetivo.email, 'editado@example.com')
		self.assertFalse(objetivo.is_active)
		self.assertEqual(list(objetivo.groups.all()), [self.grupo_administrativo])

	def test_no_puede_desactivarse_a_si_mismo(self):
		self.conceder_permiso('change_user')
		datos = {
			'username': self.gestor.username,
			'first_name': '',
			'last_name': '',
			'email': self.gestor.email,
			'grupo': self.grupo_administrador.pk,
			'is_active': '',
		}

		response = self.client.post(reverse('usuario_editar', args=[self.gestor.pk]), datos)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'No puedes desactivar tu propia cuenta.')
		self.gestor.refresh_from_db()
		self.assertTrue(self.gestor.is_active)

	def test_eliminar_muestra_confirmacion_y_elimina_otro_usuario(self):
		self.conceder_permiso('delete_user')
		objetivo = get_user_model().objects.create_user(
			username='eliminar',
			password='clave-segura',
		)
		url = reverse('usuario_eliminar', args=[objetivo.pk])

		response_get = self.client.get(url)
		self.assertEqual(response_get.status_code, 200)
		self.assertContains(response_get, '¿Seguro que deseas eliminar')

		response_post = self.client.post(url)
		self.assertRedirects(response_post, reverse('usuario_lista'))
		self.assertFalse(get_user_model().objects.filter(pk=objetivo.pk).exists())

	def test_no_puede_eliminarse_a_si_mismo(self):
		self.conceder_permiso('delete_user')

		response = self.client.post(
			reverse('usuario_eliminar', args=[self.gestor.pk]),
		)

		self.assertRedirects(response, reverse('usuario_lista'))
		self.assertTrue(get_user_model().objects.filter(pk=self.gestor.pk).exists())
