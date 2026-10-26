from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def login_view(request):
    if request.user.is_authenticated:
        return redirect('usuarios_perfil')

    error = None

    if request.method == 'POST':
        nombre_usuario = request.POST.get('usuario', '').strip()
        password = request.POST.get('password', '')

        usuario_django = authenticate(
            request,
            username=nombre_usuario,
            password=password,
        )
        if usuario_django is not None:
            auth_login(request, usuario_django)
            messages.success(
                request,
                f'Bienvenido/a, {usuario_django.get_full_name() or usuario_django.username}.',
            )
            return redirect('usuarios_perfil')

        error = "Usuario o contrasena incorrectos."

    contexto = {'error': error}
    return render(request, 'usuarios/login.html', contexto)


def logout_view(request):
    auth_logout(request)
    messages.info(request, "Sesion cerrada correctamente.")
    return redirect('usuarios_login')


@login_required
def perfil_view(request):
    usuario = request.user
    rol = usuario.groups.order_by('name').values_list('name', flat=True).first()
    contexto = {
        'nombre_usuario': usuario.get_full_name() or usuario.username,
        'usuario': usuario.username,
        'rol_usuario': rol or 'Sin rol asignado',
        'fecha_actual': datetime.now().strftime('%d-%m-%Y %H:%M'),
    }
    return render(request, 'usuarios/perfil.html', contexto)
