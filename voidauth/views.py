import secrets
import uuid
import base64
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
try:
    from ratelimit.decorators import ratelimit
except ImportError:
    from django_ratelimit.decorators import ratelimit
import webauthn
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
)
from webauthn.helpers import options_to_json, bytes_to_base64url
from .models import VoidAuthProfile, WebAuthnCredential
from .conf import voidauth_settings


class ChallengeView(View):
    @method_decorator(ratelimit(key='ip', rate=voidauth_settings.CHALLENGE_RATE, block=True))
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

    @method_decorator(ratelimit(key='post:username', rate=voidauth_settings.LOGIN_RATE, block=True))
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
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        try:
            profile = request.user.voidauth_profile
            return JsonResponse({
                'status': 'success',
                'recovery_blob': profile.recovery_blob
            })
        except (VoidAuthProfile.DoesNotExist, Exception):
            return JsonResponse({'error': 'Recovery data not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnRegisterChallengeView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        email = request.POST.get('email') or username  # Fallback to username if email is missing
        if not username:
            return JsonResponse({'error': 'Username required'}, status=400)

        # Generate user handle (unique 64-byte ID if not exists, or reuse)
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_exists = User.objects.filter(username=username).exists()
            
            # If user exists, they are adding a device. If not, they are registering.
            # For simplicity in this demo, let's assume we create a handle now.
            user_handle = secrets.token_bytes(32) # Standard 32 bytes for handle
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        # For local development, normalize numeric IP to 'localhost' if needed, 
        # as modern browsers (Chrome/Windows) are picky about numeric RP IDs.
        host_rp_id = request.get_host().split(':')[0]
        if host_rp_id == '127.0.0.1':
            host_rp_id = 'localhost'
            
        actual_rp_id = voidauth_settings.RP_ID if voidauth_settings.RP_ID != 'localhost' else host_rp_id

        options = webauthn.generate_registration_options(
            rp_id=actual_rp_id,
            rp_name=voidauth_settings.RP_NAME,
            user_id=user_handle,
            user_name=username,
            user_display_name=username,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # Cache the challenge and handle for verification
        cache_key = f"webauthn_reg_challenge_{username}"
        cache.set(cache_key, {
            'challenge': options.challenge,
            'user_handle': user_handle
        }, timeout=300)

        return JsonResponse(json.loads(options_to_json(options)))


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnRegisterVerifyView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        email = request.POST.get('email')
        credential_name = request.POST.get('device_name', 'Default Device')
        response_data = json.loads(request.POST.get('response'))

        cache_key = f"webauthn_reg_challenge_{username}"
        cached_data = cache.get(cache_key)
        if not cached_data:
            return JsonResponse({'error': 'Challenge expired or not found'}, status=400)

        try:
            registration_verification = webauthn.verify_registration_response(
                credential=response_data,
                expected_challenge=cached_data['challenge'],
                expected_origin=voidauth_settings.ORIGIN,
                expected_rp_id=voidauth_settings.RP_ID,
            )

            # Create or update user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})
            
            profile, _ = VoidAuthProfile.objects.get_or_create(user=user)
            profile.webauthn_user_handle = cached_data['user_handle']
            profile.is_void_secured = True
            profile.save()

            # Store the credential with resilient attribute access for different library versions
            cred_id = getattr(registration_verification, 'credential_id', None)
            pub_key = getattr(registration_verification, 'credential_public_key', None)
            
            # Fallback for older versions if needed
            if not cred_id and hasattr(registration_verification, 'id'):
                cred_id = registration_verification.id
            if not pub_key and hasattr(registration_verification, 'public_key'):
                pub_key = registration_verification.public_key

            WebAuthnCredential.objects.create(
                user=user,
                name=credential_name,
                credential_id=cred_id,
                public_key=pub_key,
                sign_count=registration_verification.sign_count
            )
            
            # Fallback logic for log - ensure it's logged to console
            print(f"[VoidAuth] Passkey registered for {username}")

            cache.delete(cache_key)
            login(request, user, backend='voidauth.backend.VoidAuthBackend')
            return JsonResponse({'status': 'success', 'message': 'Registration successful'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnLoginChallengeView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'error': 'Username required'}, status=400)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(username=username)
            credentials = user.webauthn_credentials.all()
            
            if not credentials.exists():
                return JsonResponse({'error': 'No passkeys registered'}, status=404)

            allow_credentials = [
                webauthn.helpers.structs.PublicKeyCredentialDescriptor(id=c.credential_id)
                for c in credentials
            ]

            # Dynamic RP_ID for local dev resilience
            host_rp_id = request.get_host().split(':')[0]
            if host_rp_id == '127.0.0.1':
                host_rp_id = 'localhost'
                
            actual_rp_id = voidauth_settings.RP_ID if voidauth_settings.RP_ID != 'localhost' else host_rp_id

            options = webauthn.generate_authentication_options(
                rp_id=actual_rp_id,
                allow_credentials=allow_credentials,
                user_verification=UserVerificationRequirement.PREFERRED,
            )

            cache_key = f"webauthn_auth_challenge_{username}"
            cache.set(cache_key, options.challenge, timeout=300)

            return JsonResponse(json.loads(options_to_json(options)))
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class WebAuthnLoginVerifyView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        response_data = json.loads(request.POST.get('response'))

        cache_key = f"webauthn_auth_challenge_{username}"
        expected_challenge = cache.get(cache_key)
        if not expected_challenge:
            return JsonResponse({'error': 'Challenge expired or not found'}, status=400)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(username=username)
            
            # Find the specific credential record using the ID from the response
            # Note: py_webauthn verification expects the raw credential ID
            credential_id_b64 = response_data['id']
            # We store it as binary in the DB, but verification needs bytes
            
            from webauthn.helpers import base64url_to_bytes
            credential_id_bytes = base64url_to_bytes(credential_id_b64)
            
            try:
                cred_record = WebAuthnCredential.objects.get(credential_id=credential_id_bytes, user=user)
            except WebAuthnCredential.DoesNotExist:
                return JsonResponse({'error': 'Credential not found for this user'}, status=404)

            authentication_verification = webauthn.verify_authentication_response(
                credential=response_data,
                expected_challenge=expected_challenge,
                expected_origin=voidauth_settings.ORIGIN,
                expected_rp_id=voidauth_settings.RP_ID,
                credential_public_key=cred_record.public_key,
                credential_current_sign_count=cred_record.sign_count,
            )
            
            cred_record.sign_count = authentication_verification.new_sign_count
            cred_record.last_used_at = timezone.now()
            cred_record.save()

            cache.delete(cache_key)
            login(request, user, backend='voidauth.backend.VoidAuthBackend')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class UpdateRecoveryBlobView(View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        recovery_blob = request.POST.get('recovery_blob')
        if not recovery_blob:
            return JsonResponse({'error': 'Recovery blob required'}, status=400)

        try:
            profile = request.user.voidauth_profile
            profile.recovery_blob = recovery_blob
            profile.save()
            return JsonResponse({'status': 'success', 'message': 'Recovery blob updated'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return JsonResponse({'status': 'success', 'message': 'Logged out'})
