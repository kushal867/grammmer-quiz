from django.db import models

# Create your models here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm

def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')  
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  
        else:
            form.add_error(None, "Invalid username or password")

    return render(request, "login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect('user:login')