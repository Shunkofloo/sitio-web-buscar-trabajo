from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .models import CategoriaOferta, Empresa, OfertaLaboral, Postulacion
from usuarios.models import PerfilPostulante


class FormularioBootstrapMixin:
	def aplicar_clases_bootstrap(self):
		for campo in self.fields.values():
			clase = 'form-check-input' if isinstance(campo.widget, forms.CheckboxInput) else 'form-control'
			campo.widget.attrs.setdefault('class', clase)

	def full_clean(self):
		super().full_clean()
		for nombre in self.errors:
			if nombre in self.fields:
				clases = self.fields[nombre].widget.attrs.get('class', '')
				if 'is-invalid' not in clases.split():
					self.fields[nombre].widget.attrs['class'] = f'{clases} is-invalid'.strip()


class EmpresaForm(FormularioBootstrapMixin, forms.ModelForm):
	correo_contacto = forms.EmailField(
		label='Correo de contacto',
		required=False,
		error_messages={'invalid': 'Ingresa una dirección de correo electrónico válida.'},
	)
	sitio_web = forms.URLField(
		label='Sitio web',
		required=False,
		error_messages={'invalid': 'Ingresa una URL válida.'},
	)

	class Meta:
		model = Empresa
		fields = (
			'nombre',
			'descripcion',
			'ubicacion',
			'correo_contacto',
			'sitio_web',
			'activa',
		)
		labels = {
			'nombre': 'Nombre',
			'descripcion': 'Descripción',
			'ubicacion': 'Ubicación',
			'correo_contacto': 'Correo de contacto',
			'sitio_web': 'Sitio web',
			'activa': 'Empresa activa',
		}
		widgets = {
			'descripcion': forms.Textarea(attrs={'rows': 4}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.aplicar_clases_bootstrap()

	def clean_nombre(self):
		nombre = self.cleaned_data['nombre'].strip()
		existentes = Empresa.objects.filter(nombre__iexact=nombre)
		if self.instance.pk:
			existentes = existentes.exclude(pk=self.instance.pk)
		if existentes.exists():
			raise ValidationError('Ya existe una empresa con ese nombre.')
		return nombre


class OfertaLaboralForm(FormularioBootstrapMixin, forms.ModelForm):
	class Meta:
		model = OfertaLaboral
		fields = (
			'titulo',
			'descripcion',
			'requisitos',
			'ubicacion',
			'modalidad',
			'estado',
			'salario_minimo',
			'salario_maximo',
			'fecha_cierre',
			'empresa',
			'categoria',
		)
		labels = {
			'titulo': 'Título',
			'descripcion': 'Descripción',
			'requisitos': 'Requisitos',
			'ubicacion': 'Ubicación',
			'modalidad': 'Modalidad',
			'estado': 'Estado',
			'salario_minimo': 'Salario mínimo',
			'salario_maximo': 'Salario máximo',
			'fecha_cierre': 'Fecha de cierre',
			'empresa': 'Empresa',
			'categoria': 'Categoría',
		}
		widgets = {
			'descripcion': forms.Textarea(attrs={'rows': 4}),
			'requisitos': forms.Textarea(attrs={'rows': 3}),
			'salario_minimo': forms.NumberInput(attrs={'step': '0.01'}),
			'salario_maximo': forms.NumberInput(attrs={'step': '0.01'}),
			'fecha_cierre': forms.DateInput(attrs={'type': 'date'}),
		}

	def __init__(self, *args, usuario=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.usuario = usuario
		self.fields['empresa'].queryset = Empresa.objects.filter(activa=True).order_by('nombre')
		self.fields['categoria'].queryset = CategoriaOferta.objects.order_by('nombre')
		if not (usuario and usuario.has_perm('eventos.change_ofertalaboral')):
			self.fields['estado'].disabled = True
			self.fields['estado'].initial = (
				self.instance.estado
				if self.instance.pk
				else OfertaLaboral.Estado.PENDIENTE
			)
		self.aplicar_clases_bootstrap()

	def clean(self):
		datos = super().clean()
		salario_minimo = datos.get('salario_minimo')
		salario_maximo = datos.get('salario_maximo')
		fecha_cierre = datos.get('fecha_cierre')
		titulo = datos.get('titulo')

		if salario_minimo is not None and salario_maximo is not None:
			if salario_maximo < salario_minimo:
				self.add_error(
					'salario_maximo',
					'El salario máximo no puede ser menor que el salario mínimo.',
				)

		if fecha_cierre and fecha_cierre < timezone.localdate():
			self.add_error('fecha_cierre', 'La fecha de cierre no puede ser anterior a hoy.')

		if titulo and len(titulo.strip()) < 5:
			self.add_error('titulo', 'El título debe tener al menos 5 caracteres.')

		return datos

	def save(self, commit=True):
		oferta = super().save(commit=False)
		if not (self.usuario and self.usuario.has_perm('eventos.change_ofertalaboral')):
			if not oferta.pk:
				oferta.estado = OfertaLaboral.Estado.PENDIENTE
			else:
				oferta.estado = OfertaLaboral.objects.only('estado').get(pk=oferta.pk).estado
		if commit:
			oferta.save()
			self.save_m2m()
		return oferta


class RegistrarPostulacionForm(FormularioBootstrapMixin, forms.Form):
	nombre_completo = forms.CharField(
		label='Nombre completo',
		max_length=200,
	)
	correo = forms.EmailField(label='Correo electrónico')
	telefono = forms.CharField(label='Teléfono', max_length=30, required=False)
	profesion = forms.CharField(label='Profesión', max_length=150, required=False)
	habilidades = forms.CharField(
		label='Habilidades',
		required=False,
		widget=forms.Textarea(attrs={'rows': 3}),
		help_text='Puedes separar las habilidades con comas.',
	)
	oferta = forms.ModelChoiceField(
		label='Oferta laboral',
		queryset=OfertaLaboral.objects.none(),
		error_messages={
			'invalid_choice': 'Selecciona una oferta publicada y vigente.',
			'required': 'Selecciona una oferta laboral.',
		},
	)
	carta_presentacion = forms.CharField(
		label='Carta de presentación',
		widget=forms.Textarea(attrs={'rows': 6}),
		help_text='Mínimo recomendado: 50 caracteres.',
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['oferta'].queryset = OfertaLaboral.objects.filter(
			estado=OfertaLaboral.Estado.PUBLICADA,
		).filter(
			Q(fecha_cierre__isnull=True)
			| Q(fecha_cierre__gte=timezone.localdate()),
		).select_related('empresa', 'categoria')
		self.fields['oferta'].queryset = self.fields['oferta'].queryset.order_by(
			'titulo',
			'pk',
		)
		self.aplicar_clases_bootstrap()

	def clean_nombre_completo(self):
		return self.cleaned_data['nombre_completo'].strip()

	def clean_carta_presentacion(self):
		carta = self.cleaned_data['carta_presentacion'].strip()
		if len(carta) < 50:
			raise ValidationError(
				'La carta de presentación debe tener al menos 50 caracteres.'
			)
		return carta

	def clean(self):
		datos = super().clean()
		oferta = datos.get('oferta')
		correo = datos.get('correo')
		if oferta and correo and PerfilPostulante.objects.filter(
			correo__iexact=correo,
			postulaciones__oferta=oferta,
		).exists():
			self.add_error(
				'oferta',
				'Ya existe una postulación para esta oferta con ese correo electrónico.',
			)
		return datos


class PostulacionEstadoForm(FormularioBootstrapMixin, forms.ModelForm):
	class Meta:
		model = Postulacion
		fields = ('estado',)
		labels = {'estado': 'Estado de la postulación'}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.aplicar_clases_bootstrap()
