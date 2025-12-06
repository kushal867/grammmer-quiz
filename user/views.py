from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import LoginForm

def user_login(request):
    # If user is already authenticated, redirect to quiz home
    if request.user.is_authenticated:
        return redirect('quiz:home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # Redirect to quiz home page
                return redirect('quiz:home')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = LoginForm()
    
    return render(request, "login.html", {"form": form})


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully')
    return redirect('user:login')