# Hireationship 💌

*Tired of being ghosted? Match with employers ready to commit.*

Hireationship is a swipe-based graduate job discovery and application assistant. Instead of making students sift through hundreds of vacancies, it starts with their CV, checks their eligibility, explains the fit, and helps draft tailored applications for the roles they like.

Built for the **Better Student Life** hackathon track.

**Public website:** [Visit Hireationship](https://itkara.pythonanywhere.com/) — anyone can open the site and its sign-in page; registration is open; sign-in protects each account’s private workspace.

**New users and hackathon judges:** use `/register/` to create a free account; existing invitation URLs also lead to registration.

**Because you should have hire standards.**

## What it does

### 1. Build your profile
- Upload a **PDF or Word (.docx) CV**, or paste CV text.
- Extract structured experience and skills, then review and edit your profile.
- Add graduation year, degree subject, predicted classification, right-to-work details, interests and links.
- The original uploaded file is processed for text extraction, not intentionally retained as a stored upload.

### 2. Discover jobs that fit
- Switch between **live UK vacancies from Adzuna** (when API credentials are configured) and an **illustrative demo deck**.
- Eligibility and matching rules check graduation stage, academic requirements, subject, skills and other available criteria.
- See **eligible** assessments, **reach / target / safe** labels, estimated competitiveness, and reasons for a match.
- Only roles with all mandatory criteria and required skills satisfied are shown; missing or unverified information should still be checked against the employer's original advert.
- On unrestricted hosting, each live search automatically checks the first five adverts needing review, using two concurrent readers; **Check next 5 full adverts** continues in small batches. Cards update as checks finish. Public page text is cached for six hours in the server cache, and failed reads for ten minutes. Cached text does not use another live-search attempt; eligibility is recalculated for the current profile. CVs, keys and eligibility decisions are not stored in the shared advert cache.
- PythonAnywhere free accounts restrict external job websites. The app detects its restricted outbound proxy and disables unavailable automatic reads before charging search attempts. Live cards then offer **Paste full advert to check**. This host limitation does not affect Adzuna search, demo matching or checking pasted descriptions. Administrators can set `HIREATIONSHIP_FULL_ADVERT_FETCH_ENABLED=0` to disable fetching explicitly, or `1` when using suitable hosting.
- Live cards offer **Read & check full advert** to fetch structured job data or visible advert text from the original public HTTPS link. Each fetch consumes one live-search attempt, never a pack generation. Sites requiring JavaScript or blocking access offer a paste-description fallback; pasted checks do not use live-search attempts. Extracted text is checked with local rules by default or optional Claude. A successful fetch does not guarantee eligibility.
- Paste a job description to add a role to your deck.
- Swipe left to pass, or swipe right to save for free; draft later from Applications; passed roles are retained in your private history and can be revisited.

### 3. Generate a tailored application pack
For each generated application, Hireationship prepares:
- A tailored **CV** grounded in the experience you actually provided.
- A **cover letter** where relevant.
- A **supporting-document checklist**.
- A **gap-closing plan** for missing requirements.
- A **trace** to help check claims against the source CV.

Claude powers AI-assisted reading and writing when an Anthropic key is configured. Without one, the app uses rule-based/template alternatives. **Review everything before submitting**: AI output and eligibility estimates are not guarantees.

### 4. Edit, export and track
- Edit application documents in the app.
- Copy content, download a Markdown pack, and **export formatted PDFs**.
- Keep application status and documents in an **Applications tracker**, ordered by deadline where dates are available.
- Return to saved applications later, even from another browser after signing into the same account.

### 5. Private accounts and open registration
- Anyone can create a free account at `/register/`; no invitation or paid API key is required.
- Sign-in is still required for CVs, private workspaces, saved roles and drafts.
- Each account can make 30 live-search attempts per day by default, configurable with `HIREATIONSHIP_DAILY_JOB_SEARCH_LIMIT`. Attempts that fail upstream also count. Demo matching does not use this allowance.
- Existing invitation and judge URLs continue to open registration; invitation records are retained for compatibility but no longer gate access.
- Privacy controls allow users to delete workspace data; account credentials and hosting backups are separate.

Demo roles are designed for the example student CV or a similar profile; other CVs may have no eligible matches.

### 6. Daily generation allowances
- Each free user has a **daily application-generation allowance**, configurable by the project administrator (default: **4**).
- The **Applications** page displays the remaining allowance; it updates when an application is generated.
- Users are warned before using their last generation; further generations are blocked at zero until the next calendar day in the server's configured timezone.
- **Regeneration and failed attempts also count**; simply viewing, editing or downloading existing documents does not.
- A separate optional daily limit applies to Claude-backed requests. **Paid plans are not implemented.**

## Try the preview

Visit **https://itkara.pythonanywhere.com** and sign in with an existing account, or create a free account at `/register/`.

For judge invitations, deployment and the access-request email templates, see **[JUDGES_ACCESS.md](JUDGES_ACCESS.md)** (added in PR #11). Each invite can be redeemed once; never publish real invitation tokens in the repository.

## Local development

The current implementation is **Python/Django**, not the original Node.js prototype.

Requirements: Python 3.10+ and pip. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On Windows, activate with `.venv\Scripts\activate`. Set a local `DJANGO_SECRET_KEY` and suitable `DJANGO_ALLOWED_HOSTS` in `.env`; keep `DJANGO_DEBUG=1` for local-only development. Check the existing `.env.example` for other supported settings. Never commit `.env`, API keys, invite links, or real user data.

Free mode is the default: local rules screen live adverts and templates generate packs without paid AI. Live search requires Adzuna credentials. Local screening only recognises basic graduate-role criteria and excludes complex or ambiguous adverts; confirm full requirements with the employer. Under Profile → Optional API connections, users can select Claude and provide a personal Anthropic key for enhanced parsing, matching and drafting. Personal credentials remain in tab memory and are sent with requests, never stored in workspace or browser storage; reload clears them. Adzuna credentials are configured only by the site administrator and shared by all users; users never enter job-feed keys. Free live searches screen up to 50 adverts per page; Claude screens up to 15 per page. Load more jobs appends the next page when available; each page uses one daily live-search attempt. The You page stores role interests (up to three), UK-wide/remote or up to two chosen locations, and opportunity type. CV skills suggest editable interests; locations are chosen explicitly. Find my roles automatically searches the selected source. Live search combines preferences, deduplicates overlapping adverts and supports loading subsequent batches. The free batch budget of 50 adverts (15 with Claude) is split across interest/location combinations; each combination consumes one live-search attempt. Edit preferences on Swipe returns to the You page. Search totals, fetched and excluded counts are displayed separately. Shared server Claude keys are disabled by default; administrators must opt in with `HIREATIONSHIP_ALLOW_SHARED_CLAUDE=1`, and users must explicitly select that mode. Personal keys remain optional. Claude requests may incur charges on the selected API account.

### Optional integrations and limits

| Setting | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Enable Claude-assisted features; otherwise use template/demo writing |
| `ANTHROPIC_MODEL` | Optional Claude model override |
| `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` | Enable live Adzuna vacancy search |
| `HIREATIONSHIP_DAILY_GENERATION_LIMIT` | Application generation attempts per user per day; default `4` |
| `HIREATIONSHIP_DAILY_AI_LIMIT` | Claude-backed requests per user per day; default `20` |
| `HIREATIONSHIP_AI_ENABLED` | Set to `0` to temporarily disable Claude-backed features |
| `HIREATIONSHIP_INVITE_CONTACT_EMAIL` | Email address for login-page access requests (PR #11) |

To create a judge invitation after applying the invite migration:

```bash
python manage.py create_invite --days 30
```

Run again for each person. Invitations are single-use. The default validity without `--days` is seven days.

Invitation commands and the judge-access documents below describe the historical invitation system; tokens are no longer required for registration.

### PythonAnywhere deployment

The live instance runs on PythonAnywhere with SQLite and static assets served from the configured static directory. After merging a PR:

```bash
cd ~/ClaudeBuilderHackathon
workon hireationship-env
git pull --ff-only origin main
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
```

Then go to **PythonAnywhere → Web → Reload** and hard-refresh the browser. Back up the local `db.sqlite3` before significant schema changes. The database and `.env` are server-local files and must not be committed.

## Technology

- **Backend:** Python, Django, SQLite, Django authentication and middleware
- **Frontend:** vanilla JavaScript, HTML and CSS
- **Job feed:** Adzuna API (optional) plus illustrative sample roles
- **Writing:** Anthropic Claude API (optional), with template fallback
- **CV ingestion:** pypdf and python-docx
- **PDF export:** ReportLab
- **Hosting:** PythonAnywhere

## Repository layout

```text
config/                 Django settings, URLs and WSGI configuration
matching/               Eligibility matching, API endpoints, Claude integration,
                        data models, access controls and migrations
matching/management/    Invitation-generation command (PR #11)
templates/              App, login and invite registration templates
static/                 Frontend JavaScript and CSS
requirements.txt        Python dependencies
manage.py               Django management entry point
JUDGES_ACCESS.md        Judge onboarding and email templates (PR #11)
```

## Current limitations and roadmap

- **Job eligibility is not verified by employers.** Live advertisements may omit critical criteria; always confirm right-to-work rules, deadlines, sponsorship and requirements at the original source.
- **Demo listings are illustrative**, not real vacancies. Competitiveness and fit are estimates, not admission probabilities.
- **AI-generated text requires human review.** The app aims not to invent experience, but generated claims and formatting should always be checked.
- **Free-tier constraints:** SQLite and hosted storage are intentionally lightweight; generated PDF files and original uploads are not maintained as permanent server-side files.
- **Registration is open.** Live searches use a per-account daily allowance; no email verification or paid plans are implemented.
- **Future ideas:** deadline reminders, improved job coverage and matching, more export formats, and optional paid tiers. These are **not currently available**.

---

*Hireationship helps you find opportunities worth pursuing — and spend less time rewriting the same application.*

### Vercel hostname configuration

Django adds the exact deployment, branch and production hostnames from `VERCEL_URL`, `VERCEL_BRANCH_URL` and `VERCEL_PROJECT_PRODUCTION_URL` to its host and CSRF-origin lists. Enable system environment variables in Vercel and redeploy after updating the code. `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` can provide additional explicit domains. Other Vercel tenants are not trusted. This host configuration does not migrate the existing SQLite database or provide persistent database storage on Vercel.
