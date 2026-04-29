from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404
from django.urls import reverse
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import models
from .models import Evento, Momento, Foto, Asistente, normalizar_texto
from .forms import FotoUploadForm
from usuarios.views import login_view
from usuarios.urls import urlpatterns as usuarios_urlpatterns
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from openpyxl import load_workbook

def intro(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)

    asistentes = []
    busqueda = request.GET.get("q", "").strip()
    mensaje = None
    error = None

    if busqueda:
        texto_busqueda = normalizar_texto(busqueda)
        palabras = texto_busqueda.split()

        qs = Asistente.objects.filter(evento=evento)

        for palabra in palabras:
            qs = qs.filter(nombre_busqueda__icontains=palabra)

        asistentes = qs[:15]

    if request.method == "POST":
        asistente_id = request.POST.get("asistente_id")
        pases_confirmados = request.POST.get("pases_confirmados")

        asistente = get_object_or_404(Asistente, id=asistente_id, evento=evento)

        try:
            pases_confirmados = int(pases_confirmados)
        except ValueError:
            pases_confirmados = 0

        if pases_confirmados < 1:
            error = "Debe confirmar al menos 1 pase."
        elif pases_confirmados > asistente.numero_pases:
            error = f"No puede confirmar más de {asistente.numero_pases} pase(s)."
        else:
            asistente.confirmado = True
            asistente.pases_confirmados = pases_confirmados
            asistente.confirmado_en = timezone.now()
            asistente.save()

            mensaje = "Asistencia confirmada correctamente. ¡Gracias!"

    return render(request, "memories/intro.html", {
        "evento": evento,
        "asistentes": asistentes,
        "busqueda": busqueda,
        "mensaje": mensaje,
        "error": error,
    })

def _get_anon_session_id(request):
    anon_id = request.session.get("anon_id")
    if not anon_id:
        request.session["anon_id"] = timezone.now().strftime("%Y%m%d%H%M%S%f")
        request.session.modified = True
        anon_id = request.session["anon_id"]
    return anon_id

def evento_home(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)
    momentos = Momento.objects.filter(evento=evento, activo=True).order_by("orden")

    return render(request, "memories/evento_home.html", {
        "evento": evento,
        "momentos": momentos,
    })




def subir_fotos(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)

    if request.method == "POST":
        form = FotoUploadForm(request.POST, request.FILES, evento=evento)
        if form.is_valid():
            momento = form.cleaned_data["momento"]
            nombre_invitado = (form.cleaned_data.get("nombre_invitado") or "").strip()
            mensaje = (form.cleaned_data.get("mensaje") or "").strip()
            
            anon_id = _get_anon_session_id(request)
            imagenes = form.cleaned_data["imagenes"]
            for img in imagenes:
                Foto.objects.create(
                    evento=evento,
                    momento=momento,
                    imagen=img,
                    nombre_invitado=nombre_invitado,
                    mensaje=mensaje,
                    owner_session_id=anon_id,
                    visible=True,
                )

            return redirect("memories:muro", token=evento.token)
    else:
        # ✅ Preselección SOLO si viene ?momento=<id>
        initial = {}
        momento_id = request.GET.get("momento")
        if momento_id:
            try:
                initial["momento"] = Momento.objects.get(id=momento_id, evento=evento, activo=True)
            except Momento.DoesNotExist:
                pass

        form = FotoUploadForm(evento=evento, initial=initial)

    return render(request, "memories/subir_fotos.html", {
        "evento": evento,
        "form": form,
    })


def muro(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)

    momento_id = request.GET.get("momento")
    momentos = Momento.objects.filter(evento=evento, activo=True).order_by("orden")

    fotos = Foto.objects.filter(evento=evento, visible=True).select_related("momento")

    momento_seleccionado = None
    if momento_id:
        try:
            momento_seleccionado = momentos.get(id=momento_id)
            fotos = fotos.filter(momento=momento_seleccionado)
        except Momento.DoesNotExist:
            momento_seleccionado = None

    # Limitar carga inicial (mejor para 200 invitados)
    fotos = fotos.order_by("-creado_en")[:240]
    anon_id = _get_anon_session_id(request)
    limite = timezone.now() - timedelta(minutes=10)

    # Marcamos flags en cada foto (para la plantilla)
    for f in fotos:
        f.es_mia = (f.owner_session_id == anon_id) and bool(f.owner_session_id)
        f.puede_ocultar = f.es_mia and (f.creado_en >= limite)

    return render(request, "memories/muro.html", {
        "evento": evento,
        "momentos": momentos,
        "fotos": fotos,
        "momento_seleccionado": momento_seleccionado,
    })



