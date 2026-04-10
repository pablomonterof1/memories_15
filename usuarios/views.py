from django.shortcuts import redirect, render
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, logout, login
from django.utils.http import url_has_allowed_host_and_scheme


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "GET":
        form = AuthenticationForm()
        return render(request, "login.html", {"form": form, "next": next_url})

    # POST
    username = request.POST.get("username")
    password = request.POST.get("password")
    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, "login.html", {
            "form": AuthenticationForm(),
            "error": "Usuario y contraseña incorrectos",
            "next": next_url
        })

    login(request, user)

    # ✅ Redirigir seguro a next si existe
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)

    # ✅ Si no hay next, manda a un lugar por defecto (elige uno)
    return redirect("memories:evento_home", token="ytzel15-2026")


def logout_view(request):
    next_url = request.GET.get("next")

    logout(request)

    # Si viene next y es seguro
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)

    # Redirección por defecto (evento principal)
    return redirect("memories:evento_home", token="ytzel15-2026")