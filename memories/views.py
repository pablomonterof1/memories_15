from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404
from django.urls import reverse
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Evento, Momento, Foto
from .forms import FotoUploadForm
from usuarios.views import login_view
from usuarios.urls import urlpatterns as usuarios_urlpatterns

def intro(request, token):
    evento = Evento.objects.get(token=token)
    return render(request, "memories/intro.html", {"evento": evento})

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
