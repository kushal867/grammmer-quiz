# user/middleware.py
import logging
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.urls import resolve

logger = logging.getLogger(__name__)

class LoginAttemptMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Only process login attempts
        if resolve(request.path_info).url_name == 'login' and request.method == 'POST':
            ip = self.get_client_ip(request)
            cache_key = f'login_attempts_{ip}'
            
            # Get current attempts
            attempts = cache.get(cache_key, 0)
            max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
            
            if attempts >= max_attempts:
                logger.warning(f"Blocked login attempt from IP: {ip} - Too many attempts")
                return HttpResponseForbidden(
                    "Too many login attempts. Please try again later."
                )
            
            # If login was unsuccessful, increment the counter
            if not request.user.is_authenticated and request.method == 'POST':
                cache.set(cache_key, attempts + 1, 3600)  # Block for 1 hour
                request.session['login_attempts'] = attempts + 1
            else:
                # Reset counter on successful login
                if cache_key in cache:
                    cache.delete(cache_key)
                if 'login_attempts' in request.session:
                    del request.session['login_attempts']

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip