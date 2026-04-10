from django import forms
from .models import Foto, Momento


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(attrs={"multiple": True, "class": "form-control"})
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []

        single_clean = super(MultipleImageField, self).clean

        if isinstance(data, (list, tuple)):
            cleaned_files = []
            for item in data:
                cleaned_files.append(single_clean(item, initial))
            return cleaned_files

        return [single_clean(data, initial)]


class FotoUploadForm(forms.ModelForm):
    imagenes = MultipleImageField(required=True, label="Fotos")

    class Meta:
        model = Foto
        fields = ["momento", "nombre_invitado", "mensaje"]
        widgets = {
            "momento": forms.Select(attrs={"class": "form-select"}),
            "nombre_invitado": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Tu nombre (opcional)"}
            ),
            "mensaje": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Mensaje (opcional)"}
            ),
        }

    def __init__(self, *args, **kwargs):
        evento = kwargs.pop("evento", None)
        super().__init__(*args, **kwargs)

        if evento:
            self.fields["momento"].queryset = Momento.objects.filter(
                evento=evento,
                activo=True
            ).order_by("orden")

        self.fields["momento"].label_from_instance = lambda obj: obj.label
        self.fields["momento"].empty_label = "— Selecciona un momento —"

    def clean_imagenes(self):
        files = self.cleaned_data.get("imagenes", [])

        if not files:
            raise forms.ValidationError("Debes subir al menos 1 foto.")

        if len(files) > 3:
            raise forms.ValidationError("Máximo 3 fotos por envío.")

        max_size = 5 * 1024 * 1024  # 5 MB
        for f in files:
            if f.size > max_size:
                raise forms.ValidationError("Cada foto debe pesar máximo 5 MB.")

        return files