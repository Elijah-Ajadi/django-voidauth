from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.inclusion_tag('voidauth/snippets/recovery_modal.html')
def void_recovery_modal():
    """Renders the Zero-Knowledge recovery modal (mnemonic display)."""
    return {}

@register.inclusion_tag('voidauth/snippets/secure_login_button.html')
def void_secure_login_button(redirect_url='/'):
    """Renders the 'Secure Login (Vault)' button with built-in JS handler."""
    return {'redirect_url': redirect_url}
