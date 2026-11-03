import logging
import secrets
import smtplib
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import (
	FormularioCodigoYContrasena,
	FormularioCrearUsuario,
	FormularioEditarUsuario,
	FormularioInicioSesion,
	FormularioPerfilUsuario,
	FormularioRecuperarContrasena,
	FormularioRegistroPublico,
)
from .mixins import LoginYPermisoRequeridoMixin
from .models import CodigoVerificacion, PerfilPostulante, PerfilUsuario
from .roles import obtener_dashboard_usuario


logger = logging.getLogger(__name__)
User = get_user_model()
CODIGO_MAX_INTENTOS = 5
LONGITUD_CODIGO_RECUPERACION = 6


class ErrorEntregaCorreo(Exception):
	pass


class CodigoReenvioReciente(Exception):
	pass


def _crear_y_enviar_codigo(usuario):
	ahora = timezone.now()
	proposito = CodigoVerificacion.Proposito.RECUPERACION
	codigos_recientes = CodigoVerificacion.objects.filter(
		usuario=usuario,
		proposito=proposito,
		creado_en__gte=ahora - timedelta(hours=1),
	)
	if (
		codigos_recientes.count() >= 5
		or codigos_recientes.filter(
			creado_en__gte=ahora - timedelta(seconds=60),
		).exists()
	):
		raise CodigoReenvioReciente

	longitud = LONGITUD_CODIGO_RECUPERACION
	duracion_minutos = settings.CODIGO_DURACION_MINUTOS
	codigo = f'{secrets.randbelow(10 ** longitud):0{longitud}d}'
	CodigoVerificacion.objects.filter(
		usuario=usuario,
		proposito=proposito,
		usado_en__isnull=True,
	).update(usado_en=timezone.now())
	CodigoVerificacion.objects.create(
		usuario=usuario,
		proposito=proposito,
		codigo_hash=make_password(codigo),
		expira_en=ahora + timedelta(minutes=duracion_minutos),
	)
	asunto = 'Código para recuperar tu contraseña'
	mensaje = render_to_string('usuarios/codigo_verificacion_email.txt', {
		'nombre': usuario.first_name or usuario.username,
		'codigo': codigo,
		'duracion_minutos': duracion_minutos,
	})
	try:
		enviados = send_mail(asunto, mensaje, None, [usuario.email], fail_silently=False)
	except (smtplib.SMTPException, OSError, UnicodeError) as error:
		logger.exception(
			'No se pudo enviar el código de %s al usuario %s.',
			proposito,
			usuario.pk,
		)
		raise ErrorEntregaCorreo from error
	if enviados != 1:
		logger.error(
			'El backend no confirmó el envío del código de %s al usuario %s.',
			proposito,
			usuario.pk,
		)
		raise ErrorEntregaCorreo


def _render_codigo_formulario(request, form, status=200):
	return render(
		request,
		'usuarios/codigo_form.html',
		{
			'form': form,
			'longitud': LONGITUD_CODIGO_RECUPERACION,
			'digitos': range(LONGITUD_CODIGO_RECUPERACION),
			'duracion_minutos': settings.CODIGO_DURACION_MINUTOS,
			'max_intentos': CODIGO_MAX_INTENTOS,
			'url_reintentar': reverse('usuarios_password_reset'),
		},
		status=status,
	)


class RedireccionDespuesGestionMixin:
	def get_success_url(self):
		if self.request.user.has_perm('auth.view_user'):
			return reverse('usuario_lista')
		return reverse('eventos_inicio')


class IniciarSesionView(LoginView):
	template_name = 'usuarios/login.html'
	authentication_form = FormularioInicioSesion
	redirect_authenticated_user = True


class CerrarSesionView(LogoutView):
	pass


class RecuperarContrasenaView(View):
	"""Paso 1: pide el correo y envía un código de un solo uso."""

	template_name = 'usuarios/password_reset_form.html'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name, {'form': FormularioRecuperarContrasena()})

	def post(self, request, *args, **kwargs):
		form = FormularioRecuperarContrasena(request.POST)
		if not form.is_valid():
			return render(request, self.template_name, {'form': form})

		email = form.cleaned_data['email']
		usuario = User.objects.filter(
			email__iexact=email,
			is_active=True,
		).order_by('pk').first()
		if usuario is not None:
			try:
				with transaction.atomic():
					_crear_y_enviar_codigo(usuario)
			except CodigoReenvioReciente:
				# Conserva el código vigente y mantiene la respuesta genérica.
				pass
			except ErrorEntregaCorreo:
				form.add_error(
					None,
					'No pudimos enviar el código. Inténtalo de nuevo más tarde.',
				)
				return render(request, self.template_name, {'form': form}, status=503)

		messages.info(
			request,
			'Si existe una cuenta activa con ese correo, te enviamos un código. '
			'Revisa tu bandeja de entrada y la carpeta de spam.',
		)
		return redirect(
			f'{reverse("usuarios_password_reset_codigo")}?'
			f'{urlencode({"email": email})}'
		)


