import secrets
import binascii
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import VoidAuthProfile, WorkstationSession
from .conf import voidauth_settings
from django.contrib.auth.mixins import LoginRequiredMixin

class ChallengeView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'status': 'error', 'error': 'Username required'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'error': 'User not found'}, status=404)

        # Generate a 32-byte cryptographically secure random nonce
        challenge = secrets.token_hex(32)
        
        # Store in cache for 60 seconds (default)
        cache_key = f"voidauth_challenge_{username}"
        cache.set(cache_key, challenge, timeout=voidauth_settings.CHALLENGE_TTL)

        return JsonResponse({'status': 'success', 'challenge': challenge})

@method_decorator(csrf_exempt, name='dispatch') # For demo/DRF compatibility, adjust as needed
class LoginView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'voidauth/login.html')

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        challenge = request.POST.get('challenge')
        signature = request.POST.get('signature')

        if not all([username, challenge, signature]):
            return JsonResponse({'error': 'Missing credentials'}, status=400)

        user = authenticate(request, username=username, challenge=challenge, signature=signature)

        if user:
            login(request, user, backend='voidauth.backend.VoidAuthBackend')
            return JsonResponse({'status': 'success', 'message': 'Logged in'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid signature or challenge'}, status=401)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'voidauth/signup.html')

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        email = request.POST.get('email')
        public_key = request.POST.get('public_key')
        recovery_blob = request.POST.get('recovery_blob')

        if not all([username, email, public_key, recovery_blob]):
            return JsonResponse({'error': 'Missing registration data'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'User already exists'}, status=400)

        user = User.objects.create_user(username=username, email=email)
        VoidAuthProfile.objects.create(
            user=user,
            public_key=public_key,
            recovery_blob=recovery_blob,
            is_void_secured=True
        )
        
        # Log the user in after registration for immediate access to dashboard/relay
        login(request, user, backend='voidauth.backend.VoidAuthBackend')

        return JsonResponse({'status': 'success', 'message': 'User registered'})

@method_decorator(csrf_exempt, name='dispatch')
class RecoveryBlobView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'error': 'Username required'}, status=400)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(username=username)
            profile = user.voidauth_profile
            return JsonResponse({
                'status': 'success', 
                'recovery_blob': profile.recovery_blob
            })
        except (User.DoesNotExist, Exception):
            return JsonResponse({'error': 'Recovery data not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class QRChallengeView(View):
    def post(self, request, *args, **kwargs):
        session_id = secrets.token_hex(16)
        challenge = secrets.token_hex(32)
        expires_at = timezone.now() + timedelta(minutes=5)
        
        WorkstationSession.objects.create(
            session_id=session_id,
            challenge=challenge,
            expires_at=expires_at
        )
        
        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'challenge': challenge
        })

@method_decorator(csrf_exempt, name='dispatch')
class QRRelayView(View):
    def post(self, request, *args, **kwargs):
        session_id = request.POST.get('session_id')
        username = request.POST.get('username')
        signature = request.POST.get('signature')
        challenge = request.POST.get('challenge')

        if not all([session_id, username, signature, challenge]):
            return JsonResponse({'error': 'Missing relay data'}, status=400)

        try:
            ws_session = WorkstationSession.objects.get(session_id=session_id, status='pending')
            if ws_session.is_expired():
                ws_session.status = 'expired'
                ws_session.save()
                return JsonResponse({'error': 'Session expired'}, status=410)
            
            if ws_session.challenge != challenge:
                return JsonResponse({'error': 'Challenge mismatch'}, status=400)

            # Authenticate using the relay proof
            user = authenticate(request, username=username, signature=signature, challenge=challenge)
            
            if user:
                ws_session.user = user
                ws_session.status = 'authorized'
                ws_session.save()
                return JsonResponse({'status': 'success', 'message': 'Workstation authorized'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid proof'}, status=401)
                
        except WorkstationSession.DoesNotExist:
            return JsonResponse({'error': 'Invalid session'}, status=404)

class SessionStatusView(View):
    def get(self, request, *args, **kwargs):
        session_id = request.GET.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'Session ID required'}, status=400)

        try:
            ws_session = WorkstationSession.objects.get(session_id=session_id)
            
            if ws_session.status == 'authorized':
                # Log the user in on this workstation (if the status check is from the workstation)
                if ws_session.user:
                    login(request, ws_session.user, backend='voidauth.backend.VoidAuthBackend')
                    return JsonResponse({'status': 'authorized', 'username': ws_session.user.username})
            
            return JsonResponse({'status': ws_session.status})
        except WorkstationSession.DoesNotExist:
            return JsonResponse({'error': 'Invalid session'}, status=404)

class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return render(request, 'voidauth/dashboard.html')

class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return JsonResponse({'status': 'success', 'message': 'Logged out'})

class RelayView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return render(request, 'voidauth/relay.html')
