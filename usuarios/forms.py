from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
	AuthenticationForm,
	PasswordResetForm,
	SetPasswordForm,
	UserCreationForm,
)
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError


User = get_user_model()
GRUPOS_DISPONIBLES = ('Administrador', 'Supervisor', 'Administrativo')


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
			'placeholder': 'Nombre de usuario',
		})
		self.fields['password'].widget.attrs.update({
			'class': 'form-control',
			'placeholder': 'Contraseña',
		})


class FormularioRecuperarContrasena(FormularioBootstrapMixin, PasswordResetForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['email'].label = 'Correo electrónico'
		self.fields['email'].widget.attrs.update({
			'class': 'form-control',
			'autocomplete': 'email',
		})


class FormularioRestablecerContrasena(FormularioBootstrapMixin, SetPasswordForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['new_password1'].label = 'Nueva contraseña'
		self.fields['new_password2'].label = 'Confirmar nueva contraseña'
		self.aplicar_clases_bootstrap()
