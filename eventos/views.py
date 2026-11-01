from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from usuarios.mixins import LoginYPermisoRequeridoMixin

from usuarios.models import PerfilPostulante

from .forms import (
    EmpresaForm,
    OfertaLaboralForm,
    PostulacionEstadoForm,
    RegistrarPostulacionForm,
)
from .models import CategoriaOferta, Empresa, Evento, OfertaLaboral, Postulacion

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


class EmpresaListaView(LoginYPermisoRequeridoMixin, ListView):
    model = Empresa
    template_name = 'eventos/empresa_lista.html'
    context_object_name = 'empresas'
    permission_required = 'eventos.view_empresa'
    paginate_by = 10

    def get_queryset(self):
        queryset = Empresa.objects.all()
        query = self.request.GET.get('q', '').strip()
        activa = self.request.GET.get('activa', '')

        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query)
                | Q(ubicacion__icontains=query)
                | Q(correo_contacto__icontains=query)
            )
        if activa == 'true':
            queryset = queryset.filter(activa=True)
        elif activa == 'false':
            queryset = queryset.filter(activa=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        context['filtro_activa'] = self.request.GET.get('activa', '')
        return context


class MensajeEmpresaGuardadoMixin:
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.mensaje_exito)
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'No se pudo guardar la empresa. Revisa los errores del formulario.')
        return super().form_invalid(form)


class EmpresaCrearView(
    MensajeEmpresaGuardadoMixin,
    LoginYPermisoRequeridoMixin,
    CreateView,
):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'eventos/empresa_formulario.html'
    permission_required = 'eventos.add_empresa'
    success_url = reverse_lazy('empresa_lista')
    mensaje_exito = 'La empresa se creó correctamente.'


class EmpresaEditarView(
    MensajeEmpresaGuardadoMixin,
    LoginYPermisoRequeridoMixin,
    UpdateView,
):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'eventos/empresa_formulario.html'
    permission_required = 'eventos.change_empresa'
    success_url = reverse_lazy('empresa_lista')
    mensaje_exito = 'La empresa se actualizó correctamente.'


class EmpresaEliminarView(LoginYPermisoRequeridoMixin, DeleteView):
    model = Empresa
    template_name = 'eventos/empresa_confirmar_eliminacion.html'
    context_object_name = 'empresa'
    permission_required = 'eventos.delete_empresa'
    success_url = reverse_lazy('empresa_lista')

    def form_valid(self, form):
        nombre = self.object.nombre
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f'No se puede eliminar “{nombre}” porque tiene ofertas laborales asociadas.',
            )
            return self.get(self.request, *self.args, **self.kwargs)
        messages.success(self.request, f'La empresa “{nombre}” se eliminó correctamente.')
        return response


class OfertaListaView(LoginYPermisoRequeridoMixin, ListView):
    model = OfertaLaboral
    template_name = 'eventos/oferta_lista.html'
    context_object_name = 'ofertas'
    permission_required = 'eventos.view_ofertalaboral'
    paginate_by = 10

    def get_queryset(self):
        queryset = OfertaLaboral.objects.select_related(
            'empresa',
            'categoria',
        ).order_by('-fecha_publicacion', 'titulo')
        query = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '')
        modalidad = self.request.GET.get('modalidad', '')
        categoria = self.request.GET.get('categoria', '')

        if query:
            queryset = queryset.filter(
                Q(titulo__icontains=query)
                | Q(empresa__nombre__icontains=query)
                | Q(categoria__nombre__icontains=query)
                | Q(ubicacion__icontains=query)
            )
        if estado in OfertaLaboral.Estado.values:
            queryset = queryset.filter(estado=estado)
        if modalidad in OfertaLaboral.Modalidad.values:
            queryset = queryset.filter(modalidad=modalidad)
        if categoria.isdigit():
            queryset = queryset.filter(categoria_id=int(categoria))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        context['filtro_estado'] = self.request.GET.get('estado', '')
        context['filtro_modalidad'] = self.request.GET.get('modalidad', '')
        context['filtro_categoria'] = self.request.GET.get('categoria', '')
        context['estados'] = OfertaLaboral.Estado.choices
        context['modalidades'] = OfertaLaboral.Modalidad.choices
        context['categorias'] = CategoriaOferta.objects.order_by('nombre')
        return context


class OfertaFormularioMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        messages.error(self.request, 'No se pudo guardar la oferta. Revisa los errores del formulario.')
        return super().form_invalid(form)


