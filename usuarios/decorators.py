"""
Decorador propio para proteger vistas sin depender del sistema de
autenticación basado en base de datos de Django.

Se apoya únicamente en la sesión (request.session), la cual está
configurada para guardarse en una cookie firmada (ver SESSION_ENGINE
en settings.py) y NO en una base de datos.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def login_requerido(vista):
    """Redirige a la página de login si el usuario no ha iniciado sesión."""

    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.session.get('usuario_autenticado'):
            messages.warning(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect('usuarios_login')
        return vista(request, *args, **kwargs)

    return envoltura
