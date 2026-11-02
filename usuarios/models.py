from django.conf import settings
from django.db import models


class PerfilPostulante(models.Model):
	nombre_completo = models.CharField(max_length=200)
	correo = models.EmailField(blank=True)
	region = models.CharField(max_length=100, blank=True)
	comuna = models.CharField(max_length=100, blank=True)
	tiene_experiencia = models.BooleanField(default=False)
	experiencia = models.TextField(blank=True)
	telefono = models.CharField(max_length=30, blank=True)
	profesion = models.CharField(max_length=150, blank=True)
	resumen_profesional = models.TextField(blank=True)
	habilidades = models.TextField(blank=True, help_text='Separar habilidades con comas.')
	curriculum_url = models.URLField(blank=True)

	class Meta:
		ordering = ['nombre_completo']
		verbose_name = 'perfil postulante'
		verbose_name_plural = 'perfiles postulantes'

	def __str__(self):
		return self.nombre_completo


class PerfilUsuario(models.Model):
	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='perfil_profesional',
	)
	titular = models.CharField(max_length=180, blank=True)
	region = models.CharField(max_length=100, blank=True)
	comuna = models.CharField(max_length=100, blank=True)
	telefono = models.CharField(max_length=30, blank=True)
	acerca_de = models.TextField(blank=True)
	experiencia = models.TextField(blank=True)
	habilidades = models.TextField(blank=True, help_text='Separar habilidades con comas.')
	curriculum_url = models.URLField(blank=True)

	class Meta:
		verbose_name = 'perfil de usuario'
		verbose_name_plural = 'perfiles de usuario'

	def __str__(self):
		return f'Perfil de {self.usuario.get_full_name() or self.usuario.username}'


class CodigoVerificacion(models.Model):
	class Proposito(models.TextChoices):
		REGISTRO = 'registro', 'Verificar registro'
		RECUPERACION = 'recuperacion', 'Recuperar contraseña'

	usuario = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='codigos_verificacion',
	)
	proposito = models.CharField(max_length=20, choices=Proposito.choices)
	codigo_hash = models.CharField(max_length=128)
	expira_en = models.DateTimeField()
	intentos = models.PositiveSmallIntegerField(default=0)
	creado_en = models.DateTimeField(auto_now_add=True)
	usado_en = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-creado_en']
		indexes = [
			models.Index(fields=['usuario', 'proposito', 'usado_en']),
		]
