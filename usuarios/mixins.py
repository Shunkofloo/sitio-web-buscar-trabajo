from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class LoginYPermisoRequeridoMixin(LoginRequiredMixin, PermissionRequiredMixin):
	raise_exception = True


def grupo_principal(user):
	if not user.is_authenticated:
		return None

	grupos_principales = ('Administrador', 'Supervisor', 'Administrativo')
	for nombre_grupo in grupos_principales:
		if user.groups.filter(name=nombre_grupo).exists():
			return nombre_grupo

	return user.groups.order_by('name').values_list('name', flat=True).first()
