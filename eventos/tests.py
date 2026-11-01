from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone

from usuarios.models import PerfilPostulante

from .models import (
	CategoriaOferta,
	Empresa,
	Evento,
	OfertaLaboral,
	Postulacion,
)


class EventoListadoTests(TestCase):
	def setUp(self):
		self.evento = Evento.objects.create(
			nombre='Feria de prueba',
			lugar='La Serena',
			fecha='2026-10-10',
		)

	def test_lista_muestra_eventos_de_base_de_datos(self):
		response = self.client.get('/eventos/lista/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.evento.nombre)
		self.assertIn(self.evento, response.context['eventos'])

	def test_busqueda_filtra_por_lugar(self):
		response = self.client.get('/eventos/lista/', {'q': 'Serena'})

		self.assertContains(response, self.evento.nombre)
		self.assertEqual(len(response.context['eventos']), 1)

	def test_visitante_no_ve_acciones_de_edicion(self):
		response = self.client.get('/eventos/lista/')

		self.assertNotContains(response, 'Modificar')
		self.assertNotContains(response, 'Eliminar')
		self.assertNotContains(response, 'Agregar evento')

class PostulacionesTests(TestCase):
	def setUp(self):
		self.perfil = PerfilPostulante.objects.create(
			nombre_completo='Postulante de prueba',
			profesion='Desarrollador',
		)
		self.empresa = Empresa.objects.create(nombre='Empresa de prueba')
		self.categoria = CategoriaOferta.objects.create(nombre='Informática')
		self.oferta = OfertaLaboral.objects.create(
			titulo='Desarrollador Django',
			descripcion='Desarrollar aplicaciones web.',
			ubicacion='La Serena',
			empresa=self.empresa,
			categoria=self.categoria,
		)

	def test_oferta_esta_asociada_a_empresa_y_categoria(self):
		self.assertIn(self.oferta, self.empresa.ofertas.all())
		self.assertIn(self.oferta, self.categoria.ofertas.all())

	def test_no_permite_postular_dos_veces_a_la_misma_oferta(self):
		Postulacion.objects.create(oferta=self.oferta, postulante=self.perfil)

		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Postulacion.objects.create(oferta=self.oferta, postulante=self.perfil)


class OfertasPublicasTests(TestCase):
	def setUp(self):
		self.empresa = Empresa.objects.create(
			nombre='Tecnología Serena',
			correo_contacto='trabajos@example.com',
		)
		self.categoria = CategoriaOferta.objects.create(nombre='Desarrollo')
		self.publicada = OfertaLaboral.objects.create(
			titulo='OfertaUnicaPythonXYZ',
			descripcion='Construir servicios web.',
			ubicacion='La Serena',
			estado=OfertaLaboral.Estado.PUBLICADA,
			empresa=self.empresa,
			categoria=self.categoria,
		)
		self.pendiente = OfertaLaboral.objects.create(
			titulo='Oferta aún no aprobada',
			descripcion='No debe aparecer al público.',
			ubicacion='Coquimbo',
			estado=OfertaLaboral.Estado.PENDIENTE,
			empresa=self.empresa,
			categoria=self.categoria,
		)

	def test_pagina_muestra_solo_ofertas_publicadas(self):
		response = self.client.get('/ofertas/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.publicada.titulo)
		self.assertNotContains(response, self.pendiente.titulo)
		self.assertContains(response, 'trabajos@example.com')

	def test_busqueda_filtra_ofertas_publicadas(self):
		response = self.client.get('/ofertas/', {'q': 'UnicaPythonXYZ'})

		self.assertContains(response, self.publicada.titulo)
		self.assertEqual(list(response.context['ofertas']), [self.publicada])

	def test_listado_publico_no_muestra_acciones_de_gestion(self):
		response = self.client.get('/ofertas/')

		self.assertNotContains(response, 'Modificar')
		self.assertNotContains(response, 'Eliminar')
		self.assertNotContains(response, 'Agregar oferta')

	def test_portada_enlaza_al_listado_de_ofertas(self):
		response = self.client.get('/eventos/')

		self.assertContains(response, 'href="/ofertas/"')


class GestionEmpresasTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_user(
			username='gestor_empresas',
			password='clave-segura',
		)

	def conceder_permiso(self, codename):
		permiso = Permission.objects.get(
			content_type__app_label='eventos',
			codename=codename,
		)
		permiso_listado = Permission.objects.get(
			content_type__app_label='eventos',
			codename='view_empresa',
		)
		self.usuario.user_permissions.add(permiso)
		self.usuario.user_permissions.add(permiso_listado)
		self.client.force_login(self.usuario)

	def test_listado_requiere_permiso_view_empresa(self):
		response = self.client.get(reverse('empresa_lista'))
		self.assertEqual(response.status_code, 403)

		self.conceder_permiso('view_empresa')
		response = self.client.get(reverse('empresa_lista'))
		self.assertEqual(response.status_code, 200)

	def test_listado_busca_nombre_ubicacion_o_correo(self):
		self.conceder_permiso('view_empresa')
		empresa = Empresa.objects.create(
			nombre='Empresa Coincidencia XYZ',
			ubicacion='Ciudad Coincidencia XYZ',
			correo_contacto='coincidencia@example.com',
		)

		for query in ('Coincidencia XYZ', 'coincidencia@example.com'):
			with self.subTest(query=query):
				response = self.client.get(reverse('empresa_lista'), {'q': query})
				self.assertContains(response, empresa.nombre)
				self.assertEqual(list(response.context['empresas']), [empresa])

	def test_listado_filtra_por_estado_y_pagina_de_diez(self):
		self.conceder_permiso('view_empresa')
		for numero in range(12):
			Empresa.objects.create(
				nombre=f'Empresa activa {numero:02}',
				activa=True,
			)
		for numero in range(2):
			Empresa.objects.create(
				nombre=f'Empresa inactiva {numero:02}',
				activa=False,
			)

		response = self.client.get(reverse('empresa_lista'), {'activa': 'false'})
		self.assertEqual(response.context['paginator'].count, 2)
		self.assertTrue(all(not empresa.activa for empresa in response.context['empresas']))

		response = self.client.get(reverse('empresa_lista'), {'activa': 'true'})
		self.assertEqual(len(response.context['empresas']), 10)
		self.assertEqual(response.context['paginator'].count, 13)

	def test_crear_empresa_valida_datos_y_nombre_unico_sin_distinguir_mayusculas(self):
		self.conceder_permiso('add_empresa')
		Empresa.objects.create(nombre='Empresa Existente')
		url = reverse('empresa_crear')
		datos = {
			'nombre': 'empresa existente',
			'descripcion': '',
			'ubicacion': '',
			'correo_contacto': '',
			'sitio_web': '',
			'activa': 'on',
		}

		response = self.client.post(url, datos)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ya existe una empresa con ese nombre.')
		self.assertContains(response, 'is-invalid')

		datos.update({
			'nombre': 'Nueva Empresa',
			'correo_contacto': 'correo-no-valido',
			'sitio_web': 'esto-no-es-url',
		})
		response = self.client.post(url, datos)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ingresa una dirección de correo electrónico válida.')
		self.assertContains(response, 'Ingresa una URL válida.')

		datos.update({
			'correo_contacto': 'contacto@example.com',
			'sitio_web': 'https://example.com',
		})
		response = self.client.post(url, datos)
		self.assertRedirects(response, reverse('empresa_lista'))
		self.assertTrue(Empresa.objects.filter(nombre='Nueva Empresa').exists())

	def test_editar_empresa_requiere_permiso_y_guarda_cambios(self):
		empresa = Empresa.objects.create(nombre='Empresa Original')
		self.conceder_permiso('change_empresa')

		response = self.client.post(reverse('empresa_editar', args=[empresa.pk]), {
			'nombre': 'Empresa Actualizada',
			'descripcion': 'Descripción nueva',
			'ubicacion': 'La Serena',
			'correo_contacto': 'nuevo@example.com',
			'sitio_web': 'https://example.com',
			'activa': '',
		})

		self.assertRedirects(response, reverse('empresa_lista'))
		empresa.refresh_from_db()
		self.assertEqual(empresa.nombre, 'Empresa Actualizada')
		self.assertFalse(empresa.activa)

	def test_eliminar_empresa_con_ofertas_muestra_mensaje_y_no_da_error_500(self):
		empresa = Empresa.objects.create(nombre='Empresa con oferta')
		categoria = CategoriaOferta.objects.create(nombre='Categoría prueba')
		OfertaLaboral.objects.create(
			titulo='Oferta protegida',
			descripcion='Descripción',
			ubicacion='La Serena',
			empresa=empresa,
			categoria=categoria,
		)
		self.conceder_permiso('delete_empresa')

		response = self.client.post(reverse('empresa_eliminar', args=[empresa.pk]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(
			response,
			'porque tiene ofertas laborales asociadas.',
		)
		self.assertTrue(Empresa.objects.filter(pk=empresa.pk).exists())

	def test_eliminar_empresa_sin_ofertas(self):
		empresa = Empresa.objects.create(nombre='Empresa eliminable')
		self.conceder_permiso('delete_empresa')
		url = reverse('empresa_eliminar', args=[empresa.pk])

		self.assertEqual(self.client.get(url).status_code, 200)
		response = self.client.post(url)
		self.assertRedirects(response, reverse('empresa_lista'))
		self.assertFalse(Empresa.objects.filter(pk=empresa.pk).exists())


class GestionOfertasTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_user(
			username='gestor_ofertas',
			password='clave-segura',
		)
		self.empresa = Empresa.objects.create(nombre='Empresa activa')
		self.empresa_inactiva = Empresa.objects.create(
			nombre='Empresa inactiva',
			activa=False,
		)
		self.categoria = CategoriaOferta.objects.create(nombre='Desarrollo de software')
		self.categoria_secundaria = CategoriaOferta.objects.create(nombre='Diseño gráfico')

	def conceder_permisos(self, *codenames):
		permisos = Permission.objects.filter(
			content_type__app_label='eventos',
			codename__in=codenames,
		)
		self.usuario.user_permissions.add(*permisos)
		self.client.force_login(self.usuario)

	def crear_oferta(self, **kwargs):
		datos = {
			'titulo': 'Desarrollador Python',
			'descripcion': 'Construir aplicaciones web.',
			'ubicacion': 'Ubicacion gestion XYZ',
			'modalidad': OfertaLaboral.Modalidad.REMOTA,
			'estado': OfertaLaboral.Estado.PENDIENTE,
			'empresa': self.empresa,
			'categoria': self.categoria,
		}
		datos.update(kwargs)
		return OfertaLaboral.objects.create(**datos)

	def datos_formulario(self, **kwargs):
		datos = {
			'titulo': 'Oferta creacion gestion XYZ',
			'descripcion': 'Construir aplicaciones web.',
			'requisitos': '',
			'ubicacion': 'Ubicacion prueba XYZ',
			'modalidad': OfertaLaboral.Modalidad.REMOTA,
			'estado': OfertaLaboral.Estado.PENDIENTE,
			'salario_minimo': '',
			'salario_maximo': '',
			'fecha_cierre': '',
			'empresa': self.empresa.pk,
			'categoria': self.categoria.pk,
		}
		datos.update(kwargs)
		return datos

	def test_listado_requiere_permiso_view_ofertalaboral(self):
		url = reverse('oferta_lista')
		self.assertEqual(self.client.get(url).status_code, 403)

		self.conceder_permisos('view_ofertalaboral')
		self.assertEqual(self.client.get(url).status_code, 200)

	def test_listado_busca_por_titulo_empresa_categoria_y_ubicacion(self):
		self.conceder_permisos('view_ofertalaboral')
		oferta = self.crear_oferta()

		for query in (
			'Desarrollador Python',
			'Empresa activa',
			'Desarrollo de software',
			'Ubicacion gestion XYZ',
		):
			with self.subTest(query=query):
				response = self.client.get(reverse('oferta_lista'), {'q': query})
				self.assertEqual(list(response.context['ofertas']), [oferta])

	def test_listado_filtra_por_estado_modalidad_categoria_y_pagina(self):
		self.conceder_permisos('view_ofertalaboral')
		publicada = self.crear_oferta(
			titulo='Oferta prueba publicada filtro XYZ',
			estado=OfertaLaboral.Estado.PUBLICADA,
		)
		self.crear_oferta(
			titulo='Oferta prueba híbrida XYZ',
			modalidad=OfertaLaboral.Modalidad.HIBRIDA,
			categoria=self.categoria_secundaria,
		)
		for numero in range(11):
			self.crear_oferta(titulo=f'Oferta filtro paginada XYZ {numero:02}')

		url = reverse('oferta_lista')
		response = self.client.get(url, {
			'estado': OfertaLaboral.Estado.PUBLICADA,
			'modalidad': OfertaLaboral.Modalidad.REMOTA,
			'categoria': self.categoria.pk,
		})
		self.assertEqual(list(response.context['ofertas']), [publicada])

		response = self.client.get(url, {'q': 'Oferta filtro paginada XYZ'})
		self.assertEqual(len(response.context['ofertas']), 10)
		self.assertEqual(response.context['paginator'].count, 11)

	def test_creacion_requiere_add_y_fuerza_estado_pendiente(self):
		url = reverse('oferta_crear')
		self.assertEqual(self.client.get(url).status_code, 403)
		self.conceder_permisos('add_ofertalaboral')

		response = self.client.post(url, self.datos_formulario(
			estado=OfertaLaboral.Estado.PUBLICADA,
		))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('oferta_lista'))
		oferta = OfertaLaboral.objects.get(titulo='Oferta creacion gestion XYZ')
		self.assertEqual(oferta.estado, OfertaLaboral.Estado.PENDIENTE)

	def test_usuario_con_permiso_change_puede_asignar_estado_al_crear(self):
		self.conceder_permisos('add_ofertalaboral', 'change_ofertalaboral')

		response = self.client.post(reverse('oferta_crear'), self.datos_formulario(
			estado=OfertaLaboral.Estado.PUBLICADA,
		))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('oferta_lista'))
		oferta = OfertaLaboral.objects.get(titulo='Oferta creacion gestion XYZ')
		self.assertEqual(oferta.estado, OfertaLaboral.Estado.PUBLICADA)

	def test_formulario_solo_ofrece_empresas_activas(self):
		self.conceder_permisos('add_ofertalaboral')
		response = self.client.get(reverse('oferta_crear'))
		opciones = response.context['form'].fields['empresa'].queryset

		self.assertEqual(list(opciones.filter(pk=self.empresa.pk)), [self.empresa])
		self.assertFalse(opciones.filter(pk=self.empresa_inactiva.pk).exists())
		self.assertNotContains(response, self.empresa_inactiva.nombre)

	def test_formulario_valida_salario_fecha_y_titulo(self):
		self.conceder_permisos('add_ofertalaboral')
		ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
		response = self.client.post(
			reverse('oferta_crear'),
			self.datos_formulario(
				titulo='Cort',
				salario_minimo='2000',
				salario_maximo='1000',
				fecha_cierre=ayer,
			),
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'El título debe tener al menos 5 caracteres.')
		self.assertContains(response, 'El salario máximo no puede ser menor que el salario mínimo.')
		self.assertContains(response, 'La fecha de cierre no puede ser anterior a hoy.')
		self.assertFalse(OfertaLaboral.objects.filter(titulo='Cort').exists())

	def test_edicion_y_eliminacion_requieren_sus_permisos(self):
		oferta = self.crear_oferta()
		self.assertEqual(
			self.client.get(reverse('oferta_editar', args=[oferta.pk])).status_code,
			403,
		)
		self.assertEqual(
			self.client.get(reverse('oferta_eliminar', args=[oferta.pk])).status_code,
			403,
		)

		self.conceder_permisos('change_ofertalaboral')
		response = self.client.post(
			reverse('oferta_editar', args=[oferta.pk]),
			self.datos_formulario(
				titulo='Oferta actualizada',
				estado=OfertaLaboral.Estado.PUBLICADA,
			),
		)
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('oferta_lista'))
		oferta.refresh_from_db()
		self.assertEqual(oferta.titulo, 'Oferta actualizada')
		self.assertEqual(oferta.estado, OfertaLaboral.Estado.PUBLICADA)

		self.conceder_permisos('delete_ofertalaboral')
		delete_url = reverse('oferta_eliminar', args=[oferta.pk])
		self.assertEqual(self.client.get(delete_url).status_code, 200)
		response = self.client.post(delete_url)
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('oferta_lista'))
		self.assertFalse(OfertaLaboral.objects.filter(pk=oferta.pk).exists())


class GestionPostulacionesTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_user(
			username='gestor_postulaciones',
			password='clave-segura',
		)
		self.empresa = Empresa.objects.create(nombre='Empresa postulaciones')
		self.categoria = CategoriaOferta.objects.create(nombre='Categoría postulaciones')
		self.oferta = self.crear_oferta()

	def crear_oferta(self, **kwargs):
		datos = {
			'titulo': 'Oferta vigente para postulaciones',
			'descripcion': 'Descripción de oferta.',
			'ubicacion': 'La Serena',
			'estado': OfertaLaboral.Estado.PUBLICADA,
			'empresa': self.empresa,
			'categoria': self.categoria,
		}
		datos.update(kwargs)
		return OfertaLaboral.objects.create(**datos)

	def conceder_permisos(self, *codenames):
		permisos = Permission.objects.filter(
			content_type__app_label='eventos',
			codename__in=codenames,
		)
		self.usuario.user_permissions.add(*permisos)
		self.client.force_login(self.usuario)

	def datos_formulario(self, **kwargs):
		datos = {
			'nombre_completo': 'Candidata de prueba',
			'correo': 'candidata@example.com',
			'telefono': '+56 9 1234 5678',
			'profesion': 'Desarrolladora',
			'habilidades': 'Python, Django',
			'oferta': self.oferta.pk,
			'carta_presentacion': (
				'Me interesa esta oportunidad y cuento con experiencia '
				'relevante para el cargo ofrecido.'
			),
		}
		datos.update(kwargs)
		return datos

	def test_registrar_postulacion_requiere_permiso_add(self):
		url = reverse('postulacion_crear')
		self.assertEqual(self.client.get(url).status_code, 403)

		self.conceder_permisos('add_postulacion')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Registrar postulación')

	def test_registro_crea_perfil_y_postulacion_enlazados(self):
		self.conceder_permisos('add_postulacion', 'view_postulacion')

		response = self.client.post(
			reverse('postulacion_crear'),
			self.datos_formulario(),
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		perfil = PerfilPostulante.objects.get(correo='candidata@example.com')
		postulacion = Postulacion.objects.get(oferta=self.oferta, postulante=perfil)
		self.assertRedirects(
			response,
			reverse('postulacion_detalle', args=[postulacion.pk]),
		)
		self.assertEqual(perfil.nombre_completo, 'Candidata de prueba')
		self.assertEqual(perfil.profesion, 'Desarrolladora')
		self.assertEqual(perfil.habilidades, 'Python, Django')
		self.assertEqual(postulacion.estado, Postulacion.Estado.RECIBIDA)
		self.assertContains(response, 'La postulación se registró correctamente.')

	def test_reutiliza_perfil_por_correo_y_actualiza_sus_datos(self):
		perfil = PerfilPostulante.objects.create(
			nombre_completo='Nombre anterior',
			correo='candidata@example.com',
			telefono='000',
		)
		otra_oferta = self.crear_oferta(titulo='Otra oferta vigente')
		self.conceder_permisos('add_postulacion', 'view_postulacion')

		response = self.client.post(
			reverse('postulacion_crear'),
			self.datos_formulario(
				nombre_completo='Nombre actualizado',
				telefono='999',
				oferta=otra_oferta.pk,
			),
		)

		self.assertEqual(response.status_code, 302)
		perfil.refresh_from_db()
		self.assertEqual(PerfilPostulante.objects.filter(correo__iexact='candidata@example.com').count(), 1)
		self.assertEqual(perfil.nombre_completo, 'Nombre actualizado')
		self.assertEqual(perfil.telefono, '999')
		self.assertTrue(Postulacion.objects.filter(oferta=otra_oferta, postulante=perfil).exists())

	def test_rechaza_postulacion_duplicada_sin_actualizar_el_perfil(self):
		perfil = PerfilPostulante.objects.create(
			nombre_completo='Nombre original',
			correo='candidata@example.com',
			telefono='111',
		)
		Postulacion.objects.create(
			oferta=self.oferta,
			postulante=perfil,
			carta_presentacion='Carta original para la postulación.',
		)
		self.conceder_permisos('add_postulacion')

		response = self.client.post(
			reverse('postulacion_crear'),
			self.datos_formulario(nombre_completo='Nombre que no debe guardarse'),
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ya existe una postulación para esta oferta con ese correo electrónico.')
		perfil.refresh_from_db()
		self.assertEqual(perfil.nombre_completo, 'Nombre original')
		self.assertEqual(Postulacion.objects.filter(oferta=self.oferta).count(), 1)

	def test_rollback_deja_sin_perfil_si_falla_la_creacion_de_postulacion(self):
		self.conceder_permisos('add_postulacion')

		with patch(
			'eventos.views.Postulacion.objects.create',
			side_effect=IntegrityError('fallo de persistencia'),
		):
			with self.assertRaises(IntegrityError):
				self.client.post(
					reverse('postulacion_crear'),
					self.datos_formulario(),
				)

		self.assertFalse(PerfilPostulante.objects.filter(
			correo='candidata@example.com',
		).exists())
		self.assertFalse(Postulacion.objects.exists())

	def test_solo_se_ofrecen_ofertas_publicadas_y_no_vencidas(self):
		self.crear_oferta(
			titulo='Oferta cerrada',
			estado=OfertaLaboral.Estado.CERRADA,
		)
		self.crear_oferta(
			titulo='Oferta vencida',
			fecha_cierre=timezone.localdate() - timedelta(days=1),
		)
		self.conceder_permisos('add_postulacion')

		response = self.client.get(reverse('postulacion_crear'))
		ofertas = response.context['form'].fields['oferta'].queryset

		self.assertIn(self.oferta, ofertas)
		self.assertFalse(ofertas.filter(titulo='Oferta cerrada').exists())
		self.assertFalse(ofertas.filter(titulo='Oferta vencida').exists())

	def test_validaciones_carta_y_oferta_publicada_vigente(self):
		self.conceder_permisos('add_postulacion')
		response = self.client.post(
			reverse('postulacion_crear'),
			self.datos_formulario(carta_presentacion='Muy breve.'),
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'La carta de presentación debe tener al menos 50 caracteres.')
		self.assertFalse(PerfilPostulante.objects.exists())

		cerrada = self.crear_oferta(
			titulo='Oferta no publicada',
			estado=OfertaLaboral.Estado.CERRADA,
		)
		response = self.client.post(
			reverse('postulacion_crear'),
			self.datos_formulario(oferta=cerrada.pk),
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Selecciona una oferta publicada y vigente.')
		self.assertFalse(PerfilPostulante.objects.exists())

	def test_listado_filtra_por_estado_y_oferta_y_detalle_requiere_view(self):
		perfil = PerfilPostulante.objects.create(
			nombre_completo='Candidato listado',
			correo='listado@example.com',
		)
		postulacion = Postulacion.objects.create(
			oferta=self.oferta,
			postulante=perfil,
			estado=Postulacion.Estado.ENTREVISTA,
			carta_presentacion='Carta de presentación con longitud suficiente.',
		)
		self.conceder_permisos('view_postulacion')

		response = self.client.get(reverse('postulacion_lista'), {
			'estado': Postulacion.Estado.ENTREVISTA,
			'oferta': self.oferta.pk,
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(list(response.context['postulaciones']), [postulacion])
		self.assertEqual(
			self.client.get(reverse('postulacion_detalle', args=[postulacion.pk])).status_code,
			200,
		)

	def test_cambio_estado_requiere_change_postulacion(self):
		perfil = PerfilPostulante.objects.create(
			nombre_completo='Candidato estado',
			correo='estado@example.com',
		)
		postulacion = Postulacion.objects.create(
			oferta=self.oferta,
			postulante=perfil,
			carta_presentacion='Carta para el cambio del estado de postulación.',
		)
		self.conceder_permisos('view_postulacion', 'add_postulacion')
		url = reverse('postulacion_estado', args=[postulacion.pk])

		response = self.client.post(url, {'estado': Postulacion.Estado.SELECCIONADA})
		self.assertEqual(response.status_code, 403)
		postulacion.refresh_from_db()
		self.assertEqual(postulacion.estado, Postulacion.Estado.RECIBIDA)

		self.conceder_permisos('view_postulacion', 'change_postulacion')
		response = self.client.post(url, {'estado': Postulacion.Estado.ENTREVISTA})
		self.assertEqual(response.status_code, 302)
		self.assertRedirects(
			response,
			reverse('postulacion_detalle', args=[postulacion.pk]),
		)
		postulacion.refresh_from_db()
		self.assertEqual(postulacion.estado, Postulacion.Estado.ENTREVISTA)
