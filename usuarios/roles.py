from django.urls import reverse


DASHBOARDS_POR_GRUPO = (
	('Administrador', 'usuarios_dashboard_administrador'),
	('Supervisor', 'usuarios_dashboard_supervisor'),
	('Administrativo', 'usuarios_dashboard_administrativo'),
)


def obtener_dashboard_usuario(usuario):
	for nombre_grupo, nombre_ruta in DASHBOARDS_POR_GRUPO:
		if usuario.groups.filter(name=nombre_grupo).exists():
			return nombre_grupo, reverse(nombre_ruta)
	return None, None
