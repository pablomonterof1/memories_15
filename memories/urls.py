from django.urls import path
from . import views

urlpatterns = [
    path("e/<slug:token>/", views.evento_home, name="evento_home"),
    path("e/<slug:token>/subir/", views.subir_fotos, name="subir_fotos"),
    path("e/<slug:token>/muro/", views.muro, name="muro"),
]