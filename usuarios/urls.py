from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='usuarios_login'),
    path('logout/', views.logout_view, name='usuarios_logout'),
    path('perfil/', views.perfil_view, name='usuarios_perfil'),
]
