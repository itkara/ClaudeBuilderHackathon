import json,logging,time
from io import BytesIO
from pypdf import PdfReader
from docx import Document
from datetime import datetime,timedelta,timezone
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from . import claude,demo,matcher
log=logging.getLogger(__name__)
@ensure_csrf_cookie
def index(request):return render(request,'index.html')
def endpoint(method='POST'):
 def decorate(fn):
  def wrapped(request):
   if request.method!=method:return JsonResponse({'error':'Method not allowed'},status=405)
   try:
    data=json.loads(request.body) if request.body else {}
    if not isinstance(data,dict):return JsonResponse({'error':'Expected a JSON object'},status=400)
    return JsonResponse(fn(data))
   except (ValueError,TypeError,KeyError) as exc:return JsonResponse({'error':str(exc)},status=400)
   except Exception:
    log.exception('API failure');return JsonResponse({'error':'Request failed. Check server logs.'},status=500)
  return wrapped
 return decorate
@endpoint('GET')
def status(data):return {'mode':'claude' if claude.has_key() else 'demo'}
@endpoint()
def profile(data):
 cv=data.get('cvText') or ''
 if len(cv.strip())<30:raise ValueError('Paste your CV text first.')
 return {'profile':claude.extract_profile(cv) if claude.has_key() else demo.demo_profile(cv),'mode':'claude' if claude.has_key() else 'demo'}
def load_roles():
 now=datetime.now(timezone.utc)
 raw=json.loads((settings.BASE_DIR/'data/roles.json').read_text())
 return [{**r,'sample':True,'closes':(now+timedelta(days=r['closesInDays'])).date().isoformat()} for r in raw]
@endpoint()
def match(data):
 p=data.get('profile') or {}
 if not p.get('gradYear'):raise ValueError('Set your graduation year first.')
 families=claude.suggest_families(p) if claude.has_key() else demo.demo_families(p)
 ids={f['id'] for f in families}
 roles=(data.get('extraRoles') or [])+load_roles()
 results=matcher.rank(matcher.match_all(p,roles))
 return {'stage':matcher.stage_for(p['gradYear']),'families':families,'results':[{**r,'inFamily':r['role'].get('sector') in ids or r['role'].get('custom') is True} for r in results],'hiddenCount':len(roles)-len(results)}
@endpoint()
def jd(data):
 if not claude.has_key():raise ValueError('Adding a role from a job description needs an Anthropic API key (see README).')
 text=data.get('text') or ''
 if len(text.strip())<80:raise ValueError('Paste the full job description.')
 role=claude.extract_role(text)
 return {'role':{**role,'id':'jd-'+str(int(time.time()*1000)),'custom':True,'sample':False,'stages':role.get('stages') or ['final','penultimate','early']}}
@endpoint()
def generate(data):
 p=data.get('profile');r=data.get('role')
 if not p or not r:raise ValueError('Missing profile or role.')
 ev=matcher.evaluate(p,r)
 return {**claude.generate_pack(p,r,ev),'mode':'claude'} if claude.has_key() else demo.demo_pack(p,r,ev)


def upload_cv(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    uploaded = request.FILES.get('cv')
    if not uploaded:
        return JsonResponse({'error': 'Choose a PDF or .docx file.'}, status=400)
    if uploaded.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'CV must be smaller than 5 MB.'}, status=400)
    extension = Path(uploaded.name).suffix.lower()
    if extension not in ('.pdf', '.docx'):
        return JsonResponse({'error': 'Only PDF and Word (.docx) files are supported.'}, status=400)
    try:
        content = uploaded.read()
        if extension == '.pdf':
            if not content.startswith(b'%PDF-'):
                raise ValueError('This does not appear to be a valid PDF.')
            reader = PdfReader(BytesIO(content))
            if len(reader.pages) > 25:
                raise ValueError('Please upload a CV of 25 pages or fewer.')
            cv_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            if not content.startswith(b'PK'):
                raise ValueError('This does not appear to be a valid Word document.')
            doc = Document(BytesIO(content))
            parts = [para.text for para in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(' | '.join(cell.text for cell in row.cells))
            cv_text = '\n'.join(parts)
        cv_text = cv_text.strip()
        if len(cv_text) < 30:
            raise ValueError('Could not extract enough text. For scanned PDFs, paste the CV text manually.')
        if len(cv_text) > 50000:
            raise ValueError('CV text is too long. Please shorten it to 50,000 characters.')
        return JsonResponse({'cvText': cv_text})
    except (ValueError, Exception) as exc:
        log.warning('CV upload failed: %s', type(exc).__name__)
        return JsonResponse({'error': str(exc) if isinstance(exc, ValueError) else 'Could not read this CV file.'}, status=400)
