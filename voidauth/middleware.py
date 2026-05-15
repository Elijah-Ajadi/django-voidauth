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
        
        response = self.get_response(request)

        # 1. Registration Interception Post-View
        if request.method == 'POST' and 'void_public_key' in request.POST:
            # User was just created and logged in by the standard view
            if request.user.is_authenticated:
                from .models import VoidAuthProfile
                # Ensure we don't create duplicates and only update if needed
                VoidAuthProfile.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'public_key': request.POST.get('void_public_key'),
                        'recovery_blob': request.POST.get('void_recovery_blob'),
                        'is_void_secured': True
                    }
                )
        
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):

        # 2. Prevent standard password login for Void-Secured users
        if voidauth_settings.LEGACY_OVERRIDE:
            return None

        # Only intercept Django's built-in login view on POST
        module_name = getattr(view_func, '__module__', '')
        if request.method == 'POST' and ('django.contrib.auth.views' in module_name or 'LoginView' in str(view_func)):
            username = request.POST.get('username', '')
            if not username:
                return None
                
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                if hasattr(user, 'voidauth_profile') and user.voidauth_profile.is_void_secured:
                    # Redirect to VoidAuth login
                    return redirect(reverse('voidauth:login'))
            except User.DoesNotExist:
                pass
        
        return None
