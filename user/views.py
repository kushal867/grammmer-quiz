# user/views.py
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from .forms import LoginForm

logger = logging.getLogger(__name__)
User = get_user_model()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@sensitive_post_parameters()
@csrf_protect
@never_cache
def user_login(request):
    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = LoginForm(request.POST or None)
    login_attempts = int(request.session.get('login_attempts', 0))
    ip_address = get_client_ip(request)
    
    if request.method == 'POST':
        if form.is_valid():
            # Check for too many login attempts
            max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
            if login_attempts >= max_attempts:
                logger.warning(
                    f"Too many login attempts from IP: {ip_address} for user: {form.cleaned_data.get('username')}"
                )
                messages.error(
                    request,
                    'Too many failed login attempts. Please try again later or reset your password.'
                )
                return render(request, "login.html", {"form": form})
            
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', False)
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Reset login attempts on successful login
                    request.session['login_attempts'] = 0
                    
                    # Set session expiry
                    if not remember_me:
                        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                    else:
                        request.session.set_expiry(settings.SESSION_COOKIE_AGE_REMEMBER_ME)
                    
                    # Log successful login
                    logger.info(f"Successful login for user: {username} from IP: {ip_address}")
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    
                    login(request, user)
                    next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
                    return redirect(next_url)
                else:
                    messages.error(request, 'This account is inactive.')
            else:
                # Increment failed login attempts
                login_attempts += 1
                request.session['login_attempts'] = login_attempts
                logger.warning(
                    f"Failed login attempt {login_attempts} for user: {username} from IP: {ip_address}"
                )
                
                # Show appropriate error message
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Invalid password. Please try again.')
                else:
                    messages.error(request, 'No account found with this username.')
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

    return render(request, "login.html", {
        "form": form,
        "login_attempts": login_attempts,
        "max_attempts": getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
    })

@never_cache
def user_logout(request):
    if request.user.is_authenticated:
        logger.info(f"User {request.user.username} logged out")
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
    return redirect(settings.LOGOUT_REDIRECT_URL)