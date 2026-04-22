# VoidAuth Documentation Website

The official landing page and documentation for `django-voidauth`.

## Tech Stack
- **Structure**: Semantic HTML5
- **Logic**: Vanilla JavaScript (ES6+)
- **Styling**: Custom CSS (Glassmorphism, Dynamic Bloom, Modern Typography)
- **Icons**: SVG-based system
- **Performance**: Zero build step, instant load times

## Local Development
Since this is a pure static site, you can serve it with any HTTP server:

```bash
cd docs
python3 -m http.server
```

## Deployment on Vercel
This project is pre-configured for Vercel deployment.

1. **GitHub Import**: Connect this repository to Vercel.
2. **Configuration**: Vercel will use the root `vercel.json` to automatically route requests to the `docs` directory.
3. **Manual Deployment**: Alternatively, use the Vercel CLI:
   ```bash
   npx vercel ./docs --prod
   ```
