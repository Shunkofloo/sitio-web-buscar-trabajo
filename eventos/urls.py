from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='eventos_inicio'),
    path('ofertas/', views.lista_ofertas, name='ofertas_lista'),
    path('lista/', views.lista_eventos, name='eventos_lista'),
]