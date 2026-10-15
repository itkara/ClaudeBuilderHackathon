import re
KNOWN_SKILLS=['python','c++','matlab','sql','excel','git','javascript','statistics','data analysis','machine learning','modelling','numerical methods','technical writing','writing','research','communication','problem solving','public speaking','tutoring','probability','optimisation','testing','algorithms','attention to detail']
FAMILY_RULES={'quant-finance':['python','statistics','probability','c++','machine learning'],'data-science':['python','data analysis','sql','machine learning','statistics'],'engineering':['modelling','matlab','python','numerical methods','optimisation'],'consulting':['communication','problem solving','excel','presentation'],'research':['research','python','numerical methods','data analysis','git'],'policy-science-comms':['writing','research','communication'],'patent-law':['technical writing','attention to detail','research'],'software':['git','python','javascript','testing','algorithms'],'teaching':['communication','tutoring','public speaking']}
def demo_profile(cv):
 lines=[x.strip() for x in cv.splitlines() if x.strip()];years=[int(x) for x in re.findall(r'\b(20[2-3]\d)\b',cv)];gh=re.search(r'github\.com/[\w-]+',cv,re.I)
 return {'name':lines[0] if lines and len(lines[0])<40 else '', 'subject':'','subjectTags':[],'gradYear':max(years) if years else None,'classification':'First' if re.search(r'\b(first|1st)\b',cv,re.I) else '2:1' if '2:1' in cv else '2:2' if '2:2' in cv else None,'skills':[s for s in KNOWN_SKILLS if s in cv.lower()],'links':{'github':'https://'+gh.group() if gh else '', 'portfolio':'','linkedin':''},'experiences':[{'title':'From your CV','org':'','bullets':[re.sub(r'^[-•*]\s*','',x) for x in lines if re.match(r'^[-•*]',x)]}],'projects':[]}
def demo_families(p):
 have=set(s.lower() for s in p.get('skills',[]));hum='humanities' in p.get('subjectTags',[]);out=[]
 for id,skills in FAMILY_RULES.items():
  hits=[s for s in skills if s in have];score=len(hits)+(int(hum) if id in ('policy-science-comms','patent-law') else 0)
  if score:out.append((score,{'id':id,'why':'Your CV shows '+', '.join(hits)+'.' if hits else 'Fits your subject mix.'}))
 return [x for _,x in sorted(out,key=lambda x:-x[0])[:4]]
def demo_pack(p,r,ev):
 bullets=[{'text':b,'source':'Experience: '+e.get('title','')+(' at '+e['org'] if e.get('org') else '')} for e in p.get('experiences',[]) for b in e.get('bullets',[])]
 bullets += [{'text':x.get('name','')+': '+x.get('description',''),'source':'Project: '+x.get('name','')} for x in p.get('projects',[]) if isinstance(x,dict)]
 wanted=[s.lower() for s in (r.get('skillsRequired',[])+r.get('skillsPreferred',[]))]
 top=sorted(bullets,key=lambda b:-sum(w in b['text'].lower() for w in wanted))[:6]
 skills=ev['matched']+[s for s in p.get('skills',[]) if s not in ev['matched']]
 links=' | '.join(f'{k}: {v}' for k,v in p.get('links',{}).items() if v)
 cv='\n'.join(['# '+(p.get('name') or 'Your name'),links,'','## Education',f"{p.get('subject') or 'Your degree'}, graduating {p.get('gradYear') or '—'}"+(f" ({p['classification']})" if p.get('classification') else ''),'','## Relevant skills',', '.join(skills),'','## Selected experience (reordered for this role)']+['- '+b['text'] for b in top])
 lead=top[0]['text'].rstrip('.') if top else 'my coursework';employer=r.get('employer','').replace(' (sample)','')
 letter=None
 if r.get('needsCoverLetter'):
  letter=f"Dear {employer} hiring team,\n\nI am applying for the {r.get('title','role')}. I am a {p.get('subject') or 'university'} student graduating in {p.get('gradYear')}, and the part of my background most relevant to this role is this: {lead}.\n\n"
  if len(top)>1:letter+='I have also '+top[1]['text'][:1].lower()+top[1]['text'][1:].rstrip('.')+'.\n\n'
  letter+=f"I would welcome the chance to discuss how I could contribute.\n\nKind regards,\n{p.get('name') or ''}\n\n[Demo mode: this is a template built from your own CV lines. Add an Anthropic API key to get a letter written for this specific role.]"
 docs=[]
 for item in r.get('supportingDocs',[]):
  have=bool(re.search('github|code|portfolio',item,re.I) and (p.get('links',{}).get('github') or p.get('links',{}).get('portfolio')))
  docs.append({'item':item,'status':'have' if have else 'need','note':'Covered by the link on your profile.' if have else 'Prepare this before you apply.'})
 gaps=(ev['missingRequired']+ev['missingPreferred'])[:4]
 return {'cv':cv,'coverLetter':letter,'supportingDocs':docs,'gapPlan':[{'action':f'Build a small piece of real evidence for "{g}" (a project, course or society role) and add it to your CV','why':('Required' if g in ev['missingRequired'] else 'Preferred')+' by '+employer,'effort':'1 to 3 weeks alongside term-time work'} for g in gaps],'traceability':[{'line':b['text'],'source':b['source']} for b in top],'mode':'demo'}
