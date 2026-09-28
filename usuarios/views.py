from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect

from .decorators import login_requerido
from .models import UsuarioSitio


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin:index')

    # Si ya inicio sesion, lo mandamos directo al perfil.
    if request.session.get('usuario_autenticado'):
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
        if usuario_django is not None and usuario_django.is_staff:
            auth_login(request, usuario_django)
            messages.success(request, f'Bienvenido/a, {usuario_django.username}.')
            return redirect('admin:index')

        usuario = UsuarioSitio.objects.filter(usuario__iexact=nombre_usuario).first()

        if usuario is not None and usuario.rol == 'administrador':
            error = 'Para ingresar al panel usa una cuenta creada con createsuperuser.'
        elif usuario is not None and check_password(password, usuario.password):
            request.session['usuario_autenticado'] = usuario.usuario
            request.session['nombre_usuario'] = usuario.nombre
            request.session['rol_usuario'] = usuario.rol
            messages.success(request, f"Bienvenido/a, {usuario.nombre}!")
            return redirect('usuarios_perfil')
        else:
            error = "Usuario o contrasena incorrectos."

    contexto = {'error': error}
    return render(request, 'usuarios/login.html', contexto)


def logout_view(request):
    auth_logout(request)
    messages.info(request, "Sesion cerrada correctamente.")
    return redirect('usuarios_login')


@login_requerido
def perfil_view(request):
    contexto = {
        'nombre_usuario': request.session.get('nombre_usuario'),
        'usuario': request.session.get('usuario_autenticado'),
        'rol_usuario': request.session.get('rol_usuario'),
        'fecha_actual': datetime.now().strftime('%d-%m-%Y %H:%M'),
    }
    return render(request, 'usuarios/perfil.html', contexto)
