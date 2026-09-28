from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='noticias_inicio'),
    path('lista/', views.lista_noticias, name='noticias_lista'),
]