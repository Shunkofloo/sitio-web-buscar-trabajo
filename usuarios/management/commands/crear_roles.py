import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
	help = 'Crea los grupos, permisos y usuarios de demostración del sitio.'

	usuarios_demo = (
		('admin_demo', 'admin_demo@example.com', 'Administrador'),
		('supervisor_demo', 'supervisor_demo@example.com', 'Supervisor'),
		('administrativo_demo', 'administrativo_demo@example.com', 'Administrativo'),
	)

	def handle(self, *args, **options):
		password = os.environ.get('DEMO_PASSWORD')
		if not password:
			raise CommandError(
				'La variable de entorno DEMO_PASSWORD es obligatoria y no puede estar vacía.'
			)

		with transaction.atomic():
			grupos = {}
			grupos_creados = 0
			for nombre in ('Administrador', 'Supervisor', 'Administrativo'):
				grupos[nombre], creado = Group.objects.get_or_create(name=nombre)
				grupos_creados += creado

			permisos_administrador = set(
				Permission.objects.filter(
					content_type__app_label__in=('eventos', 'noticias'),
				)
			)
			permisos_administrador.update(
				self._permisos(
					'auth',
					'User',
					('view_user', 'add_user', 'change_user', 'delete_user'),
				)
			)
			permisos_administrador.update(self._permisos('auth', 'Group', ('view_group',)))

			permisos_supervisor = set()
			permisos_supervisor.update(
				self._permisos('eventos', 'Empresa', ('view_empresa', 'add_empresa', 'change_empresa'))
			)
			permisos_supervisor.update(
				self._permisos(
					'eventos',
					'OfertaLaboral',
					('view_ofertalaboral', 'add_ofertalaboral', 'change_ofertalaboral'),
				)
			)
			permisos_supervisor.update(
				self._permisos(
					'eventos',
					'Postulacion',
					('view_postulacion', 'add_postulacion', 'change_postulacion'),
				)
			)
			permisos_supervisor.update(
				self._permisos('eventos', 'CategoriaOferta', ('view_categoriaoferta',))
			)

			permisos_administrativo = set()
			permisos_administrativo.update(
				self._permisos('eventos', 'Empresa', ('view_empresa',))
			)
			permisos_administrativo.update(
				self._permisos('eventos', 'OfertaLaboral', ('view_ofertalaboral',))
			)
			permisos_administrativo.update(
				self._permisos(
					'eventos',
					'Postulacion',
					('view_postulacion', 'add_postulacion'),
				)
			)

			permisos_por_grupo = {
				'Administrador': permisos_administrador,
				'Supervisor': permisos_supervisor,
				'Administrativo': permisos_administrativo,
			}
			for nombre, permisos in permisos_por_grupo.items():
				grupos[nombre].permissions.set(permisos)

			User = get_user_model()
			usuarios_creados = 0
			for username, email, grupo_nombre in self.usuarios_demo:
				usuario, creado = User.objects.get_or_create(
					username=username,
					defaults={'email': email},
				)
				usuarios_creados += creado
				usuario.email = email
				usuario.set_password(password)
				usuario.save(update_fields=('email', 'password'))
				usuario.groups.set((grupos[grupo_nombre],))

		self.stdout.write(
			self.style.SUCCESS(
				'Roles listos: '
				f'{grupos_creados} grupos nuevos, '
				f'{usuarios_creados} usuarios demo nuevos; '
				'permisos y grupos de usuarios sincronizados.'
			)
		)

	@staticmethod
	def _permisos(app_label, model_name, codigos):
		content_type = ContentType.objects.get(
			app_label=app_label,
			model=model_name.lower(),
		)
		return set(
			Permission.objects.filter(
				content_type=content_type,
				codename__in=codigos,
			)
		)
