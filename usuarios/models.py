from django.db import models


class PerfilPostulante(models.Model):
	nombre_completo = models.CharField(max_length=200)
	correo = models.EmailField(blank=True)
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
