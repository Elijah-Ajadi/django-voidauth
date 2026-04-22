from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .conf import voidauth_settings

class VoidAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We check if the user is attempting to login via standard Django views
        # and if they are Void-Secured.
        
        # This is a simplified check. In a real scenario, we might hook into 
        # the login signal or check the request path.
        
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Prevent standard password login for Void-Secured users
        # unless Legacy Override is active.
        
        if voidauth_settings.LEGACY_OVERRIDE:
            return None

        # Logic to intercept standard login attempts would go here.
        # For now, we rely on the Backend to handle the restriction if we wanted to be strict.
        
        return None
