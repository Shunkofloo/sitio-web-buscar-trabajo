from django.urls import path, include
from eventos.views import lista_ofertas

urlpatterns = [
    path('', include('eventos.urls')),
    path('noticias/', include('noticias.urls')),
    path('eventos/', include('eventos.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('gestion/empresas/', include('eventos.gestion_urls')),
    path('gestion/ofertas/', include('eventos.ofertas_urls')),
    path('gestion/postulaciones/', include('eventos.postulaciones_urls')),
    path('ofertas/', lista_ofertas, name='ofertas_lista'),
]

handler403 = 'usuarios.views.permission_denied'