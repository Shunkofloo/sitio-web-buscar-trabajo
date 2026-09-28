from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import models


class UsuarioSitio(models.Model):
	usuario = models.CharField(max_length=150, unique=True)
	password = models.CharField(max_length=128)
	nombre = models.CharField(max_length=200)
	rol = models.CharField(max_length=50, default='invitado')

	class Meta:
		ordering = ['usuario']
		verbose_name = 'usuario del sitio'
		verbose_name_plural = 'usuarios del sitio'

	def save(self, *args, **kwargs):
		try:
			identify_hasher(self.password)
		except ValueError:
			self.password = make_password(self.password)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.usuario


class PerfilPostulante(models.Model):
	usuario = models.OneToOneField(
		UsuarioSitio,
		on_delete=models.CASCADE,
		related_name='perfil_postulante',
	)
	correo = models.EmailField(blank=True)
	telefono = models.CharField(max_length=30, blank=True)
	profesion = models.CharField(max_length=150, blank=True)
	resumen_profesional = models.TextField(blank=True)
	habilidades = models.TextField(blank=True, help_text='Separar habilidades con comas.')
	curriculum_url = models.URLField(blank=True)

	class Meta:
		ordering = ['usuario__nombre']
		verbose_name = 'perfil postulante'
		verbose_name_plural = 'perfiles postulantes'

	def __str__(self):
		return self.usuario.nombre
