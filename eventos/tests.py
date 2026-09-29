from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from usuarios.models import PerfilPostulante, UsuarioSitio

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

	def test_evento_esta_registrado_en_admin(self):
		self.assertIn(Evento, admin.site._registry)

	def test_visitante_no_ve_acciones_de_edicion(self):
		response = self.client.get('/eventos/lista/')

		self.assertNotContains(response, 'Modificar')
		self.assertNotContains(response, 'Eliminar')
		self.assertNotContains(response, 'Agregar evento')

	def test_superusuario_ve_enlace_real_para_modificar_evento(self):
		administrador = get_user_model().objects.create_superuser(
			username='admin_eventos',
			email='admin-eventos@example.com',
			password='clave-admin-segura',
		)
		self.client.force_login(administrador)

		response = self.client.get('/eventos/lista/')

		self.assertContains(response, f'/admin/eventos/evento/{self.evento.pk}/change/')
		self.assertContains(response, '/admin/eventos/evento/add/')


class GestionOfertasAdminTests(TestCase):
	def setUp(self):
		usuario = UsuarioSitio.objects.create(
			usuario='postulante_test',
			password='clave-segura',
			nombre='Postulante de prueba',
			rol='invitado',
		)
		self.perfil = PerfilPostulante.objects.create(
			usuario=usuario,
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

	def test_entidades_del_portal_estan_registradas_en_admin(self):
		for modelo in (Empresa, CategoriaOferta, OfertaLaboral, Postulacion):
			with self.subTest(modelo=modelo.__name__):
				self.assertIn(modelo, admin.site._registry)

		self.assertIn(self.oferta, self.empresa.ofertas.all())
		self.assertIn(self.oferta, self.categoria.ofertas.all())

	def test_panel_admin_muestra_listados_de_gestion(self):
		administrador = get_user_model().objects.create_superuser(
			username='admin_prueba',
			email='admin@example.com',
			password='clave-segura-prueba',
		)
		self.client.force_login(administrador)
		urls = (
			'/admin/eventos/empresa/',
			'/admin/eventos/categoriaoferta/',
			'/admin/eventos/ofertalaboral/',
			'/admin/eventos/postulacion/',
			'/admin/usuarios/perfilpostulante/',
		)

		for url in urls:
			with self.subTest(url=url):
				self.assertEqual(self.client.get(url).status_code, 200)

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

	def test_visitante_no_ve_ni_puede_abrir_acciones_de_admin(self):
		response = self.client.get('/ofertas/')

		self.assertNotContains(response, 'Modificar')
		self.assertNotContains(response, 'Eliminar')
		self.assertNotContains(response, 'Agregar oferta')
		edit_response = self.client.get(
			f'/admin/eventos/ofertalaboral/{self.publicada.pk}/change/'
		)
		self.assertEqual(edit_response.status_code, 302)

	def test_superusuario_ve_enlaces_reales_de_gestion_de_ofertas(self):
		administrador = get_user_model().objects.create_superuser(
			username='admin_ofertas',
			email='admin-ofertas@example.com',
			password='clave-admin-segura',
		)
		self.client.force_login(administrador)

		response = self.client.get('/ofertas/')

		self.assertContains(
			response,
			f'/admin/eventos/ofertalaboral/{self.publicada.pk}/change/',
		)
		self.assertContains(response, '/admin/eventos/ofertalaboral/add/')
		self.assertContains(response, f'/admin/eventos/ofertalaboral/{self.publicada.pk}/delete/')

	def test_portada_enlaza_al_listado_de_ofertas(self):
		response = self.client.get('/eventos/')

		self.assertContains(response, 'href="/ofertas/"')
