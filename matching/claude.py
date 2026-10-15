import os,json,requests
API='https://api.anthropic.com/v1/messages'
FAMILIES='quant-finance, data-science, engineering, consulting, research, policy-science-comms, patent-law, software, teaching'
SUBJECT_TAGS='physics, maths, engineering, computer-science, chemistry, biology, economics, humanities, other'
def has_key():return bool(os.getenv('ANTHROPIC_API_KEY'))
def ask(system,user,max_tokens=4096):
 response=requests.post(API,headers={'content-type':'application/json','x-api-key':os.environ['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},json={'model':os.getenv('ANTHROPIC_MODEL','claude-sonnet-4-5'),'max_tokens':max_tokens,'system':system,'messages':[{'role':'user','content':user}]},timeout=90)
 if not response.ok:raise ValueError(f'Claude API {response.status_code}: {response.text[:300]}')
 return ''.join(b['text'] for b in response.json()['content'] if b['type']=='text')
def parse_json(text):
 a=text.find('{');b=text.rfind('}')
 if a<0 or b<0:raise ValueError('The model reply did not contain JSON')
 return json.loads(text[a:b+1])
def extract_profile(cv):
 system='You read student CVs and return structured JSON only. Never invent facts: if something is not in the CV, leave it empty or null.'
 user=f"""Extract this CV into JSON with exactly these keys:
{{"name":str,"subject":str,"subjectTags":[from: {SUBJECT_TAGS}],"gradYear":int|null,"classification":"First"|"2:1"|"2:2"|"Third"|null,"skills":[short lowercase skill names],"links":{{"github":str,"portfolio":str,"linkedin":str}},"experiences":[{{"title":str,"org":str,"bullets":[str]}}],"projects":[{{"name":str,"description":str}}]}}
Copy bullets as written in the CV.

CV:
{cv}"""
 return parse_json(ask(system,user,3000))
def suggest_families(profile):
 user=f"""Given this student profile, choose the 3 to 5 role families that suit them best, most suitable first. Think beyond the obvious: use their subject mix, projects and interests. Allowed ids: {FAMILIES}.
Return {{"families":[{{"id":str,"why":"one sentence citing evidence from the profile"}}]}}

Profile:
{json.dumps(profile)}"""
 return parse_json(ask('You are a careers adviser for UK university students. Return JSON only.',user,1200))['families']
def extract_role(text):
 user=f"""Return {{"employer":str,"title":str,"type":"spring-week"|"internship"|"grad","sector":one of [{FAMILIES}],"location":str,"closes":"YYYY-MM-DD"|null,"stages":[subset of "early","penultimate","final"],"minClassification":"First"|"2:1"|"2:2"|null,"subjects":["any" or tags from {SUBJECT_TAGS}],"rightToWork":"UK"|"any","skillsRequired":[short lowercase skills],"skillsPreferred":[...],"competitiveness":1-5 (a rough estimate from employer profile and requirements),"needsCoverLetter":bool,"supportingDocs":[things beyond basic personal details, e.g. portfolio, GitHub, writing sample, transcript],"summary":"one sentence"}}
Job description:
{text}"""
 return parse_json(ask('You turn job descriptions into structured JSON. Return JSON only. Do not guess: use null or [] when the text does not say.',user,1500))
def generate_pack(profile,role,ev):
 system='You write job applications for a student. The most important rule: NEVER invent or exaggerate experience, skills, grades or dates. Every claim must come from the profile provided. If the student lacks something the role wants, do not hide it behind vague wording; leave it out of the CV and put it in the gap plan. Write in plain, specific UK English with no clichés ("passionate", "team player"). Return JSON only.'
 user=f"""Role:
{json.dumps(role)}

Where the student matches and misses (computed separately; trust it):
{json.dumps({k:ev[k] for k in ('matched','missingRequired','missingPreferred')})}

Student profile and base CV:
{json.dumps(profile)}

Return:
{{"cv":"markdown CV tailored to this role: reorder and reword the student's real material to foreground what this role values; one page",
"coverLetter":{'"under 300 words, specific to this employer and role, using only real evidence"' if role.get('needsCoverLetter') else 'null'},
"supportingDocs":[{{"item":str,"status":"have"|"need","note":"what exactly to prepare, or which link of theirs covers it"}}] (only things beyond basic personal details; base it on role.supportingDocs plus anything the CV is missing that the role evidently expects),
"gapPlan":[{{"action":"a concrete thing to do before the deadline","why":"which missing requirement it closes","effort":"realistic time estimate"}}] (2 to 4 items, achievable before {role.get('closes') or 'the deadline'}),
"traceability":[{{"line":"a notable claim from the tailored CV","source":"where in the base CV it comes from"}}]}} """
 return parse_json(ask(system,user,5000))
