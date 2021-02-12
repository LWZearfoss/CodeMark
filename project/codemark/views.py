from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from verify_email.email_handler import send_verification_email
from .forms import RegisterForm

def logout_view(request):
    logout(request)
    return redirect("/")

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            send_verification_email(request, form)
            return render(request, 'activation/notify.html')
    else:
        form = RegisterForm()
    context = {
        'form': form,
    }
    return render(request, "registration/register.html", context=context)

@login_required
def index_view(request):
    return render(request, 'codemark/index.html')