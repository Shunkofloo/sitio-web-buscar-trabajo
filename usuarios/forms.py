from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q

from .models import PerfilPostulante, PerfilUsuario


User = get_user_model()
GRUPOS_DISPONIBLES = ('Administrador', 'Supervisor', 'Administrativo')
COMUNAS_POR_REGION = {
	'Región de Coquimbo': ('La Serena', 'Coquimbo'),
	'Región de Atacama': ('Copiapó',),
	'Región Metropolitana de Santiago': ('Santiago',),
}
REGIONES_POR_COMUNA = {
	comuna: region
	for region, comunas in COMUNAS_POR_REGION.items()
	for comuna in comunas
}


class FormularioBootstrapMixin:
	def aplicar_clases_bootstrap(self):
		for field in self.fields.values():
			clase = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
			field.widget.attrs.setdefault('class', clase)

	def full_clean(self):
		super().full_clean()
		for nombre, errores in self.errors.items():
			if nombre in self.fields:
				clases = self.fields[nombre].widget.attrs.get('class', '')
				if 'is-invalid' not in clases.split():
					self.fields[nombre].widget.attrs['class'] = f'{clases} is-invalid'.strip()


class FormularioCrearUsuario(FormularioBootstrapMixin, UserCreationForm):
	first_name = forms.CharField(label='Nombre', max_length=150)
	last_name = forms.CharField(label='Apellido', max_length=150)
	email = forms.EmailField(label='Correo electrónico', required=True)
	grupo = forms.ModelChoiceField(
		label='Grupo',
		queryset=Group.objects.filter(name__in=GRUPOS_DISPONIBLES).order_by('name'),
		empty_label='Selecciona un grupo',
	)

	class Meta(UserCreationForm.Meta):
		model = User
		fields = ('username', 'first_name', 'last_name', 'email')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['username'].label = 'Nombre de usuario'
		self.fields['password1'].label = 'Contraseña'
		self.fields['password2'].label = 'Confirmar contraseña'
		self.aplicar_clases_bootstrap()

	def clean_email(self):
		email = self.cleaned_data['email'].strip()
		if User.objects.filter(email__iexact=email).exists():
			raise ValidationError('Ya existe un usuario con este correo electrónico.')
		return email

	def save(self, commit=True):
		usuario = super().save(commit=False)
		usuario.first_name = self.cleaned_data['first_name'].strip()
		usuario.last_name = self.cleaned_data['last_name'].strip()
		usuario.email = self.cleaned_data['email'].strip()
		if commit:
			usuario.save()
			usuario.groups.set((self.cleaned_data['grupo'],))
		return usuario


class FormularioEditarUsuario(FormularioBootstrapMixin, forms.ModelForm):
	grupo = forms.ModelChoiceField(
		label='Grupo',
		queryset=Group.objects.filter(name__in=GRUPOS_DISPONIBLES).order_by('name'),
		empty_label='Selecciona un grupo',
	)

	class Meta:
		model = User
		fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
		labels = {
			'username': 'Nombre de usuario',
			'first_name': 'Nombre',
			'last_name': 'Apellido',
			'email': 'Correo electrónico',
			'is_active': 'Usuario activo',
		}

	def __init__(self, *args, **kwargs):
		self.usuario_actual = kwargs.pop('usuario_actual', None)
		super().__init__(*args, **kwargs)
		self.fields['email'].required = True
		self.fields['grupo'].initial = self.instance.groups.filter(
			name__in=GRUPOS_DISPONIBLES,
		).first()
		self.aplicar_clases_bootstrap()

	def clean_email(self):
		email = self.cleaned_data['email'].strip()
		if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
			raise ValidationError('Ya existe un usuario con este correo electrónico.')
		return email

	def clean(self):
		datos = super().clean()
		if (
			self.usuario_actual
			and self.instance.pk == self.usuario_actual.pk
			and datos.get('is_active') is False
		):
			self.add_error('is_active', 'No puedes desactivar tu propia cuenta.')
		return datos

	def save(self, commit=True):
		usuario = super().save(commit=commit)
		if commit:
			usuario.groups.set((self.cleaned_data['grupo'],))
		return usuario


