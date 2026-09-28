from django.shortcuts import render

from .models import Evento, OfertaLaboral

def inicio(request):
    return render(request, 'eventos/inicio.html')

def lista_eventos(request):
    query = request.GET.get('q', '').strip()
    eventos = Evento.objects.all()
    if query:
        eventos = eventos.filter(nombre__icontains=query) | eventos.filter(
            lugar__icontains=query
        )
    return render(request, 'eventos/detalle.html', {
        'eventos': eventos,
        'query': query,
    })


def lista_ofertas(request):
    query = request.GET.get('q', '').strip()
    ofertas = OfertaLaboral.objects.filter(
        estado=OfertaLaboral.Estado.PUBLICADA
    ).select_related('empresa', 'categoria')
    if query:
        ofertas = ofertas.filter(
            titulo__icontains=query
        ) | ofertas.filter(
            descripcion__icontains=query
        ) | ofertas.filter(
            ubicacion__icontains=query
        ) | ofertas.filter(
            empresa__nombre__icontains=query
        ) | ofertas.filter(
            categoria__nombre__icontains=query
        )
    return render(request, 'eventos/ofertas.html', {
        'ofertas': ofertas,
        'query': query,
    })
