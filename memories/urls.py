from django.urls import path
from . import views

app_name = "memories"

urlpatterns = [
    path("intro/<slug:token>/", views.intro, name="intro"),
    path("e/<slug:token>/", views.evento_home, name="evento_home"),
    path("e/<slug:token>/subir/", views.subir_fotos, name="subir_fotos"),
    path("e/<slug:token>/muro/", views.muro, name="muro"),
    path("e/<slug:token>/foto/<int:foto_id>/", views.foto_detalle, name="foto_detalle"),
    path("e/<slug:token>/foto/<int:foto_id>/ocultar/", views.ocultar_foto, name="ocultar_foto"),
]