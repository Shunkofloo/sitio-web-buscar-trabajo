from .roles import obtener_dashboard_usuario


def dashboard_usuario(request):
	if not request.user.is_authenticated:
		return {}

	nombre_dashboard, dashboard_url = obtener_dashboard_usuario(request.user)

	return {
		'nombre_grupo_usuario': nombre_dashboard,
		'es_cliente': nombre_dashboard == 'Cliente',
		'dashboard_usuario_url': dashboard_url,
	}
