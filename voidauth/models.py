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

    def is_in_vetting_period(self):
        if not self.vetting_period_end:
            return False
        return timezone.now() < self.vetting_period_end

    def start_vetting_period(self):
        self.vetting_period_end = timezone.now() + timedelta(hours=72)
        self.save()

    def __str__(self):
        return f"VoidAuthProfile for {self.user.username}"

class WorkstationSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('voided', 'Voided'),
        ('expired', 'Expired'),
    ]

    session_id = models.CharField(max_length=64, unique=True)
    challenge = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"WorkstationSession {self.session_id} - {self.status}"
