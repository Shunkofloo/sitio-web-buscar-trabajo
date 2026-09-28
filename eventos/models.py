from django.db import models
from django.db.models import Q

from usuarios.models import PerfilPostulante


class Evento(models.Model):
	nombre = models.CharField(max_length=200)
	lugar = models.CharField(max_length=200)
	fecha = models.DateField()
	imagen = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ['fecha', 'nombre']

	def __str__(self):
		return self.nombre


class Empresa(models.Model):
	nombre = models.CharField(max_length=150, unique=True)
	descripcion = models.TextField(blank=True)
	ubicacion = models.CharField(max_length=150, blank=True)
	correo_contacto = models.EmailField(blank=True)
	sitio_web = models.URLField(blank=True)
	activa = models.BooleanField(default=True)

	class Meta:
		ordering = ['nombre']

	def __str__(self):
		return self.nombre


class CategoriaOferta(models.Model):
	nombre = models.CharField(max_length=100, unique=True)
	descripcion = models.CharField(max_length=250, blank=True)

	class Meta:
		ordering = ['nombre']
		verbose_name = 'categoría de oferta'
		verbose_name_plural = 'categorías de ofertas'

	def __str__(self):
		return self.nombre


class OfertaLaboral(models.Model):
	class Modalidad(models.TextChoices):
		PRESENCIAL = 'presencial', 'Presencial'
		HIBRIDA = 'hibrida', 'Híbrida'
		REMOTA = 'remota', 'Remota'

	class Estado(models.TextChoices):
		BORRADOR = 'borrador', 'Borrador'
		PENDIENTE = 'pendiente', 'Pendiente de revisión'
		PUBLICADA = 'publicada', 'Publicada'
		CERRADA = 'cerrada', 'Cerrada'
		RECHAZADA = 'rechazada', 'Rechazada'

	titulo = models.CharField(max_length=200)
	descripcion = models.TextField()
	requisitos = models.TextField(blank=True)
	ubicacion = models.CharField(max_length=150)
	modalidad = models.CharField(
		max_length=12,
		choices=Modalidad.choices,
		default=Modalidad.PRESENCIAL,
	)
	estado = models.CharField(
		max_length=12,
		choices=Estado.choices,
		default=Estado.PENDIENTE,
	)
	salario_minimo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	salario_maximo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	fecha_publicacion = models.DateField(auto_now_add=True)
	fecha_cierre = models.DateField(null=True, blank=True)
	empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='ofertas')
	categoria = models.ForeignKey(CategoriaOferta, on_delete=models.PROTECT, related_name='ofertas')

	class Meta:
		ordering = ['-fecha_publicacion', 'titulo']
		constraints = [
			models.CheckConstraint(
				condition=(
					Q(salario_minimo__isnull=True)
					| Q(salario_maximo__isnull=True)
					| Q(salario_maximo__gte=models.F('salario_minimo'))
				),
				name='oferta_rango_salario_valido',
			)
		]

	def __str__(self):
		return self.titulo


class Postulacion(models.Model):
	class Estado(models.TextChoices):
		RECIBIDA = 'recibida', 'Recibida'
		REVISION = 'revision', 'En revisión'
		ENTREVISTA = 'entrevista', 'Entrevista'
		SELECCIONADA = 'seleccionada', 'Seleccionada'
		RECHAZADA = 'rechazada', 'Rechazada'

	oferta = models.ForeignKey(OfertaLaboral, on_delete=models.CASCADE, related_name='postulaciones')
	postulante = models.ForeignKey(PerfilPostulante, on_delete=models.CASCADE, related_name='postulaciones')
	fecha_postulacion = models.DateTimeField(auto_now_add=True)
	estado = models.CharField(
		max_length=12,
		choices=Estado.choices,
		default=Estado.RECIBIDA,
	)
	carta_presentacion = models.TextField(blank=True)

	class Meta:
		ordering = ['-fecha_postulacion']
		constraints = [
			models.UniqueConstraint(
				fields=['oferta', 'postulante'],
				name='postulacion_unica_por_oferta_y_usuario',
			)
		]

	def __str__(self):
		return f'{self.postulante} - {self.oferta}'
