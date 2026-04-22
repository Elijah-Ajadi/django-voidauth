import binascii
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache
from cryptography.hazmat.primitives.asymmetric import ed25519
from .models import VoidAuthProfile
from .conf import voidauth_settings

User = get_user_model()

class VoidAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, signature=None, challenge=None, **kwargs):
        if not username or not signature or not challenge:
            return None

        try:
            user = User.objects.get(username=username)
            profile = user.voidauth_profile
        except (User.DoesNotExist, VoidAuthProfile.DoesNotExist):
            return None

        # Verify challenge exists in cache and matches
        cache_key = f"voidauth_challenge_{username}"
        stored_challenge = cache.get(cache_key)

        if not stored_challenge or stored_challenge != challenge:
            return None

        # Verify Signature
        try:
            public_key_bytes = binascii.unhexlify(profile.public_key)
            signature_bytes = binascii.unhexlify(signature)
            challenge_bytes = challenge.encode('utf-8')

            verify_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            verify_key.verify(signature_bytes, challenge_bytes)
            
            # Clean up challenge after successful use
            cache.delete(cache_key)
            
            return user
        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
