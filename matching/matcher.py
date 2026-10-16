import re
from datetime import datetime,date,timezone
CLASS_RANK={'first':4,'2:1':3,'2:2':2,'third':1}
SYNONYMS={'py':'python','ml':'machine learning','js':'javascript','stats':'statistics','modeling':'modelling','optimization':'optimisation'}
def norm(s):
 t=str(s or '').lower().strip();return SYNONYMS.get(t,t)
def academic_end_year(now=None):
 now=now or datetime.now(timezone.utc);return now.year+(now.month>=9)
def stage_for(year,now=None):
 d=int(year)-academic_end_year(now)
 return 'final' if d<=0 else 'penultimate' if d==1 else 'early'
def haystack(p):
 parts=list(p.get('skills') or [])
 for e in p.get('experiences') or []:parts += [e.get('title',''),e.get('org','')]+(e.get('bullets') or [])
 for x in p.get('projects') or []:parts.append(x if isinstance(x,str) else str(x.get('name',''))+' '+str(x.get('description','')))
 return ' \n '.join(str(x) for x in parts).lower()
def has_skill(p,skill,hay):
 s=norm(skill)
 return any(norm(x)==s for x in p.get('skills',[])) or (len(s)>2 and bool(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',hay)))
def categorise(tier,fit,competitiveness):
 if tier=='stretch':return 'reach'
 gap=float(competitiveness or 3)-fit/20
 return 'reach' if gap>=1 else 'safe' if gap<=-1 else 'target'
def evaluate(p,r,now=None):
 now=now or datetime.now(timezone.utc);stage=stage_for(p.get('gradYear'),now);passes=[];fails=[]
 def check(ok,yes,no): (passes if ok else fails).append(yes if ok else no)
 stages=r.get('stages') or ['early','penultimate','final']
 check(stage in stages,f'Open to {stage}-year students',f"Aimed at {'/'.join(stages)}-year students; you are {stage}-year")
 if r.get('minClassification'):
  have=CLASS_RANK.get(norm(p.get('classification')),0);need=CLASS_RANK.get(norm(r['minClassification']),0)
  check(have>=need,f"Needs {r['minClassification']} (you: {p.get('classification')})",f"Needs {r['minClassification']}; you have {p.get('classification') or 'not set'}")
 subjects=r.get('subjects') or ['any']
 if 'any' not in subjects:check(any(norm(s) in [norm(t) for t in p.get('subjectTags',[])] for s in subjects),'Your subject is accepted',f"Wants {', '.join(subjects)}")
 if r.get('rightToWork')=='UK':check(p.get('rightToWork')=='UK','Right to work in the UK','Requires UK right to work without sponsorship')
 if r.get('closes'):
  try:
   if date.fromisoformat(r['closes'])<now.date():check(False,'','Applications have closed')
  except ValueError:pass
 hay=haystack(p);req=r.get('skillsRequired') or [];pref=r.get('skillsPreferred') or []
 matched_req=[s for s in req if has_skill(p,s,hay)];matched_pref=[s for s in pref if has_skill(p,s,hay)]
 missing_req=[s for s in req if s not in matched_req];missing_pref=[s for s in pref if s not in matched_pref]
 denom=2*len(req)+len(pref);fit=int((2*len(matched_req)+len(matched_pref))/denom*100+0.5) if denom else 100
 tier='hidden'
 if not fails:
  if not missing_req:tier='eligible'

 return {'role':r,'stage':stage,'tier':tier,'fit':fit,'category':None if tier=='hidden' else categorise(tier,fit,r.get('competitiveness',3)),'hardPasses':passes,'hardFails':fails,'matched':matched_req+matched_pref,'missingRequired':missing_req,'missingPreferred':missing_pref}
def rank(results,mode='competitive'):
 arr=[r for r in results if r['tier']=='eligible']
 return sorted(arr,key=(lambda r:(-r['fit'],-r['role'].get('competitiveness',3))) if mode=='fit' else (lambda r:(-r['role'].get('competitiveness',3),-r['fit'])))
def match_all(profile,roles,now=None):return [evaluate(profile,r,now) for r in roles]
