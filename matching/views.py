import json,logging,time
from io import BytesIO
from pypdf import PdfReader
from docx import Document
from datetime import datetime,timedelta,timezone
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse, HttpResponse
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


def export_pdf(request):
    """Render user-reviewed application text as a downloadable PDF."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        from io import BytesIO
        from xml.sax.saxutils import escape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        payload = json.loads(request.body)
        kind = payload.get('kind')
        content = payload.get('text', '')
        if kind not in ('cv', 'letter') or not isinstance(content, str) or not content.strip() or len(content) > 50000:
            raise ValueError('Choose a CV or cover letter containing up to 50,000 characters.')
        template = payload.get('template', 'classic')
        if template not in ('classic', 'modern'):
            raise ValueError('Invalid template.')
        styles = getSampleStyleSheet()
        navy = colors.HexColor('#263A67')
        accent = colors.HexColor('#E95B65') if template == 'modern' else navy
        body = ParagraphStyle('AppBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, spaceAfter=5, textColor=colors.HexColor('#222222'))
        heading = ParagraphStyle('AppHeading', parent=body, fontName='Helvetica-Bold', fontSize=11, leading=15, spaceBefore=10, spaceAfter=5, textColor=accent)
        title = ParagraphStyle('AppTitle', parent=heading, fontSize=16, leading=20, spaceAfter=12)
        bullet = ParagraphStyle('AppBullet', parent=body, leftIndent=14, firstLineIndent=-8)
        out = BytesIO()
        doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=48, rightMargin=48, topMargin=45, bottomMargin=45, title='Tailored CV' if kind == 'cv' else 'Cover letter')
        story = []
        for i, line in enumerate(content.splitlines()):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 7))
                continue
            line = line.lstrip('#').strip()
            if line.startswith(('- ', '* ', '• ')):
                story.append(Paragraph('&#8226; ' + escape(line[2:]), bullet))
            elif kind == 'cv' and (i == 0 or (len(line) < 65 and (line.isupper() or line.endswith(':')))):
                story.append(Paragraph(escape(line.rstrip(':')), title if i == 0 else heading))
            else:
                story.append(Paragraph(escape(line), body))
        doc.build(story)
        response = HttpResponse(out.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="hireationship-' + ('cv' if kind == 'cv' else 'cover-letter') + '.pdf"'
        response['Cache-Control'] = 'no-store'
        return response
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except Exception:
        log.exception('PDF export failed')
        return JsonResponse({'error': 'Could not generate PDF.'}, status=500)
