from django.contrib import admin
from django.urls import path, include
from eventos.views import lista_ofertas

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('eventos.urls')),
    path('noticias/', include('noticias.urls')),
    path('eventos/', include('eventos.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('ofertas/', lista_ofertas, name='ofertas_lista'),
]