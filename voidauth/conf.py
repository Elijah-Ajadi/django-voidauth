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

    @property
    def CHALLENGE_RATE(self):
        return getattr(settings, 'VOIDAUTH_CHALLENGE_RATE', '10/m')

    @property
    def LOGIN_RATE(self):
        return getattr(settings, 'VOIDAUTH_LOGIN_RATE', '5/m')

    @property
    def RP_ID(self):
        return getattr(settings, 'VOIDAUTH_RP_ID', 'localhost')

    @property
    def RP_NAME(self):
        return getattr(settings, 'VOIDAUTH_RP_NAME', 'VoidAuth Secure')

    @property
    def ORIGIN(self):
        return getattr(settings, 'VOIDAUTH_ORIGIN', 'http://localhost:8000')

voidauth_settings = VoidAuthSettings()