class RegistroPublicoView(View):
	template_name = 'usuarios/registro.html'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name, {'form': FormularioRegistroPublico()})

	def post(self, request, *args, **kwargs):
		form = FormularioRegistroPublico(request.POST)
		if not form.is_valid():
			return render(request, self.template_name, {'form': form})

		datos = form.cleaned_data
		with transaction.atomic():
			usuario_existente = User.objects.filter(
				Q(email__iexact=datos['email'])
				| Q(username__iexact=datos['email']),
				is_active=False,
				is_staff=False,
				is_superuser=False,
				groups__isnull=True,
			).order_by('pk').first()
			if usuario_existente:
				usuario = usuario_existente
				usuario.email = datos['email']
				usuario.first_name = datos['nombre_completo']
				usuario.set_password(datos['password1'])
				usuario.is_active = True
				usuario.save(update_fields=['email', 'first_name', 'password', 'is_active'])
				perfil = PerfilPostulante.objects.filter(
					correo__iexact=datos['email'],
				).order_by('pk').first()
				if perfil is None:
					perfil = PerfilPostulante(
						nombre_completo=datos['nombre_completo'],
						correo=datos['email'],
					)
			else:
				usuario = User.objects.create_user(
					username=datos['email'],
					email=datos['email'],
					first_name=datos['nombre_completo'],
					password=datos['password1'],
					is_active=True,
				)
				perfil = PerfilPostulante.objects.filter(
					correo__iexact=datos['email'],
				).order_by('pk').first()
				if perfil is None:
					perfil = PerfilPostulante(
						nombre_completo=datos['nombre_completo'],
						correo=datos['email'],
					)
			perfil.nombre_completo = datos['nombre_completo']
			perfil.correo = datos['email']
			perfil.region = datos['region']
			perfil.comuna = datos['comuna']
			perfil.tiene_experiencia = datos['tiene_experiencia']
			perfil.experiencia = datos['experiencia']
			perfil.save()

		messages.success(
			request,
			'Tu cuenta fue creada correctamente. Ya puedes iniciar sesión.',
		)
		return redirect('usuarios_login')


class ConfirmarRecuperacionView(View):
	def get(self, request, *args, **kwargs):
		form = FormularioCodigoYContrasena(
			initial={'email': request.GET.get('email', '').strip().lower()},
			longitud=LONGITUD_CODIGO_RECUPERACION,
		)
		return _render_codigo_formulario(
			request,
			form,
		)

	def post(self, request, *args, **kwargs):
		form = FormularioCodigoYContrasena(
			request.POST,
			longitud=LONGITUD_CODIGO_RECUPERACION,
		)
		if not form.is_valid():
			return _render_codigo_formulario(
				request,
				form,
			)

		datos = form.cleaned_data
		with transaction.atomic():
			codigos = CodigoVerificacion.objects.select_for_update().filter(
				usuario__email__iexact=datos['email'],
				proposito=CodigoVerificacion.Proposito.RECUPERACION,
				usado_en__isnull=True,
				expira_en__gt=timezone.now(),
				intentos__lt=CODIGO_MAX_INTENTOS,
			)
			codigos = codigos.filter(usuario__is_active=True)
			codigo = codigos.order_by('-creado_en').first()
			if codigo is None:
				form.add_error(
					'codigo',
					'El código no es válido o expiró. Solicita uno nuevo para continuar.',
				)
				return _render_codigo_formulario(
					request,
					form,
				)
			if not check_password(datos['codigo'], codigo.codigo_hash):
				codigo.intentos += 1
				codigo.save(update_fields=['intentos'])
				form.add_error(
					'codigo',
					f'El código es incorrecto. Después de {CODIGO_MAX_INTENTOS} intentos tendrás que solicitar otro.',
				)
				return _render_codigo_formulario(
					request,
					form,
				)

			usuario = codigo.usuario
			try:
				validate_password(datos['password1'], user=usuario)
			except ValidationError as error:
				form.add_error('password1', error)
				return _render_codigo_formulario(request, form)

			usuario.set_password(datos['password1'])
			usuario.save(update_fields=['password'])
			codigo.usado_en = timezone.now()
			codigo.save(update_fields=['usado_en'])

		return redirect('usuarios_password_reset_complete')


class RestablecimientoContrasenaCompletoView(TemplateView):
	template_name = 'usuarios/password_reset_complete.html'


class UsuarioListaView(LoginYPermisoRequeridoMixin, ListView):
	model = User
	template_name = 'usuarios/usuario_lista.html'
	context_object_name = 'usuarios'
	permission_required = 'auth.view_user'
	paginate_by = 10

	def get_queryset(self):
		queryset = User.objects.prefetch_related('groups').order_by('username')
		consulta = self.request.GET.get('q', '').strip()
		if consulta:
			queryset = queryset.filter(
				Q(username__icontains=consulta)
				| Q(first_name__icontains=consulta)
				| Q(last_name__icontains=consulta)
				| Q(email__icontains=consulta)
			)
		return queryset

	def get_context_data(self, **kwargs):
		contexto = super().get_context_data(**kwargs)
		contexto['query'] = self.request.GET.get('q', '').strip()
		return contexto


