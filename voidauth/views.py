import secrets
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import VoidAuthProfile
from .conf import voidauth_settings


class ChallengeView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'status': 'error', 'error': 'Username required'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'error': 'User not found'}, status=404)

        challenge = secrets.token_hex(32)
        cache_key = f"voidauth_challenge_{username}"
        cache.set(cache_key, challenge, timeout=voidauth_settings.CHALLENGE_TTL)

        return JsonResponse({'status': 'success', 'challenge': challenge})


@method_decorator(csrf_exempt, name='dispatch')
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


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return JsonResponse({'status': 'success', 'message': 'Logged out'})
