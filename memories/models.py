from django.db import models
from django.utils import timezone


class Evento(models.Model):
    """
    Evento principal (por ahora: Mis 15 de Ytzel).
    token: se usa para la URL secreta del QR.
    """
    nombre = models.CharField(max_length=120)
    fecha = models.DateField(default=timezone.now)
    token = models.SlugField(max_length=64, unique=True)  # Ej: ytzel15-9f3k2a...
    activo = models.BooleanField(default=True)

    # Portada opcional (si luego quieres una imagen principal)
    portada = models.ImageField(upload_to="eventos/portadas/", blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self):
        return self.nombre


class Momento(models.Model):
    """
    Etapas del evento: ✨ Entrada, 💃 Vals, 🎉 Hora loca, etc.
    emoji + nombre se mostrarán en el selector.
    """
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="momentos")
    orden = models.PositiveIntegerField(default=1)
    emoji = models.CharField(max_length=5, default="✨")
    nombre = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Momento"
        verbose_name_plural = "Momentos"
        unique_together = ("evento", "nombre")
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.emoji} {self.nombre}"

    @property
    def label(self):
        return f"{self.emoji} {self.nombre}"


class Foto(models.Model):
    """
    Foto subida por invitados.
    - momento es obligatorio (Opción A)
    - visible permite moderación (ocultar sin borrar)
    """
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="fotos")
    momento = models.ForeignKey(Momento, on_delete=models.PROTECT, related_name="fotos")

    imagen = models.ImageField(upload_to="eventos/fotos/%Y/%m/%d/")
    nombre_invitado = models.CharField(max_length=80, blank=True)
    mensaje = models.CharField(max_length=200, blank=True)

    visible = models.BooleanField(default=True)
    destacada = models.BooleanField(default=False)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ["-creado_en"]

    def __str__(self):
        invitado = self.nombre_invitado.strip() or "Anónimo"
        return f"{invitado} - {self.momento}"
