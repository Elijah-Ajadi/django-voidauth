import binascii
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from voidauth.models import VoidAuthProfile
from voidauth.backend import VoidAuthBackend
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class VoidAuthBackendTests(TestCase):
    def setUp(self):
        self.backend = VoidAuthBackend()
        
        # Generate a keypair
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        # Public key to hex
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        self.public_key_hex = binascii.hexlify(public_bytes).decode('utf-8')
        
        # Create user and profile
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.profile = VoidAuthProfile.objects.create(
            user=self.user,
            public_key=self.public_key_hex,
            recovery_blob='{}',
            is_void_secured=True
        )

    def test_authenticate_success(self):
        challenge = 'a_secure_random_challenge_string'
        cache.set(f"voidauth_challenge_{self.user.username}", challenge, 60)
        
        challenge_bytes = challenge.encode('utf-8')
        signature_bytes = self.private_key.sign(challenge_bytes)
        signature_hex = binascii.hexlify(signature_bytes).decode('utf-8')
        
        authenticated_user = self.backend.authenticate(
            request=None, 
            username=self.user.username, 
            signature=signature_hex, 
            challenge=challenge
        )
        
        self.assertEqual(authenticated_user, self.user)

    def test_authenticate_invalid_challenge(self):
        challenge = 'a_secure_random_challenge_string'
        cache.set(f"voidauth_challenge_{self.user.username}", challenge, 60)
        
        wrong_challenge = 'wrong_challenge'
        challenge_bytes = wrong_challenge.encode('utf-8')
        signature_bytes = self.private_key.sign(challenge_bytes)
        signature_hex = binascii.hexlify(signature_bytes).decode('utf-8')
        
        authenticated_user = self.backend.authenticate(
            request=None, 
            username=self.user.username, 
            signature=signature_hex, 
            challenge=wrong_challenge
        )
        
        self.assertIsNone(authenticated_user)

    def test_authenticate_invalid_signature(self):
        challenge = 'a_secure_random_challenge_string'
        cache.set(f"voidauth_challenge_{self.user.username}", challenge, 60)
        
        wrong_private_key = ed25519.Ed25519PrivateKey.generate()
        challenge_bytes = challenge.encode('utf-8')
        signature_bytes = wrong_private_key.sign(challenge_bytes)
        signature_hex = binascii.hexlify(signature_bytes).decode('utf-8')
        
        authenticated_user = self.backend.authenticate(
            request=None, 
            username=self.user.username, 
            signature=signature_hex, 
            challenge=challenge
        )
        
        self.assertIsNone(authenticated_user)
