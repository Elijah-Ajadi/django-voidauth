import os
import json
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.template.loader import get_template

class Command(BaseCommand):
    help = "🌌 Void Architect: AI-powered project integration assistant."

    def add_arguments(self, parser):
        parser.add_argument('--auto', action='store_true', help='Automatically apply suggested changes.')
        parser.add_argument('--guide', action='store_true', default=True, help='Print a step-by-step integration guide.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🌌 VOID ARCHITECT: INITIALIZING SCAN..."))
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise CommandError("GEMINI_API_KEY not found in environment. Please export it first.")

        try:
            from google import genai
        except ImportError:
            raise CommandError("google-genai library not found. Run 'pip install google-genai' first.")

        # 1. Project Scan
        context = self.scan_project()
        
        # 2. AI Assessment
        self.stdout.write("🧠 Consulting the Void (AI Analysis)...")
        plan = self.get_ai_plan(api_key, context)
        
        if options.get('auto'):
            self.execute_auto_flow(plan)
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
                context['settings'] = settings_path.read_text()
                context['settings_path'] = str(settings_path)

        url_conf = getattr(settings, 'ROOT_URLCONF', None)
        if url_conf:
            url_rel_path = Path(url_conf.replace('.', '/') + '.py')
            url_path = base_dir / url_rel_path
            if url_path.exists():
                self.stdout.write(f"🔍 Analyzing Root URLs: {self.style.NOTICE(url_path)}")
                context['urls'] = url_path.read_text()
                context['urls_path'] = str(url_path)

        # 2. Local App Scanning (Models & Views)
        local_apps = [app for app in settings.INSTALLED_APPS if not app.startswith('django.') and '.' not in app]
        for app_name in local_apps:
            app_path = base_dir / app_name
            if app_path.is_dir():
                app_context = {}
                for filename in ['models.py', 'views.py', 'urls.py']:
                    file_path = app_path / filename
                    if file_path.exists():
                        self.stdout.write(f"🔍 Analyzing App Node: {self.style.NOTICE(f'{app_name}/{filename}')}")
                        app_context[filename] = file_path.read_text()
                if app_context:
                    context['apps'][app_name] = app_context

        # 3. Template Discovery (Searching for login/register)
        template_dirs = []
        if hasattr(settings, 'TEMPLATES'):
            for t in settings.TEMPLATES:
                template_dirs.extend(t.get('DIRS', []))
        
        context['existing_templates'] = {}
        search_patterns = ['*login*', '*register*', '*signup*', 'base.html']
        
        for t_dir in template_dirs:
            t_path = Path(t_dir)
            if not t_path.is_absolute():
                t_path = base_dir / t_path
            
            if t_path.exists():
                for pattern in search_patterns:
                    for found in t_path.rglob(pattern):
                        if found.is_file() and found.suffix == '.html':
                            rel_name = found.relative_to(t_path)
                            self.stdout.write(f"🔍 Analyzing Template: {self.style.NOTICE(rel_name)}")
                            context['existing_templates'][str(rel_name)] = found.read_text()

        return context

    def get_ai_plan(self, api_key, context):
        """Call Gemini to generate a structured integration plan."""
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Build app context string
        apps_summary = ""
        for app, files in context['apps'].items():
            apps_summary += f"\nAPP: {app}"
            for f, content in files.items():
                apps_summary += f"\n-- {f}: {content[:1000]}..." # Limit content to 1000 chars per file for efficiency

        templates_summary = ""
        for t, content in context['existing_templates'].items():
            templates_summary += f"\nTEMPLATE: {t}\n{content[:1000]}..."

        prompt = f"""
        You are the Void Architect. Integrate django-voidauth into this project.
        
        PROJECT CONTEXT:
        - Settings: {context.get('settings', 'Empty')[:2000]}
        - Root URLs: {context.get('urls', 'Empty')[:1000]}
        - Apps Metadata: {apps_summary}
        - Existing Auth Templates: {templates_summary}
        
        RULES:
        1. USE BUILT-IN TEMPLATE TAGS:
           - Load them using `{{% load voidauth_tags %}}`.
           - For signup/register, add `{{% void_recovery_modal %}}` at the end of the template.
           - For login, add `{{% void_secure_login_button redirect_url='/dashboard' %}}` (adjust redirect as needed).
        2. JS INTEGRATION:
           - Intercept the registration form submit.
           - Identify the fields for `username`, `email`, and `password` (e.g. check for `password1` vs `password`).
           - Call `await VoidAuth.register(username, email, password)`.
           - If successful, call `window.showVoidRecovery(result.mnemonic, '/login/')` instead of a direct redirect.
        3. DO NOT OVERWRITE: Append a script block or inclusion tag at the end of the existing `content` block.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "steps": ["Step 1...", "..."],
            "edits": [
                {{ 
                    "file": "path", 
                    "action": "replace | append", 
                    "target": "text_to_find_for_replace", 
                    "replacement": "new_text" 
                }}
            ],
            "new_files": [
                {{ "file": "path", "content": "content" }}
            ]
        }}
        """
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        try:
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except Exception:
            self.stdout.write(self.style.ERROR("Failed to parse AI response. Raw output:"))
            self.stdout.write(response.text)
            raise CommandError("AI response was not valid JSON.")

    def print_guide(self, plan):
        """Print the step-by-step instructions."""
        self.stdout.write(self.style.SUCCESS("\n📝 INTEGRATION GUIDE GENERATED:"))
        for i, step in enumerate(plan.get('steps', []), 1):
            self.stdout.write(f"{i}. {step}")
        
        self.stdout.write(self.style.WARNING("\nRun with --auto to apply these changes automatically (requires approval)."))

    def execute_auto_flow(self, plan):
        """Interactively apply changes."""
        self.stdout.write(self.style.WARNING("\n⚠️  VOID ARCHITECT: AUTO-PILOT ENGAGED."))
        self.stdout.write("The following changes will be applied:")
        
        for edit in plan.get('edits', []):
            self.stdout.write(f"  [MODIFY] {edit['file']}")
        for new_file in plan.get('new_files', []):
            self.stdout.write(f"  [NEW]    {new_file['file']}")

        confirm = input("\nDo you approve these changes? (y/N): ")
        if confirm.lower() != 'y':
            self.stdout.write("Operation cancelled.")
            return

        # Apply Edits
        for edit in plan.get('edits', []):
            path = Path(edit['file'])
            if path.exists():
                # Backup
                if not Path(str(path) + '.bak').exists():
                    shutil.copy(path, str(path) + '.bak')
                
                content = path.read_text()
                action = edit.get('action', 'replace')
                
                if action == 'replace' and edit.get('target'):
                    new_content = content.replace(edit['target'], edit['replacement'])
                elif action == 'append':
                    new_content = content + "\n" + edit['replacement']
                else:
                    new_content = content
                
                path.write_text(new_content)
                self.stdout.write(self.style.SUCCESS(f"  Fixed: {edit['file']}"))

        # Create New Files
        for new_file in plan.get('new_files', []):
            path = Path(new_file['file'])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_file['content'])
            self.stdout.write(self.style.SUCCESS(f"  Created: {new_file['file']}"))

        self.stdout.write(self.style.SUCCESS("\n🌌 INTEGRATION COMPLETE. Welcome to the Void."))