class UsuarioCrearView(RedireccionDespuesGestionMixin, LoginYPermisoRequeridoMixin, CreateView):
	model = User
	form_class = FormularioCrearUsuario
	template_name = 'usuarios/usuario_formulario.html'
	permission_required = 'auth.add_user'
	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f'El usuario {self.object.username} fue creado correctamente.')
		return response

	def form_invalid(self, form):
		messages.error(self.request, 'No se pudo crear el usuario. Revisa los errores del formulario.')
		return super().form_invalid(form)


class UsuarioEditarView(RedireccionDespuesGestionMixin, LoginYPermisoRequeridoMixin, UpdateView):
	model = User
	form_class = FormularioEditarUsuario
	template_name = 'usuarios/usuario_formulario.html'
	permission_required = 'auth.change_user'
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['usuario_actual'] = self.request.user
		return kwargs

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f'El usuario {self.object.username} fue actualizado correctamente.')
		return response

	def form_invalid(self, form):
		messages.error(self.request, 'No se pudo guardar el usuario. Revisa los errores del formulario.')
		return super().form_invalid(form)


class UsuarioEliminarView(RedireccionDespuesGestionMixin, LoginYPermisoRequeridoMixin, DeleteView):
	model = User
	template_name = 'usuarios/usuario_confirmar_eliminacion.html'
	context_object_name = 'usuario_objetivo'
	permission_required = 'auth.delete_user'
	def dispatch(self, request, *args, **kwargs):
		if (
			request.user.is_authenticated
			and request.user.has_perm(self.permission_required)
		):
			usuario_objetivo = self.get_object()
			if usuario_objetivo.pk == request.user.pk:
				messages.error(request, 'No puedes eliminar tu propia cuenta.')
				return redirect('usuario_lista')
		return super().dispatch(request, *args, **kwargs)

	def form_valid(self, form):
		nombre_usuario = self.object.username
		response = super().form_valid(form)
		messages.success(self.request, f'El usuario {nombre_usuario} fue eliminado correctamente.')
		return response


@login_required
def redireccion_dashboard(request):
	_, dashboard_url = obtener_dashboard_usuario(request.user)
	return redirect(dashboard_url)


@login_required
def perfil_usuario(request):
	nombre_dashboard, dashboard_url = obtener_dashboard_usuario(request.user)
	if nombre_dashboard != 'Cliente':
		messages.info(
			request,
			'El perfil profesional está disponible para las cuentas de usuarios postulantes.',
		)
		return redirect(dashboard_url)

	perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
	editar = request.method == 'POST' or request.GET.get('editar') == '1'
	form = FormularioPerfilUsuario(
		request.POST or None,
		instance=perfil,
		usuario=request.user,
	)

	if request.method == 'POST':
		if form.is_valid():
			with transaction.atomic():
				form.save()
			messages.success(request, 'Tu perfil profesional se actualizó correctamente.')
			return redirect('usuarios_perfil')
		messages.error(request, 'No se pudo guardar el perfil. Revisa los campos indicados.')

	campos_completos = sum(bool(getattr(perfil, campo)) for campo in (
		'titular',
		'region',
		'comuna',
		'telefono',
		'acerca_de',
		'experiencia',
		'habilidades',
		'curriculum_url',
	))
	return render(request, 'usuarios/perfil.html', {
		'perfil': perfil,
		'form': form,
		'editar': editar,
		'habilidades_lista': [
			habilidad.strip()
			for habilidad in perfil.habilidades.split(',')
			if habilidad.strip()
		],
		'completitud_perfil': round(campos_completos / 8 * 100),
	})


def _mostrar_dashboard(request, nombre_grupo):
	if not request.user.groups.filter(name=nombre_grupo).exists():
		raise PermissionDenied
	return render(request, 'usuarios/dashboard.html', {'nombre_dashboard': nombre_grupo})


@login_required
def dashboard_administrador(request):
	return _mostrar_dashboard(request, 'Administrador')


@login_required
def dashboard_supervisor(request):
	return _mostrar_dashboard(request, 'Supervisor')


@login_required
def dashboard_administrativo(request):
	return _mostrar_dashboard(request, 'Administrativo')


@login_required
def dashboard_cliente(request):
	nombre_dashboard, dashboard_url = obtener_dashboard_usuario(request.user)
	if nombre_dashboard != 'Cliente':
		return redirect(dashboard_url)
	return render(request, 'usuarios/dashboard_cliente.html')


def permission_denied(request, exception=None):
	return render(request, '403.html', status=403)
