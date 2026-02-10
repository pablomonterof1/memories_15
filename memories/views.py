from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404
from django.urls import reverse
from django.db.models import Q

from .models import Evento, Momento, Foto
from .forms import FotoUploadForm


def evento_home(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)
    momentos = Momento.objects.filter(evento=evento, activo=True).order_by("orden")

    return render(request, "memories/evento_home.html", {
        "evento": evento,
        "momentos": momentos,
    })


# def subir_fotos(request, token):
#     evento = get_object_or_404(Evento, token=token, activo=True)

#     if request.method == "POST":
#         form = FotoUploadForm(request.POST, request.FILES, evento=evento)
#         if form.is_valid():
#             momento = form.cleaned_data["momento"]
#             nombre_invitado = (form.cleaned_data.get("nombre_invitado") or "").strip()
#             mensaje = (form.cleaned_data.get("mensaje") or "").strip()

#             # Guardar 1..3 fotos
#             imagenes = form.cleaned_data["imagenes"]
#             for img in imagenes:
#                 Foto.objects.create(
#                     evento=evento,
#                     momento=momento,
#                     imagen=img,
#                     nombre_invitado=nombre_invitado,
#                     mensaje=mensaje,
#                     visible=True,
#                 )

#             return redirect("muro", token=evento.token)
#     else:
#         form = FotoUploadForm(evento=evento)

#     return render(request, "memories/subir_fotos.html", {
#         "evento": evento,
#         "form": form,
#     })

def subir_fotos(request, token):
    evento = get_object_or_404(Evento, token=token, activo=True)

    if request.method == "POST":
        form = FotoUploadForm(request.POST, request.FILES, evento=evento)
        if form.is_valid():
            momento = form.cleaned_data["momento"]
            nombre_invitado = (form.cleaned_data.get("nombre_invitado") or "").strip()
            mensaje = (form.cleaned_data.get("mensaje") or "").strip()

            imagenes = form.cleaned_data["imagenes"]
            for img in imagenes:
                Foto.objects.create(
                    evento=evento,
                    momento=momento,
                    imagen=img,
                    nombre_invitado=nombre_invitado,
                    mensaje=mensaje,
                    visible=True,
                )

            return redirect("muro", token=evento.token)
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

    return render(request, "memories/muro.html", {
        "evento": evento,
        "momentos": momentos,
        "fotos": fotos,
        "momento_seleccionado": momento_seleccionado,
    })
