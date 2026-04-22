from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from voidauth.models import VoidAuthProfile

class VettingPeriodTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='vettinguser')
        self.profile = VoidAuthProfile.objects.create(
            user=self.user,
            public_key='dummy_pub_key',
            is_void_secured=True
        )

    def test_initial_vetting_status(self):
        self.assertFalse(self.profile.is_in_vetting_period())

    def test_start_vetting_period(self):
        self.profile.start_vetting_period()
        self.assertTrue(self.profile.is_in_vetting_period())
        
        # Verify it's set to approximately 72 hours from now
        expected_end = timezone.now() + timedelta(hours=72)
        diff = abs((self.profile.vetting_period_end - expected_end).total_seconds())
        self.assertLess(diff, 5) # Should be within 5 seconds

    def test_expired_vetting_period(self):
        self.profile.vetting_period_end = timezone.now() - timedelta(minutes=1)
        self.profile.save()
        self.assertFalse(self.profile.is_in_vetting_period())