class OfertaCrearView(
    OfertaFormularioMixin,
    LoginYPermisoRequeridoMixin,
    CreateView,
):
    model = OfertaLaboral
    form_class = OfertaLaboralForm
    template_name = 'eventos/oferta_formulario.html'
    permission_required = 'eventos.add_ofertalaboral'
    success_url = reverse_lazy('oferta_lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'La oferta laboral se creó correctamente.')
        return response


class OfertaEditarView(
    OfertaFormularioMixin,
    LoginYPermisoRequeridoMixin,
    UpdateView,
):
    model = OfertaLaboral
    form_class = OfertaLaboralForm
    template_name = 'eventos/oferta_formulario.html'
    permission_required = 'eventos.change_ofertalaboral'
    success_url = reverse_lazy('oferta_lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'La oferta laboral se actualizó correctamente.')
        return response


class OfertaEliminarView(LoginYPermisoRequeridoMixin, DeleteView):
    model = OfertaLaboral
    template_name = 'eventos/oferta_confirmar_eliminacion.html'
    context_object_name = 'oferta'
    permission_required = 'eventos.delete_ofertalaboral'
    success_url = reverse_lazy('oferta_lista')

    def form_valid(self, form):
        titulo = self.object.titulo
        response = super().form_valid(form)
        messages.success(self.request, f'La oferta “{titulo}” se eliminó correctamente.')
        return response


class PostulacionCrearView(LoginYPermisoRequeridoMixin, FormView):
    form_class = RegistrarPostulacionForm
    template_name = 'eventos/postulacion_formulario.html'
    permission_required = 'eventos.add_postulacion'

    def get_initial(self):
        initial = super().get_initial()
        oferta_id = self.request.GET.get('oferta')
        if oferta_id and oferta_id.isdigit():
            initial['oferta'] = oferta_id
        return initial

    def form_valid(self, form):
        datos = form.cleaned_data
        error_oferta = None
        try:
            with transaction.atomic():
                oferta = OfertaLaboral.objects.select_for_update().get(
                    pk=datos['oferta'].pk,
                )
                if (
                    oferta.estado != OfertaLaboral.Estado.PUBLICADA
                    or (
                        oferta.fecha_cierre
                        and oferta.fecha_cierre < timezone.localdate()
                    )
                ):
                    error_oferta = 'La oferta ya no está publicada o se encuentra vencida.'
                elif PerfilPostulante.objects.filter(
                    correo__iexact=datos['correo'],
                    postulaciones__oferta=oferta,
                ).exists():
                    error_oferta = (
                        'Ya existe una postulación para esta oferta con ese correo electrónico.'
                    )
                if error_oferta:
                    form.add_error('oferta', error_oferta)
                else:
                    perfil = PerfilPostulante.objects.filter(
                        correo__iexact=datos['correo'],
                    ).order_by('pk').first()
                    if perfil is None:
                        perfil = PerfilPostulante.objects.create(
                            nombre_completo=datos['nombre_completo'],
                            correo=datos['correo'],
                            telefono=datos['telefono'],
                            profesion=datos['profesion'],
                            habilidades=datos['habilidades'],
                        )
                    else:
                        perfil.nombre_completo = datos['nombre_completo']
                        perfil.correo = datos['correo']
                        perfil.telefono = datos['telefono']
                        perfil.profesion = datos['profesion']
                        perfil.habilidades = datos['habilidades']
                        perfil.save(update_fields=[
                            'nombre_completo',
                            'correo',
                            'telefono',
                            'profesion',
                            'habilidades',
                        ])
                    self.object = Postulacion.objects.create(
                        oferta=oferta,
                        postulante=perfil,
                        carta_presentacion=datos['carta_presentacion'],
                    )
        except IntegrityError:
            if PerfilPostulante.objects.filter(
                correo__iexact=datos['correo'],
                postulaciones__oferta=datos['oferta'],
            ).exists():
                form.add_error(
                    'oferta',
                    'Ya existe una postulación para esta oferta con ese correo electrónico.',
                )
                messages.error(
                    self.request,
                    'El candidato ya postuló a esta oferta.',
                )
                return super().form_invalid(form)
            raise

        if error_oferta:
            messages.error(self.request, error_oferta)
            return super().form_invalid(form)

        messages.success(self.request, 'La postulación se registró correctamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('postulacion_detalle', kwargs={'pk': self.object.pk})

    def form_invalid(self, form):
        messages.error(
            self.request,
            'No se pudo registrar la postulación. Revisa los datos ingresados.',
        )
        return super().form_invalid(form)


class PostulacionListaView(LoginYPermisoRequeridoMixin, ListView):
    model = Postulacion
    template_name = 'eventos/postulacion_lista.html'
    context_object_name = 'postulaciones'
    permission_required = 'eventos.view_postulacion'
    paginate_by = 10

    def get_queryset(self):
        queryset = Postulacion.objects.select_related(
            'postulante',
            'oferta',
            'oferta__empresa',
        )
        estado = self.request.GET.get('estado', '')
        oferta = self.request.GET.get('oferta', '')
        if estado in Postulacion.Estado.values:
            queryset = queryset.filter(estado=estado)
        if oferta.isdigit():
            queryset = queryset.filter(oferta_id=int(oferta))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_estado'] = self.request.GET.get('estado', '')
        context['filtro_oferta'] = self.request.GET.get('oferta', '')
        context['estados'] = Postulacion.Estado.choices
        context['ofertas'] = OfertaLaboral.objects.order_by('titulo', 'pk')
        return context


class PostulacionDetalleView(LoginYPermisoRequeridoMixin, DetailView):
    model = Postulacion
    template_name = 'eventos/postulacion_detalle.html'
    context_object_name = 'postulacion'
    permission_required = 'eventos.view_postulacion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostulacionEstadoForm(instance=self.object)
        return context


class PostulacionEstadoView(LoginYPermisoRequeridoMixin, FormView):
    form_class = PostulacionEstadoForm
    template_name = 'eventos/postulacion_detalle.html'
    permission_required = 'eventos.change_postulacion'

    def dispatch(self, request, *args, **kwargs):
        self.postulacion = get_object_or_404(
            Postulacion.objects.select_related('postulante', 'oferta', 'oferta__empresa'),
            pk=kwargs['pk'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {'estado': self.postulacion.estado}

    def get(self, request, *args, **kwargs):
        return redirect('postulacion_detalle', pk=self.postulacion.pk)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.postulacion
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['postulacion'] = self.postulacion
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.postulacion = form.save()
        messages.success(self.request, 'El estado de la postulación se actualizó correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'No se pudo actualizar el estado de la postulación.')
        return redirect('postulacion_detalle', pk=self.postulacion.pk)

    def get_success_url(self):
        return reverse('postulacion_detalle', kwargs={'pk': self.postulacion.pk})
