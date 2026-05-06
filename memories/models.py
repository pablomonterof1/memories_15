from django.db import models
from django.utils import timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from django.core.files.base import ContentFile
import unicodedata


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
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="fotos")
    momento = models.ForeignKey(Momento, on_delete=models.PROTECT, related_name="fotos")

    imagen = models.ImageField(upload_to="eventos/fotos/%Y/%m/%d/")
    nombre_invitado = models.CharField(max_length=80, blank=True)
    mensaje = models.CharField(max_length=200, blank=True)

    visible = models.BooleanField(default=True)
    destacada = models.BooleanField(default=False)

    owner_session_id = models.CharField(max_length=64, blank=True, db_index=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ["-creado_en"]

    def __str__(self):
        invitado = self.nombre_invitado.strip() or "Anónimo"
        return f"{invitado} - {self.momento}"

    def save(self, *args, **kwargs):
        """
        Optimiza la imagen automáticamente:
        - corrige orientación
        - convierte a RGB
        - reduce tamaño máximo
        - guarda como JPEG comprimido
        """
        if self.imagen and not kwargs.pop("skip_optimize", False):
            try:
                self.imagen.open()
                img = Image.open(self.imagen)

                # Corrige orientación de fotos tomadas en celular
                img = ImageOps.exif_transpose(img)

                # Convierte a RGB si viene PNG, WEBP, HEIC convertido, etc.
                if img.mode in ("RGBA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Redimensiona manteniendo proporción
                max_size = (1600, 1600)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Guarda optimizada en memoria
                output = BytesIO()
                img.save(
                    output,
                    format="JPEG",
                    quality=80,
                    optimize=True,
                )
                output.seek(0)

                original_name = Path(self.imagen.name).stem
                new_name = f"{original_name}.jpg"

                self.imagen.save(new_name, ContentFile(output.read()), save=False)

            except Exception:
                # Si algo falla, guarda la imagen original sin romper el flujo
                pass

        super().save(*args, **kwargs)

def normalizar_texto(texto):
    texto = texto or ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())

class Asistente(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ASISTE = "asiste"
    ESTADO_NO_ASISTE = "no_asiste"

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_ASISTE, "Asiste"),
        (ESTADO_NO_ASISTE, "No asistira"),
    ]

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="asistentes")

    nombres = models.CharField(max_length=180)

    adultos = models.PositiveIntegerField(default=1)
    ninos = models.PositiveIntegerField(default=0)

    nombre_busqueda = models.CharField(max_length=250, blank=True, db_index=True)

    estado_confirmacion = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        db_index=True
    )

    adultos_confirmados = models.PositiveIntegerField(default=0)
    ninos_confirmados = models.PositiveIntegerField(default=0)

    confirmado_en = models.DateTimeField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asistente"
        verbose_name_plural = "Asistentes"
        ordering = ["nombres"]

    @property
    def total_pases(self):
        return self.adultos + self.ninos

    @property
    def total_confirmados(self):
        return self.adultos_confirmados + self.ninos_confirmados

    def save(self, *args, **kwargs):
        self.nombre_busqueda = normalizar_texto(self.nombres)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombres} - {self.total_pases} pase(s)"