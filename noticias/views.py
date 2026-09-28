from django.shortcuts import render

from .models import Noticia

def inicio(request):
    return render(request, 'noticias/inicio.html')

def lista_noticias(request):
    query = request.GET.get('q', '').strip()
    noticias = Noticia.objects.select_related('categoria')
    if query:
        noticias = noticias.filter(titulo__icontains=query) | noticias.filter(
            resumen__icontains=query
        )
    return render(request, 'noticias/detalle.html', {
        'noticias': noticias,
        'query': query,
    })
