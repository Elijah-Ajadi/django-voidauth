from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class VoidAuthProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voidauth_profile'
    )
    public_key = models.CharField(max_length=64, help_text="Ed25519 Public Key in Hex format")
    recovery_blob = models.TextField(blank=True, null=True, help_text="Encrypted private key for recovery")
    is_void_secured = models.BooleanField(default=False)
    vetting_period_end = models.DateTimeField(blank=True, null=True)
    
    # WebAuthn User ID (64 bytes opaque id)
    webauthn_user_handle = models.BinaryField(
        unique=True, 
        null=True, 
        blank=True,
        help_text="Opaque 64-byte ID for WebAuthn"
    )

    def is_in_vetting_period(self):
        if not self.vetting_period_end:
            return False
        return timezone.now() < self.vetting_period_end

    def start_vetting_period(self):
        self.vetting_period_end = timezone.now() + timedelta(hours=72)
        self.save()

    def __str__(self):
        return f"VoidAuthProfile for {self.user.username}"


class WebAuthnCredential(models.Model):
    """Stores multiple WebAuthn credentials per user."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webauthn_credentials'
    )
    name = models.CharField(max_length=255, default="Default Device", help_text="User-friendly name for the device")
    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} for {self.user.username}"


class VoidAuthSession(models.Model):
    """Tracks used challenges to prevent replay attacks."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voidauth_sessions'
    )
    challenge = models.CharField(max_length=128, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Session {self.challenge[:8]} for {self.user.username}"