def foto_detalle(request, token, foto_id):
    evento = get_object_or_404(Evento, token=token, activo=True)
    foto = get_object_or_404(
        Foto.objects.select_related("momento"),
        id=foto_id,
        evento=evento,
        visible=True,
    )

    momento_id = request.GET.get("momento")
    back_url = reverse("memories:muro", kwargs={"token": token})
    if momento_id:
        back_url = f"{back_url}?momento={momento_id}"

    return render(request, "memories/foto_detalle.html", {
        "evento": evento,
        "foto": foto,
        "back_url": back_url,
    })


@require_POST
def ocultar_foto(request, token, foto_id):
    evento = get_object_or_404(Evento, token=token, activo=True)
    foto = get_object_or_404(Foto, id=foto_id, evento=evento)

    # ✅ Si está logueado, puede ocultar cualquier foto
    if request.user.is_authenticated:
        foto.visible = False
        foto.save(update_fields=["visible"])

    else:
        # ✅ Si NO está logueado: solo su sesión + solo 10 min
        anon_id = _get_anon_session_id(request)
        limite = timezone.now() - timedelta(minutes=10)

        if foto.owner_session_id != anon_id:
            raise Http404("No autorizado")

        if foto.creado_en < limite:
            raise Http404("Tiempo expirado")

        foto.visible = False
        foto.save(update_fields=["visible"])

    # Volver al muro conservando filtro si viene
    momento = request.POST.get("momento")
    if momento:
        return redirect(f"{reverse('memories:muro', kwargs={'token': token})}?momento={momento}")

    return redirect("memories:muro", token=token)

@login_required
def asistentes_admin(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)

    if request.method == "POST":
        archivo = request.FILES.get("archivo_excel")

        if not archivo:
            messages.error(request, "Debe seleccionar un archivo Excel.")
            return redirect("memories:asistentes_admin", token=evento.token)

        try:
            wb = load_workbook(archivo, data_only=True)
            ws = wb.active

            creados = 0
            actualizados = 0
            omitidos = 0

            # Encabezados esperados:
            # nombres | apellidos | numero_pases | referencia
            headers = []
            for cell in ws[1]:
                headers.append(str(cell.value).strip().lower() if cell.value else "")

            def obtener(row, nombre_columna):
                try:
                    index = headers.index(nombre_columna)
                    value = row[index]
                    return str(value).strip() if value is not None else ""
                except ValueError:
                    return ""

            for row in ws.iter_rows(min_row=2, values_only=True):
                nombres = obtener(row, "nombres")
                apellidos = obtener(row, "apellidos")
                numero_pases = obtener(row, "numero_pases")
                referencia = obtener(row, "referencia")

                if not nombres or not apellidos:
                    omitidos += 1
                    continue

                try:
                    numero_pases = int(numero_pases)
                except:
                    numero_pases = 1

                if numero_pases < 1:
                    numero_pases = 1

                # Busca si ya existe el mismo asistente en este evento
                existente = Asistente.objects.filter(
                    evento=evento,
                    nombres__iexact=nombres,
                    apellidos__iexact=apellidos,
                    referencia__iexact=referencia,
                ).first()

                if existente:
                    existente.numero_pases = numero_pases
                    existente.referencia = referencia
                    existente.save()
                    actualizados += 1
                else:
                    Asistente.objects.create(
                        evento=evento,
                        nombres=nombres,
                        apellidos=apellidos,
                        numero_pases=numero_pases,
                        referencia=referencia,
                    )
                    creados += 1

            messages.success(
                request,
                f"Importación finalizada. Creados: {creados}, actualizados: {actualizados}, omitidos: {omitidos}."
            )

        except Exception as e:
            messages.error(request, f"Error al procesar el Excel: {e}")

        return redirect("memories:asistentes_admin", token=evento.token)

    asistentes = Asistente.objects.filter(evento=evento).order_by("apellidos", "nombres")

    total_asistentes = asistentes.count()
    confirmados = asistentes.filter(confirmado=True).count()
    pendientes = total_asistentes - confirmados

    total_pases = asistentes.aggregate(total=Sum("numero_pases"))["total"] or 0
    total_pases_confirmados = asistentes.aggregate(total=Sum("pases_confirmados"))["total"] or 0

    return render(request, "memories/asistentes_admin.html", {
        "evento": evento,
        "asistentes": asistentes,
        "total_asistentes": total_asistentes,
        "confirmados": confirmados,
        "pendientes": pendientes,
        "total_pases": total_pases,
        "total_pases_confirmados": total_pases_confirmados,
    })