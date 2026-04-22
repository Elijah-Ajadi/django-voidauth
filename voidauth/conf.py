from django.conf import settings

class VoidAuthSettings:
    @property
    def LEGACY_OVERRIDE(self):
        return getattr(settings, 'VOIDAUTH_LEGACY_OVERRIDE', False)

    @property
    def CHALLENGE_TTL(self):
        return getattr(settings, 'VOIDAUTH_CHALLENGE_TTL', 60)

    @property
    def VETTING_PERIOD_HOURS(self):
        return getattr(settings, 'VOIDAUTH_VETTING_PERIOD_HOURS', 72)

voidauth_settings = VoidAuthSettings()
