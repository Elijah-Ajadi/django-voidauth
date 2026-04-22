import json
import binascii
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from voidauth.models import VoidAuthProfile
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class VoidAuthViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Generate a keypair
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        self.public_key_hex = binascii.hexlify(public_bytes).decode('utf-8')
        
    def test_challenge_generation(self):
        # Should fail for non-existent user
        response = self.client.post(reverse('voidauth:challenge'), {'username': 'nobody'})
        self.assertEqual(response.json()['status'], 'error')
        
        # Create user
        User.objects.create_user(username='testuser')
        VoidAuthProfile.objects.create(
            user=User.objects.get(username='testuser'),
            public_key=self.public_key_hex,
            is_void_secured=True
        )
        
        # Should succeed for existing user
        response = self.client.post(reverse('voidauth:challenge'), {'username': 'testuser'})
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue('challenge' in data)

    def test_registration(self):
        response = self.client.post(reverse('voidauth:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'public_key': self.public_key_hex,
            'recovery_blob': '{"some": "data"}'
        })
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Verify user was created
        user = User.objects.get(username='newuser')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newuser@example.com')
        
        # Verify profile
        profile = VoidAuthProfile.objects.get(user=user)
        self.assertEqual(profile.public_key, self.public_key_hex)
        self.assertTrue(profile.is_void_secured)

    def test_login_flow(self):
        user = User.objects.create_user(username='testuser')
        VoidAuthProfile.objects.create(
            user=user,
            public_key=self.public_key_hex,
            is_void_secured=True
        )
        
        # 1. Get challenge
        response = self.client.post(reverse('voidauth:challenge'), {'username': 'testuser'})
        challenge = response.json()['challenge']
        
        # 2. Sign challenge
        challenge_bytes = challenge.encode('utf-8')
        signature_bytes = self.private_key.sign(challenge_bytes)
        signature_hex = binascii.hexlify(signature_bytes).decode('utf-8')
        
        # 3. Login
        login_response = self.client.post(reverse('voidauth:login'), {
            'username': 'testuser',
            'challenge': challenge,
            'signature': signature_hex
        })
        
        self.assertEqual(login_response.json()['status'], 'success')
        
        # Check if user is actually authenticated
        # Note: the test client automatically sets the session if login succeeds.
        # But our view returns JSON. Let's check session.
        self.assertTrue('_auth_user_id' in self.client.session)
