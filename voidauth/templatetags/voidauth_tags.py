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

@register.inclusion_tag('voidauth/snippets/recovery_form.html')
def void_recovery_form():
    """Renders the Zero-Knowledge account recovery form."""
    return {}

@register.simple_tag
def voidauth_scripts():
    """Renders the necessary JS library includes."""
    from django.templatetags.static import static
    scripts = [
        static('voidauth/js/libsodium.js'),
        static('voidauth/js/bip39.js'),
        static('voidauth/js/voidauth.js'),
    ]
    html = "".join([f'<script src="{s}"></script>' for s in scripts])
    return mark_safe(html)
