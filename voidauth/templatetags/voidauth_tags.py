from django import template
from django.utils.safestring import mark_safe
from django.templatetags.static import static

register = template.Library()

@register.simple_tag
def voidauth_scripts():
    # Load libsodium (Wasm) and our SDK
    libsodium_js = static('voidauth/js/libsodium.js')
    bip39_js = static('voidauth/js/bip39.js')
    voidauth_sdk = static('voidauth/js/voidauth.js')
    
    html = f"""
    <script src="{libsodium_js}?v=5"></script>
    <script src="{bip39_js}?v=5"></script>
    <script src="{voidauth_sdk}?v=5"></script>
    <script>
        window.addEventListener('load', async () => {{
            if (typeof sodium !== 'undefined') {{
                await sodium.ready;
                console.log('VoidAuth: Libsodium Ready');
            }}
        }});
    </script>
    """
    return mark_safe(html)
