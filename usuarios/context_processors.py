from .mixins import grupo_principal
from .roles import obtener_dashboard_usuario


def dashboard_usuario(request):
	if not request.user.is_authenticated:
		return {}

	_, dashboard_url = obtener_dashboard_usuario(request.user)

	return {
		'nombre_grupo_usuario': grupo_principal(request.user) or 'Sin grupo asignado',
		'dashboard_usuario_url': dashboard_url,
	}
