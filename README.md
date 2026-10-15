# Hireationship — Django edition

A Python/Django port of the original Hireationship hackathon app. The HTML, CSS and browser-side swipe JavaScript are retained; the server, eligibility algorithm, demo profile extraction, demo application pack and Claude API calls now run in Python.

## Local setup (no Node.js)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver
```

On Windows activate with `.venv\Scripts\activate` instead. Open http://127.0.0.1:8000. The application starts in **demo mode** without an Anthropic key. To enable Claude, set `ANTHROPIC_API_KEY` and a valid `ANTHROPIC_MODEL` in `.env`.

## PythonAnywhere deployment

1. Upload this project or clone your new Django repository in a PythonAnywhere Bash console.
2. Create a virtual environment and `pip install -r requirements.txt`.
3. Create a **Manual configuration** Python web app in the PythonAnywhere Web tab and choose the supported Python version.
4. Set its source directory and virtualenv path. In the WSGI configuration file, set `DJANGO_SETTINGS_MODULE=config.settings`, add the project directory to `sys.path`, and import `application` from `config.wsgi`.
5. In the Web tab, configure static files: URL `/static/` → `<project>/static/` (or run `collectstatic` and point it to `staticfiles`).
6. Set `DJANGO_SECRET_KEY` to a long random secret, `DJANGO_DEBUG=0`, and `DJANGO_ALLOWED_HOSTS=yourusername.pythonanywhere.com`. Set these as environment variables, or put them in a private `.env` in the project root. The WSGI file must load `.env` if using that option.
7. Reload the web app and open your PythonAnywhere URL.

**Note:** Anthropic API access from PythonAnywhere depends on your account's outbound network restrictions; demo mode works without outbound API calls. Free plans may not permit external Anthropic API access. Check the provider's current restrictions.

## Security and limitations

- API POST requests use Django CSRF protection; the frontend sends the CSRF cookie.
- Do not commit `.env`, API keys, or real CVs. Profile data is processed in memory by the server and may be stored locally in the browser by the existing frontend.
- The sample jobs are **fictional**, and their closing dates are generated relative to the current date; this is not a live job board.
- The demo CV extraction and writing are rule-based; AI mode uses the Anthropic API.
- Verify eligibility, sponsorship, and job deadlines against official job listings before applying.
- For production, add rate limits, privacy notices, and appropriate CV data handling.
