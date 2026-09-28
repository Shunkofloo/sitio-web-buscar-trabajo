from django.db import models


class CategoriaNoticia(models.Model):
	nombre = models.CharField(max_length=100, unique=True)

	class Meta:
		ordering = ['nombre']
		verbose_name = 'categoría de noticia'
		verbose_name_plural = 'categorías de noticias'

	def __str__(self):
		return self.nombre


class Noticia(models.Model):
	categoria = models.ForeignKey(
		CategoriaNoticia,
		on_delete=models.PROTECT,
		related_name='noticias',
	)
	titulo = models.CharField(max_length=250)
	resumen = models.TextField()
	fecha = models.DateField()
	imagen = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ['-fecha', 'titulo']
		verbose_name_plural = 'noticias'

	def __str__(self):
		return self.titulo