class FormularioPerfilUsuario(FormularioBootstrapMixin, forms.ModelForm):
	nombre = forms.CharField(label='Nombre', max_length=150)
	apellido = forms.CharField(label='Apellido', max_length=150, required=False)

	class Meta:
		model = PerfilUsuario
		fields = (
			'titular',
			'region',
			'comuna',
			'telefono',
			'acerca_de',
			'experiencia',
			'habilidades',
			'curriculum_url',
		)
		labels = {
			'titular': 'Titular profesional',
			'region': 'Región',
			'comuna': 'Comuna',
			'telefono': 'Teléfono',
			'acerca_de': 'Acerca de mí',
			'experiencia': 'Experiencia profesional',
			'habilidades': 'Habilidades',
			'curriculum_url': 'Enlace a mi currículum',
		}
		help_texts = {
			'titular': 'Por ejemplo: Desarrolladora web | Atención al cliente | Estudiante de enfermería',
			'habilidades': 'Escribe tus habilidades separadas por comas.',
			'curriculum_url': 'Pega un enlace seguro a tu currículum, si tienes uno.',
		}
		widgets = {
			'acerca_de': forms.Textarea(attrs={'rows': 5}),
			'experiencia': forms.Textarea(attrs={'rows': 5}),
			'habilidades': forms.Textarea(attrs={'rows': 3}),
			'curriculum_url': forms.URLInput(attrs={'placeholder': 'https://'}),
		}

	def __init__(self, *args, **kwargs):
		self.usuario = kwargs.pop('usuario')
		super().__init__(*args, **kwargs)
		self.fields['nombre'].initial = self.usuario.first_name
		self.fields['apellido'].initial = self.usuario.last_name
		self.order_fields((
			'nombre',
			'apellido',
			'titular',
			'region',
			'comuna',
			'telefono',
			'acerca_de',
			'experiencia',
			'habilidades',
			'curriculum_url',
		))
		self.aplicar_clases_bootstrap()

	def save(self, commit=True):
		perfil = super().save(commit=commit)
		if commit:
			self.usuario.first_name = self.cleaned_data['nombre'].strip()
			self.usuario.last_name = self.cleaned_data['apellido'].strip()
			self.usuario.save(update_fields=('first_name', 'last_name'))
		return perfil


class FormularioInicioSesion(AuthenticationForm):
	error_messages = {
		**AuthenticationForm.error_messages,
		'invalid_login': 'Usuario o contraseña incorrectos. Verifica tus datos e inténtalo de nuevo.',
	}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['username'].widget.attrs.update({
			'class': 'form-control',
			'autofocus': True,
			'placeholder': 'Correo electrónico o usuario',
		})
		self.fields['password'].widget.attrs.update({
			'class': 'form-control',
			'placeholder': 'Contraseña',
		})


class FormularioRecuperarContrasena(FormularioBootstrapMixin, forms.Form):
	email = forms.EmailField(
		label='Correo electrónico',
		widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.aplicar_clases_bootstrap()

	def clean_email(self):
		return self.cleaned_data['email'].strip().lower()


class FormularioRegistroPublico(FormularioBootstrapMixin, forms.Form):
	nombre_completo = forms.CharField(label='Nombre', max_length=150)
	email = forms.EmailField(label='Correo electrónico')
	comuna = forms.ChoiceField(
		label='Región y comuna',
		choices=[
			('', 'Selecciona tu comuna'),
			*[
				(region, [(comuna, comuna) for comuna in comunas])
				for region, comunas in COMUNAS_POR_REGION.items()
			],
		],
	)
	tiene_experiencia = forms.BooleanField(
		label='¿Tienes experiencia laboral?',
		required=False,
	)
	experiencia = forms.CharField(
		label='Cuéntanos tu experiencia',
		required=False,
		widget=forms.Textarea(attrs={'rows': 4}),
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.aplicar_clases_bootstrap()

	def clean_nombre_completo(self):
		return self.cleaned_data['nombre_completo'].strip()

	def clean_email(self):
		email = self.cleaned_data['email'].strip().lower()
		usuario = User.objects.filter(
			Q(email__iexact=email) | Q(username__iexact=email),
		).order_by('pk').first()
		if usuario and (
			usuario.is_active
			or usuario.is_staff
			or usuario.is_superuser
			or usuario.groups.exists()
			or usuario.has_usable_password()
			or not PerfilPostulante.objects.filter(correo__iexact=email).exists()
		):
			raise ValidationError('Ya existe una cuenta registrada con ese correo.')
		return email

	def clean(self):
		datos = super().clean()
		comuna = datos.get('comuna')
		if comuna:
			datos['region'] = REGIONES_POR_COMUNA[comuna]
		if datos.get('tiene_experiencia'):
			experiencia = (datos.get('experiencia') or '').strip()
			if not experiencia:
				self.add_error(
					'experiencia',
					'Cuéntanos brevemente tu experiencia laboral.',
				)
			datos['experiencia'] = experiencia
		else:
			datos['experiencia'] = ''
		return datos


class FormularioCodigoYContrasena(FormularioBootstrapMixin, forms.Form):
	email = forms.EmailField(label='Correo electrónico')
	codigo = forms.CharField(label='Código')
	password1 = forms.CharField(
		label='Nueva contraseña',
		widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
	)
	password2 = forms.CharField(
		label='Confirmar contraseña',
		widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
	)

	def __init__(self, *args, longitud=4, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['codigo'] = forms.CharField(
			label=f'Código de {longitud} dígitos',
			max_length=longitud,
			validators=[RegexValidator(
				rf'^\d{{{longitud}}}$',
				f'Ingresa los {longitud} dígitos del código.',
			)],
			widget=forms.TextInput(attrs={
				'autocomplete': 'one-time-code',
				'inputmode': 'numeric',
				'maxlength': str(longitud),
			}),
		)
		self.aplicar_clases_bootstrap()

	def clean_email(self):
		return self.cleaned_data['email'].strip().lower()

	def clean(self):
		datos = super().clean()
		if (
			datos.get('password1')
			and datos.get('password2')
			and datos['password1'] != datos['password2']
		):
			self.add_error('password2', 'Las contraseñas no coinciden.')
		return datos
