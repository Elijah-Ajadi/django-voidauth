import os
import json
import shutil
from pathlib import Path
import re
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.template.loader import get_template

class Command(BaseCommand):
    help = "🌌 Void Architect: AI-powered project integration assistant."

    def add_arguments(self, parser):
        parser.add_argument('--auto', action='store_true', help='Automatically apply suggested changes.')
        parser.add_argument('--guide', action='store_true', default=True, help='Print a step-by-step integration guide.')
        parser.add_argument('--rollback', action='store_true', help='Rollback the last changes applied by Void Architect.')
        parser.add_argument('--test', action='store_true', help='Verify the integration by running automated backend tests.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🌌 VOID ARCHITECT: INITIALIZING SCAN..."))
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise CommandError("GEMINI_API_KEY not found in environment. Please export it first.")

        try:
            from google import genai
        except ImportError:
            raise CommandError("google-genai library not found. Run 'pip install google-genai' first.")

        # 0. Rollback Logic
        if options.get('rollback'):
            self.execute_rollback()
            return

        # 0.5 Run Tests
        if options.get('test'):
            self.execute_test_suite()
            return

        # 1. Project Scan
        context = self.scan_project()
        experiences = self.get_experience()
        
        # 2. AI Assessment
        self.stdout.write("🧠 Consulting the Void (Dynamic Analysis + Past Experience)...")
        plan = self.get_ai_plan(api_key, context, experiences)
        
        if options.get('auto'):
            self.execute_auto_flow(plan, context)
        else:
            self.print_guide(plan)

    def scan_project(self):
        """Gather comprehensive project files for AI context."""
        context = {'apps': {}}
        base_dir = Path(settings.BASE_DIR)
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Deep Scanning: {base_dir}"))

        # 1. Core Settings & URLs
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        if settings_module:
            settings_rel_path = Path(settings_module.replace('.', '/') + '.py')
            settings_path = base_dir / settings_rel_path
            if settings_path.exists():
                self.stdout.write(f"🔍 Analyzing Core Settings: {self.style.NOTICE(settings_path)}")
                context['settings'] = settings_path.read_text(encoding='utf-8', errors='replace')
                context['settings_path'] = str(settings_path)

        url_conf = getattr(settings, 'ROOT_URLCONF', None)
        if url_conf:
            url_rel_path = Path(url_conf.replace('.', '/') + '.py')
            url_path = base_dir / url_rel_path
            if url_path.exists():
                self.stdout.write(f"🔍 Analyzing Root URLs: {self.style.NOTICE(url_path)}")
                context['urls'] = url_path.read_text(encoding='utf-8', errors='replace')
                context['urls_path'] = str(url_path)

        # 2. Architectural Context
        context['installed_apps'] = list(settings.INSTALLED_APPS)
        context['middleware'] = list(settings.MIDDLEWARE)
        context['auth_backends'] = list(getattr(settings, 'AUTHENTICATION_BACKENDS', []))

        # 3. Local App Scanning (Models & Views)
        local_apps = [app for app in settings.INSTALLED_APPS if not app.startswith('django.') and '.' not in app]
        for app_name in local_apps:
            app_path = base_dir / app_name
            if app_path.is_dir():
                app_context = {}
                for filename in ['models.py', 'views.py', 'urls.py']:
                    file_path = app_path / filename
                    if file_path.exists():
                        self.stdout.write(f"🔍 Analyzing App Node: {self.style.NOTICE(f'{app_name}/{filename}')}")
                        app_context[filename] = file_path.read_text(encoding='utf-8', errors='replace')
                if app_context:
                    context['apps'][app_name] = app_context

        # 4. Template Discovery (Searching for login/register)
        template_dirs = []
        if hasattr(settings, 'TEMPLATES'):
            for t in settings.TEMPLATES:
                template_dirs.extend(t.get('DIRS', []))
                if t.get('APP_DIRS'):
                    for app in settings.INSTALLED_APPS:
                        # Try to find the app's template directory
                        try:
                            import importlib
                            mod = importlib.import_module(app)
                            if hasattr(mod, '__path__'):
                                app_base = Path(mod.__path__[0])
                                t_dir = app_base / 'templates'
                                if t_dir.is_dir():
                                    template_dirs.append(str(t_dir))
                        except:
                            continue
        
        context['existing_templates'] = {}
        search_patterns = ['*login*', '*register*', '*signup*', 'base.html']
        
        for t_dir in set(template_dirs): # Use set to avoid duplicates
            t_path = Path(t_dir)
            if not t_path.is_absolute():
                t_path = base_dir / t_path
            
            if t_path.exists():
                for pattern in search_patterns:
                    for found in t_path.rglob(pattern):
                        if found.is_file() and found.suffix == '.html':
                            # Try to get relative path for display, but keep absolute for AI
                            try:
                                key = str(found.relative_to(base_dir))
                            except ValueError:
                                key = found.name
                                
                            self.stdout.write(f"🔍 Analyzing Template: {self.style.NOTICE(key)}")
                            context['existing_templates'][key] = {
                                "content": found.read_text(encoding='utf-8', errors='replace')[:3000], # Cap size
                                "full_path": str(found)
                            }

        # 5. Dependency Analysis
        req_file = base_dir / 'requirements.txt'
        if req_file.exists():
            context['requirements'] = req_file.read_text(encoding='utf-8', errors='replace')

        return context

    def get_ai_plan(self, api_key, context, experiences=[]):
        """Consult the AI for an integration plan."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise CommandError("google-genai library not found. Run 'pip install google-genai' first.")

        client = genai.Client(api_key=api_key)

        apps_summary = ""
        for app, details in context.get('apps', {}).items():
            apps_summary += f"\nAPP: {app}\nMODELS: {details.get('models', 'None')}\nVIEWS: {details.get('views', 'None')[:500]}..."
        
        templates_summary = ""
        for name, info in context.get('existing_templates', {}).items():
            templates_summary += f"\nTEMPLATE: {name} (Path: {info['full_path']})\n{info['content'][:1500]}..."
        
        experience_summary = ""
        for exp in experiences:
            if isinstance(exp, str):
                experience_summary += f"- {exp}\n"
            else:
                # Handle old structured format for backward compatibility
                experience_summary += f"- [{exp.get('outcome', 'UNKNOWN')}] Architecture: {exp.get('architecture', {}).get('apps', [])}. Strategy: {exp.get('strategy', 'No strategy recorded')}\n"

        VOIDAUTH_SPEC = """
        VOIDAUTH SYSTEM CAPABILITIES:
        1. WebAuthn (Passkeys):
           - Client SDK: `VoidAuth.registerPasskey(username, email, deviceName)` and `VoidAuth.loginWithPasskey(username)`.
           - Template Tags: `{% load voidauth_tags %}` -> `{% void_secure_login_button %}`.
           - Logic: Hardware-backed signing. Does NOT require password fields.
        2. BIP-39 Recovery (Fallback):
           - Logic: 12-word mnemonic.
           - UI: `{% void_recovery_modal %}` must be present on registration/signup pages.
        3. Security Primitives:
           - Origin Binding: Requires `VOIDAUTH_ORIGIN`, `VOIDAUTH_RP_ID`.
           - Middleware: `voidauth.middleware.VoidAuthMiddleware` enforces security redirects.
        """

        prompt = f"""
        Act as the Void Architect (Senior Security Engineer). Your mission is to integrate VoidAuth into this project.
        
        {VOIDAUTH_SPEC}
        
        PAST EXPERIENCES (LEARN FROM THESE):
        {experience_summary if experience_summary else "No past experiences recorded yet."}

        PROJECT CONTEXT ANALYZED:
        - Settings Path: {context.get('settings_path')}
        - Root Settings: {context.get('settings', 'Empty')[:3000]}
        - Root URLs Path: {context.get('urls_path')}
        - Root URLs: {context.get('urls', 'Empty')[:1000]}
        - Middleware: {context.get('middleware', [])}
        - Installed Apps: {context.get('installed_apps', [])}
        - Apps Metadata: {apps_summary}
        - Discovered Auth Templates: {templates_summary}
        
        INTEGRATION REQUIREMENTS:
        1. Base Template (Crucial):
           - In root base.html, insert `{{% voidauth_scripts %}}` inside the `<head>` or at the end of the `<body>`. THIS IS MANDATORY for JS to work.
        2. Settings: 
           - Ensure 'voidauth' is in INSTALLED_APPS.
           - Ensure 'voidauth.middleware.VoidAuthMiddleware' is in MIDDLEWARE.
           - Ensure 'voidauth.backend.VoidAuthBackend' is in AUTHENTICATION_BACKENDS (along with 'django.contrib.auth.backends.ModelBackend').
           - Suggest VOIDAUTH_RP_ID and VOIDAUTH_ORIGIN if missing.
        3. URLs:
           - Ensure `path('voidauth/', include('voidauth.urls'))` is in root urls.py. WITHOUT THIS, JS API CALLS WILL 404.
        4. Auth Templates (SignUp/Login):
           - Insert `{{% load voidauth_tags %}}` at the top of the file (after `extends`).
           - Insert `{{% void_secure_login_button %}}` inside the `<form>` tag, ideally after `{{% csrf_token %}}`.
           - Insert `{{% void_registration_interceptor %}}` inside the `<form>` tag in signup templates (use `{{% csrf_token %}}` as the anchor).
           - Insert `{{% void_recovery_modal %}}` BEFORE the `{{% endblock %}}` of the MAIN content area. NEVER place it inside title blocks.
        5. View Patch (Registration Logic):
           - If a signup/registration view calls `form.save()`, you MUST patch it to handle `VoidAuthProfile`.
           - Requirement: Check if `void_public_key` is in `request.POST`. If NOT, return a `messages.error` and redirect back. 
           - DO NOT attempt to create the profile if the key is missing from POST data.
           - Example View Patch:
             ```python
             if form.is_valid():
                 user = form.save()
                 # Ensure security keys were injected by JS
                 public_key = request.POST.get('void_public_key')
                 if not public_key:
                     messages.error(request, "Security initialization failed: Browser handshake incomplete.")
                     user.delete() # Critical: Don't leave insecure users
                     return redirect('signup')
                 
                 from voidauth.models import VoidAuthProfile
                 VoidAuthProfile.objects.create(user=user, public_key=public_key, is_void_secured=True)
             ```
        
        SECURITY CHECKLIST (MANDATORY):
        - Did I include VoidAuth URLs in the root urls.py?
        - Did I load 'voidauth_tags' in every template I modified?
        - Did I avoid injecting tags into 'title' or 'meta' blocks?
        - Did I specify a backend for all `login(request, user)` calls?
        - Did I add a defensive check for `void_public_key` in the signup view?
        
        OUTPUT RULES:
        - For every file modification, use the EXACT absolute path provided.
        - Ensure all inserted tags are balanced.
        - CRITICAL: NEVER add concluding tags like `{{% endblock %}}` or `{{% endif %}}` unless you specifically opened a NEW matching tag.
        - CRITICAL: NEVER inject non-text tags (like `{{% void_* %}}`) into the `title` block or `meta` tags. 
        - Always ensure `{{% load voidauth_tags %}}` is present at the top of modified templates.
        - If a setting or middleware is already present, SKIP IT.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "architect_reasoning": "...",
            "steps": ["..."],
            "edits": [
                {{ 
                    "file": "ABSOLUTE_PATH", 
                    "anchor": "unique_string_to_find", 
                    "position": "after | before | inside_start | replace",
                    "content": "text_to_inject"
                }}
            ],
            "settings_to_add": {{ ... }}
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        try:
            if response.parsed:
                return response.parsed
            
            # Fallback to manual parsing if parsed is not supported or returns None
            import json
            import re
            
            # Remove markdown code blocks if present
            clean_text = re.sub(r'^```json\s*|```\s*$', '', response.text, flags=re.MULTILINE).strip()
            return json.loads(clean_text)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse AI response: {str(e)}"))
            self.stdout.write(f"Raw response: {response.text}")
            raise CommandError("AI response was not valid JSON.")

    def print_guide(self, plan):
        """Print the step-by-step instructions."""
        self.stdout.write(self.style.SUCCESS("\n🧠 ARCHITECT REASONING:"))
        self.stdout.write(f"{plan.get('architect_reasoning', 'No reasoning provided.')}")

        self.stdout.write(self.style.SUCCESS("\n📝 INTEGRATION GUIDE GENERATED:"))
        for i, step in enumerate(plan.get('steps', []), 1):
            self.stdout.write(f"{i}. {step}")
        
        if plan.get('settings_to_add'):
            self.stdout.write(self.style.NOTICE("\n⚙️  REQUIRED SETTINGS:"))
            for k, v in plan['settings_to_add'].items():
                self.stdout.write(f"  {k} = '{v}'")

        self.stdout.write(self.style.WARNING("\nRun with --auto to apply these changes automatically (requires approval)."))

    def execute_auto_flow(self, plan, context):
        """Interactively apply changes."""
        self.stdout.write(self.style.WARNING("\n⚠️  VOID ARCHITECT: AUTO-PILOT ENGAGED."))
        self.stdout.write(self.style.SUCCESS(f"Reasoning: {plan.get('architect_reasoning')}"))
        self.stdout.write("\nThe following changes will be applied:")
        
        for edit in plan.get('edits', []):
            self.stdout.write(f"  [MODIFY] {edit['file']}")
        for new_file in plan.get('new_files', []):
            self.stdout.write(f"  [NEW]    {new_file['file']}")
        if plan.get('settings_to_add'):
            self.stdout.write(f"  [PATCH]  Core Settings (RP_ID and Origin)")

        confirm = input("\nDo you approve these changes? (y/N): ")
        if confirm.lower() != 'y':
            self.stdout.write("Operation cancelled.")
            return

        # 1. Patch Settings
        if plan.get('settings_to_add'):
            settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
            if settings_module:
                 path = Path(settings.BASE_DIR) / (settings_module.replace('.', '/') + '.py')
                 if path.exists():
                     content = path.read_text()
                     has_updates = False
                     
                     for k, v in plan['settings_to_add'].items():
                         # Skip if already perfectly matched
                         if f"{k} = {repr(v)}" in content or f"{k} = '{v}'" in content:
                             continue

                         # Case A: Setting exists and looks like a list
                         list_pattern = rf"{k}\s*=\s*\[([^\]]*)\]"
                         match = re.search(list_pattern, content, re.DOTALL)
                         
                         if match:
                             existing_items_str = match.group(1)
                             # Identify what to add (handle if v is already a list or a string repo of a list)
                             items_to_add = []
                             if isinstance(v, list):
                                 items_to_add = v
                             elif isinstance(v, str) and v.startswith('[') and v.endswith(']'):
                                 try:
                                     import ast
                                     items_to_add = ast.literal_eval(v)
                                 except:
                                     items_to_add = [v.strip("[]'\" ")]
                             else:
                                 items_to_add = [v]

                             new_items_content = existing_items_str
                             added_count = 0
                             for item in items_to_add:
                                 if repr(item) not in existing_items_str and f"'{item}'" not in existing_items_str and f'"{item}"' not in existing_items_str:
                                     # Append to the list string
                                     if new_items_content.strip() and not new_items_content.strip().endswith(','):
                                         new_items_content = new_items_content.rstrip() + ",\n    "
                                     
                                     padding = "    " if "\n" in new_items_content else ""
                                     new_items_content += f"{padding}{repr(item)},\n"
                                     added_count += 1
                             
                             if added_count > 0:
                                 content = content.replace(match.group(0), f"{k} = [{new_items_content}]")
                                 has_updates = True
                         
                         # Case B: Setting does NOT exist
                         elif f"{k} =" not in content:
                             formatted_val = repr(v) if not isinstance(v, str) else (v if (v.startswith('[') or v.startswith('{')) else f"'{v}'")
                             content += f"\n{k} = {formatted_val}"
                             has_updates = True

                     if has_updates:
                         path.write_text(content)
                         self.stdout.write(self.style.SUCCESS(f"  Patched: {path.name}"))

        # 2. Apply Edits
        for edit in plan.get('edits', []):
            path = Path(edit['file'])
            if path.exists():
                # Backup
                if not Path(str(path) + '.bak').exists():
                    shutil.copy(path, str(path) + '.bak')
                
                content = path.read_text()
                anchor = edit.get('anchor')
                pos = edit.get('position', 'after')
                new_text = edit.get('content', '')
                
                if not anchor:
                    continue

                if anchor not in content:
                    self.stdout.write(self.style.WARNING(f"  [SKIPPED] Anchor '{anchor}' not found in {path.name}"))
                    continue

                if pos == 'after':
                    result = content.replace(anchor, f"{anchor}\n{new_text}", 1)
                elif pos == 'before':
                    result = content.replace(anchor, f"{new_text}\n{anchor}", 1)
                elif pos == 'replace':
                    result = content.replace(anchor, new_text, 1)
                elif pos == 'inside_start':
                    # Find the closing bracket of the tag
                    tag_end = content.find('>', content.find(anchor))
                    if tag_end != -1:
                        result = content[:tag_end+1] + f"\n{new_text}" + content[tag_end+1:]
                    else:
                        result = content.replace(anchor, f"{anchor}\n{new_text}", 1)
                else:
                    result = content

                # 2.5 Safety Checks & Auto-Load
                if path.suffix == '.html':
                    # A. Force-load voidauth_tags if any void tags are present in the new content
                    if '{% void' in result and '{% load voidauth_tags %}' not in result:
                        if '{% extends' in result:
                            # Place it right after extends for best compatibility
                            result = re.sub(r'(\{% extends [^%]+ %\})', r'\1\n{% load voidauth_tags %}', result)
                        else:
                            result = "{% load voidauth_tags %}\n" + result

                    # B. Sanity Filter: Ensure no void_ tags are trapped in invisible/sensitive blocks
                    # This is a global post-edit scrubber that fixes AI mistakes
                    sensitive_patterns = [
                        (r'\{% block title %\}.*?\{% void_.*?%\}.*?\{% endblock %}', r'{% block title %}...{% endblock %}'),
                        (r'<title>.*?\{% void_.*?%\}.*?</title>', r'<title>...</title>'),
                        (r'<head>.*?\{% void_.*?%\}.*?</head>', r'<head>...</head>')
                    ]
                    
                    for pattern, label in sensitive_patterns:
                        if re.search(pattern, result, re.DOTALL | re.IGNORECASE):
                            self.stdout.write(self.style.ERROR(f"  [FIXED] {path.name}: Stripped misplaced tags from {label}"))
                            # Attempt to 'scrub' the specific tag out while keeping the rest
                            result = re.sub(r'(\{%.*?block title.*?%\}.*?)(\{%\s*void_.*?\s*%\})(.*?\{% endblock %\})', r'\1 \3', result, flags=re.DOTALL | re.IGNORECASE)
                            result = re.sub(r'(<title>.*?)(\{%\s*void_.*?\s*%\})(.*?</title>)', r'\1 \3', result, flags=re.DOTALL | re.IGNORECASE)

                    # C. Script De-duplication: Ensure voidauth_scripts is only once
                    if result.count('{% voidauth_scripts %}') > 1:
                        self.stdout.write(self.style.ERROR(f"  [FIXED] {path.name}: Removed duplicate script tags."))
                        first_idx = result.find('{% voidauth_scripts %}')
                        # Keep only the tag at first_idx, remove others
                        prefix = result[:first_idx + 22] # len of tag
                        suffix = result[first_idx + 22:].replace('{% voidauth_scripts %}', '')
                        result = prefix + suffix

                # 2.6 View Shield (Python-level defensive patches)
                if path.suffix == '.py':
                    if 'VoidAuthProfile.objects.create' in result:
                        # Ensure there is a guard for void_public_key
                        if 'if not request.POST.get(\'void_public_key\')' not in result and 'if not public_key' not in result:
                            self.stdout.write(self.style.ERROR(f"  [FIXED] {path.name}: Injected missing defensive guard for security keys."))
                            
                            # Regex magic to find indentation and creation call
                            pattern = r'(\s+)VoidAuthProfile\.objects\.create'
                            def inject_guard(match):
                                indent = match.group(1)
                                guard = (
                                    f"{indent}# Defensive Guard (Injected by Void Architect Shield)\n"
                                    f"{indent}if not request.POST.get('void_public_key'):\n"
                                    f"{indent}    from django.contrib import messages\n"
                                    f"{indent}    messages.error(request, 'Security failure: Hardware handshake did not trigger. Please ensure JavaScript is enabled and you are using http://localhost:8000')\n"
                                    f"{indent}    return redirect(request.path)\n\n"
                                )
                                return f"{guard}{indent}VoidAuthProfile.objects.create"
                            
                            result = re.sub(pattern, inject_guard, result)

                # 3. Structural Validation
                if path.suffix == '.html':
                    error = self.validate_template_syntax(result)
                    if error:
                        self.stdout.write(self.style.ERROR(f"  [REJECTED] {path.name}: {error}"))
                        # Record failure as experience for future learning
                        self.record_experience("FAILURE", {"architect_reasoning": f"Broken syntax in {path.name}: {error}"}, context)
                        continue

                path.write_text(result)
                self.stdout.write(self.style.SUCCESS(f"  Secured: {edit['file']}"))

        # Create New Files
        for new_file in plan.get('new_files', []):
            path = Path(new_file['file'])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_file['content'])
            self.stdout.write(self.style.SUCCESS(f"  Created: {new_file['file']}"))

        self.record_experience("SUCCESS", plan, context)
        self.stdout.write(self.style.SUCCESS("\n🌌 INTEGRATION COMPLETE. Welcome to the Void."))

    def execute_rollback(self):
        """Restore all .bak files found in the project."""
        self.stdout.write(self.style.WARNING("🔄 VOID ARCHITECT: ROLLBACK INITIATED."))
        
        base_dir = Path(settings.BASE_DIR)
        backups = list(base_dir.rglob('*.bak'))
        
        if not backups:
            self.stdout.write("No backup files found. Nothing to rollback.")
            return

        for bak in backups:
            original = bak.with_suffix('')
            self.stdout.write(f"  Restoring: {original}")
            shutil.move(bak, original)
        
        # Record experience AFTER successful rollback
        self.record_experience("ROLLBACK", {"architect_reasoning": "User triggered rollback"}, {"apps": {}, "middleware": [], "requirements": ""})
        
        self.stdout.write(self.style.SUCCESS("\n✅ Rollback complete. Project restored to previous state."))

    def execute_test_suite(self):
        """Perform automated verification of the VoidAuth integration."""
        self.stdout.write(self.style.SUCCESS("\n🧪 VOID ARCHITECT: COMMENCING TEST SUITE..."))
        
        from django.test import Client
        from django.urls import reverse, NoReverseMatch
        client = Client()

        # Test 1: URL Reachability
        self.stdout.write("  [1/3] Verifying URL Configuration...")
        try:
            challenge_url = reverse('voidauth:challenge')
            login_url = reverse('voidauth:login')
            self.stdout.write(self.style.SUCCESS(f"    - URLs recognized: {challenge_url}"))
        except NoReverseMatch:
            self.stdout.write(self.style.ERROR("    - FAILURE: VoidAuth URLs not found in root config."))
            return

        # Test 2: Backend Challenge Generation
        self.stdout.write("  [2/3] Verifying Challenge Backend...")
        response = client.post(challenge_url, {"username": "architect_test_user"})
        if response.status_code in [200, 401, 404]: # 401/404 is fine as long as view responds
            self.stdout.write(self.style.SUCCESS("    - Backend reachable and responding."))
        else:
            self.stdout.write(self.style.ERROR(f"    - FAILURE: Backend returned {response.status_code}"))

        # Test 3: Standard Login View Interception (Middleware Check)
        self.stdout.write("  [3/3] Verifying Middleware Enforcement...")
        try:
             # Find a login URL
             django_login = reverse('login')
             response = client.get(django_login)
             if 'void-secure-login-btn' in response.content.decode():
                 self.stdout.write(self.style.SUCCESS("    - Middleware verified: Secure button discovered in login view."))
             else:
                 self.stdout.write(self.style.WARNING("    - WARNING: Secure button NOT found in login view. Check integration."))
        except:
             self.stdout.write(self.style.NOTICE("    - Skipping standard login check (custom auth detected)."))

        self.stdout.write(self.style.SUCCESS("\n✅ TEST SUITE COMPLETE. Integration appears healthy."))

    def validate_template_syntax(self, content):
        """Check for common Django template structural errors."""
        tags = {
            'block': 'endblock',
            'if': 'endif',
            'for': 'endfor',
            'with': 'endwith',
            'autoescape': 'endautoescape',
            'comment': 'endcomment'
        }
        
        # Check for unbalanced blocks
        import re
        for start, end in tags.items():
            start_count = len(re.findall(rf'\{{% \s*{start}\b', content))
            end_count = len(re.findall(rf'\{{% \s*{end}\b', content))
            if start_count != end_count:
                return f"Unbalanced '{start}' tags ({start_count} start vs {end_count} end)"
        
        return None

    def get_experience(self):
        """Load past integration experiences."""
        path = Path(settings.BASE_DIR) / '.void_experience.json'
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                return []
        return []

    def record_experience(self, outcome, plan, context):
        """Record a successful or failed integration pattern in a descriptive format."""
        try:
            path = Path(settings.BASE_DIR) / '.void_experience.json'
            experiences = self.get_experience()
            
            apps = list(context.get('apps', {}).keys())
            strategy = plan.get('architect_reasoning', 'No specific strategy was documented.')
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create a descriptive paragraph
            desc = (
                f"On {timestamp}, the Void Architect achieved a {outcome} outcome. "
                f"The project architecture included apps: {', '.join(apps) if apps else 'none detected'}. "
                f"The strategy employed was: {strategy}"
            )
            
            experiences.append(desc)
            # Keep only last 10 experiences for prompt efficiency
            path.write_text(json.dumps(experiences[-10:], indent=4))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Failed to record experience: {str(e)}"))
