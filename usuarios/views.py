from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
	LoginView,
	LogoutView,
	PasswordResetCompleteView,
	PasswordResetConfirmView,
	PasswordResetDoneView,
	PasswordResetView,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import (
	FormularioCrearUsuario,
	FormularioEditarUsuario,
	FormularioInicioSesion,
	FormularioRecuperarContrasena,
	FormularioRestablecerContrasena,
)
from .mixins import LoginYPermisoRequeridoMixin
from .roles import obtener_dashboard_usuario


User = get_user_model()


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


class RecuperarContrasenaView(PasswordResetView):
	template_name = 'usuarios/password_reset_form.html'
	email_template_name = 'usuarios/password_reset_email.html'
	subject_template_name = 'usuarios/password_reset_subject.txt'
	form_class = FormularioRecuperarContrasena
	success_url = reverse_lazy('usuarios_password_reset_done')


class RecuperarContrasenaEnviadaView(PasswordResetDoneView):
	template_name = 'usuarios/password_reset_done.html'


class ConfirmarRestablecimientoContrasenaView(PasswordResetConfirmView):
	template_name = 'usuarios/password_reset_confirm.html'
	form_class = FormularioRestablecerContrasena
	success_url = reverse_lazy('usuarios_password_reset_complete')


class RestablecimientoContrasenaCompletoView(PasswordResetCompleteView):
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
	if dashboard_url is None:
		messages.error(
			request,
			'Tu cuenta no tiene asignado un grupo con un dashboard disponible. Contacta al administrador.',
		)
		return redirect('eventos_inicio')
	return redirect(dashboard_url)


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


def permission_denied(request, exception=None):
	return render(request, '403.html', status=403)
