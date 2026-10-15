'use strict';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  get(k, d) { try { const v = localStorage.getItem('hr.' + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('hr.' + k, JSON.stringify(v)); } catch { /* storage unavailable: state lives in memory only */ } },
};
async function api(path, body) {
  const res = await fetch(path, body ? { method: 'POST', headers: { 'content-type': 'application/json', 'X-CSRFToken': document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '' }, body: JSON.stringify(body) } : undefined);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
  return json;
}
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 3200); }

$('#privacyOpen').addEventListener('click', () => $('#privacyDialog').showModal());
$('#privacyClose').addEventListener('click', () => $('#privacyDialog').close());
$('#privacyClear').addEventListener('click', () => {
  if (!confirm('Delete Hireationship CV, profile, application drafts and preferences stored in this browser?')) return;
  try {
    Object.keys(localStorage).filter(key => key.startsWith('hr.')).forEach(key => localStorage.removeItem(key));
  } catch {
    alert('Could not clear browser storage. Please clear this site\'s data in browser settings.');
    return;
  }
  location.reload();
});
const SUBJECT_TAGS = ['physics', 'maths', 'engineering', 'computer-science', 'chemistry', 'biology', 'economics', 'humanities', 'other'];
const STATUSES = ['Ready to apply', 'Applied', 'Online assessment', 'Interview', 'Offer', 'Rejected', 'Withdrawn'];
const FAMILY_NAMES = { 'quant-finance': 'Quant & finance', 'data-science': 'Data science', engineering: 'Engineering', consulting: 'Consulting', research: 'Research', 'policy-science-comms': 'Policy & science comms', 'patent-law': 'Patent law', software: 'Software', teaching: 'Teaching' };
const EXAMPLE_CV = `Alex Example
BSc Physics, University of Exampleshire. Graduating 2027, predicted First.
github.com/alex-example

Experience
- Wrote Python scripts to fit and plot 40 hours of oscillation data for a third-year lab project, with statistics on the uncertainties
- Tutored 6 first-year students in mechanics weekly, improving their mock exam marks (tutoring, communication)
- Treasurer of the Astronomy Society: managed a 1,200 GBP budget in Excel and presented the term report to 60 members

Projects
- Simulated a three-body orbit in Python with numerical methods and wrote up the modelling choices
- Used Git for a 3-person coding project`;

let profile = store.get('profile', null);
let parsed = store.get('parsed', { experiences: [], projects: [] });
let apps = store.get('apps', []);
let passed = store.get('passed', []);
let extraRoles = store.get('extraRoles', []);
let families = [];
let results = [];
let busy = false;

/* ---------- navigation ---------- */
function show(view) {
  document.querySelectorAll('.view').forEach((v) => (v.hidden = v.id !== 'view-' + view));
  document.querySelectorAll('nav button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
  if (view === 'swipe') renderSwipe();
  if (view === 'tracker') renderTracker();
}
document.querySelectorAll('nav button').forEach((b) => b.addEventListener('click', () => show(b.dataset.view)));

/* ---------- profile ---------- */
$('#subjectTags').innerHTML = SUBJECT_TAGS.map((t) => `<label><input type="checkbox" value="${t}"> ${t}</label>`).join('');

function fillForm(p) {
  $('#f-name').value = p.name || '';
  $('#f-subject').value = p.subject || '';
  $('#f-gradYear').value = p.gradYear || '';
  $('#f-class').value = p.classification || '';
  $('#f-rtw').value = p.rightToWork || 'UK';
  $('#f-skills').value = (p.skills || []).join(', ');
  $('#f-github').value = p.links?.github || '';
  $('#f-portfolio').value = p.links?.portfolio || '';
  document.querySelectorAll('#subjectTags input').forEach((i) => (i.checked = (p.subjectTags || []).includes(i.value)));
}
function readForm() {
  return {
    name: $('#f-name').value.trim(), subject: $('#f-subject').value.trim(),
    gradYear: Number($('#f-gradYear').value) || null, classification: $('#f-class').value,
    rightToWork: $('#f-rtw').value,
    skills: $('#f-skills').value.split(',').map((s) => s.trim().toLowerCase()).filter(Boolean),
    subjectTags: [...document.querySelectorAll('#subjectTags input:checked')].map((i) => i.value),
    links: { github: $('#f-github').value.trim(), portfolio: $('#f-portfolio').value.trim(), linkedin: parsed.links?.linkedin || '' },
    experiences: parsed.experiences || [], projects: parsed.projects || [],
  };
}
function setMsg(id, text, err) { const el = $(id); el.textContent = text; el.classList.toggle('err', Boolean(err)); }

async function readCv() {
  const cvText = $('#cvText').value;
  const btn = $('#readCv'); btn.disabled = true; setMsg('#readMsg', 'Reading your CV…');
  try {
    const { profile: p } = await api('/api/profile', { cvText });
    parsed = { experiences: p.experiences || [], projects: p.projects || [], links: p.links || {} };
    const current = readForm();
    fillForm({ ...p, subject: p.subject || current.subject, rightToWork: current.rightToWork });
    store.set('parsed', parsed); store.set('cv', cvText);
    setMsg('#readMsg', 'Done. Check the details on the right: especially graduation year and classification.');
    return true;
  } catch (e) { setMsg('#readMsg', e.message, true); return false; }
  finally { btn.disabled = false; }
}
$('#readCv').addEventListener('click', readCv);
$('#cvFile').addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) { setMsg('#uploadMsg', 'Please choose a file smaller than 5 MB.', true); return; }
  const data = new FormData();
  data.append('cv', file);
  setMsg('#uploadMsg', 'Extracting text from your CV…');
  const input = $('#cvFile'); input.disabled = true;
  try {
    const token = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '';
    const response = await fetch('/api/upload-cv', { method: 'POST', headers: { 'X-CSRFToken': token }, body: data });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Upload failed (${response.status})`);
    $('#cvText').value = result.cvText;
    setMsg('#uploadMsg', 'Text extracted. Analysing your CV and filling in your profile…');
    const success = await readCv();
    setMsg('#uploadMsg', success ? 'CV imported! Review the profile fields before finding matches.' : 'Text extracted, but profile analysis failed. You can retry with Read my CV.', !success);
  } catch (error) { setMsg('#uploadMsg', error.message, true); }
  finally { input.disabled = false; }
});
$('#loadExample').addEventListener('click', async () => {
  $('#cvText').value = EXAMPLE_CV;
  if (await readCv()) {
    $('#f-name').value = 'Alex Example'; $('#f-subject').value = 'BSc Physics'; $('#f-gradYear').value = 2027; $('#f-class').value = 'First';
    document.querySelectorAll('#subjectTags input').forEach((i) => (i.checked = i.value === 'physics'));
  }
});

$('#findRoles').addEventListener('click', async () => {
  if (!$('#cvText').value.trim() && !parsed.experiences.length) return setMsg('#findMsg', 'Paste your CV first so we can tailor things later.', true);
  if (!parsed.experiences.length && !(await readCv())) return;
  const p = readForm();
  if (!p.gradYear) return setMsg('#findMsg', 'Add your graduation year: it decides which roles you can apply for.', true);
  if (!p.classification) return setMsg('#findMsg', 'Add your current or predicted classification.', true);
  if (!p.subjectTags.length) return setMsg('#findMsg', 'Tick at least one subject area.', true);
  profile = p; store.set('profile', p);
  const btn = $('#findRoles'); btn.disabled = true; setMsg('#findMsg', 'Working out which roles suit you…');
  try { await runMatch(); setMsg('#findMsg', ''); show('swipe'); }
  catch (e) { setMsg('#findMsg', e.message, true); }
  finally { btn.disabled = false; }
});

async function runMatch() {
  const data = await api('/api/match', { profile, extraRoles });
  families = data.families; results = data.results;
  $('#swipeSub').textContent = `You graduate in ${profile.gradYear}, so we're showing ${data.stage}-year opportunities you're eligible for, plus a few stretches.`;
}



let jobMode = store.get('jobMode', 'demo') === 'live' ? 'live' : 'demo';
function setJobMode(mode) {
  jobMode = mode === 'live' ? 'live' : 'demo';
  store.set('jobMode', jobMode);
  $('#demoModePanel').hidden = jobMode !== 'demo';
  $('#liveModePanel').hidden = jobMode !== 'live';
  $('#demoModeBtn').className = jobMode === 'demo' ? 'btn primary' : 'btn ghost';
  $('#liveModeBtn').className = jobMode === 'live' ? 'btn primary' : 'btn ghost';
  $('#demoModeBtn').setAttribute('aria-pressed', String(jobMode === 'demo'));
  $('#liveModeBtn').setAttribute('aria-pressed', String(jobMode === 'live'));
  $('#jobModeDescription').textContent = jobMode === 'live'
    ? 'Live: search real UK job advertisements. Eligibility and deadlines must be verified.'
    : 'Demo: explore fictional example roles with swipe matching.';
  if (jobMode === 'demo') renderSwipe();
}
$('#demoModeBtn').addEventListener('click', () => setJobMode('demo'));
$('#liveModeBtn').addEventListener('click', () => setJobMode('live'));
setJobMode(jobMode);

let liveJobs = [];
$('#searchLiveJobs').addEventListener('click', async () => {
 const button=$('#searchLiveJobs'); button.disabled=true; setMsg('#liveJobsMsg','Searching…');
 try {
  const params=new URLSearchParams({what:$('#liveKeywords').value,where:$('#liveLocation').value});
  const response=await fetch('/api/live-jobs?'+params);
  const data=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(data.error||'Search failed');
  liveJobs=data.jobs||[];
  $('#liveJobsResults').innerHTML=liveJobs.map((job,i)=>'<div class="card app"><div><h3>'+esc(job.title)+'</h3><p class="meta">'+esc(job.employer)+' · '+esc(job.location)+'</p><p>'+esc(job.summary)+'</p><p class="hint">Eligibility and closing date unverified.</p></div><div class="actions"><a class="btn ghost" target="_blank" rel="noopener noreferrer" href="'+esc(job.applyUrl)+'">View job ↗</a><button class="btn" data-live-save="'+i+'">Save to applications</button></div></div>').join('')||'<p class="hint">No advertisements found.</p>';
  setMsg('#liveJobsMsg',liveJobs.length+' live advertisements found. Check eligibility and deadlines on the job page.');
 } catch(e){setMsg('#liveJobsMsg',e.message,true);}
 finally{button.disabled=false;}
});
$('#liveJobsResults').addEventListener('click',(e)=>{
 const button=e.target.closest('[data-live-save]');if(!button)return;
 const job=liveJobs[Number(button.dataset.liveSave)];
 if(!job||apps.some(a=>a.role.id===job.id)){toast('Already saved');return;}
 const role={...job,custom:true,sample:false,source:'Adzuna',eligibilityUnverified:true};
 apps.push({id:'a'+Date.now(),role,tier:'unverified',category:'unverified',status:'Saved — check eligibility',docs:null,error:null,addedAt:new Date().toISOString()});
 saveApps();toast('Saved. Verify the requirements and deadline on the job page.');
});

/* ---------- swipe deck ---------- */
const byFit = (a, b) => b.fit - a.fit || b.role.competitiveness - a.role.competitiveness;
function queue() {
  const done = new Set([...passed, ...apps.map((a) => a.role.id)]);
  const showAll = $('#showAll').checked;
  const list = results.filter((r) => !done.has(r.role.id) && (r.inFamily || showAll));
  return $('#orderMode').value === 'fit' ? list.sort(byFit) : list;
}
const daysLeft = (iso) => Math.ceil((new Date(iso) - Date.now()) / 864e5);
const dots = (n) => `<span class="dots" aria-label="${n} out of 5">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= n ? 'on' : ''}"></i>`).join('')}</span>`;

function cardHTML(r) {
  const ro = r.role;
  const typeLabel = ro.type === 'grad' ? 'Graduate role' : ro.type === 'spring-week' ? 'Spring week' : 'Internship';
  const hard = [...r.hardPasses.map((t) => `<li class="ok">${esc(t)}</li>`)].join('');
  const chips = [...r.matched.map((s) => `<span class="chip ok">${esc(s)}</span>`), ...r.missingRequired.map((s) => `<span class="chip miss">needs ${esc(s)}</span>`), ...r.missingPreferred.map((s) => `<span class="chip">nice: ${esc(s)}</span>`)].join('');
  const d = daysLeft(ro.closes);
  return `<span class="stamp l">PASS</span><span class="stamp r">LIKE</span>
    ${ro.sample ? '<span class="sampleTag" title="Illustrative listing, not a live vacancy">Sample listing</span>' : ''}
    <div><span class="pill ${r.tier}">${r.tier === 'eligible' ? 'Eligible' : 'Stretch'}</span><span class="pill ${r.category}">${r.category}</span><span class="pill">${typeLabel}</span></div>
    <h2>${esc(ro.title)}</h2>
    <p class="emp">${esc(ro.employer)} · ${esc(ro.location || '')}</p>
    <p>${esc(ro.summary || '')}</p>
    <div class="meter">Competitiveness (estimate) ${dots(ro.competitiveness)} · Fit ${r.fit}%</div>
    <ul class="why">${hard}</ul>
    <div class="chips">${chips}</div>
    <p class="deadline">Closes ${esc(ro.closes)} (${d > 0 ? `in ${d} days` : 'closed'}). Always confirm the criteria and deadline on the employer's own page.</p>`;
}

function renderSwipe() {
  $('#families').innerHTML = families.length ? '<span class="famLabel">Suggested for you (hover for why):</span>' + families.map((f) => `<span class="fam" title="${esc(f.why)}">${esc(FAMILY_NAMES[f.id] || f.id)}</span>`).join('') : '';
  const q = queue();
  const deck = $('#deck');
  $('#swipeTitle').textContent = profile ? `${q.length} role${q.length === 1 ? '' : 's'} to look at` : 'Your matches';
  if (!profile || !results.length) { deck.innerHTML = '<p class="empty">Start with your profile, then your matches will appear here.</p>'; setBtns(false); return; }
  if (!q.length) { deck.innerHTML = '<p class="empty">You\'ve been through everything for now. Check <b>Applications</b>, or tick "show eligible roles outside my suggested areas".</p>'; setBtns(false); return; }
  deck.innerHTML = '';
  if (q[1]) { const n = document.createElement('div'); n.className = 'swipeCard next'; n.innerHTML = cardHTML(q[1]); deck.appendChild(n); }
  const top = document.createElement('div'); top.className = 'swipeCard'; top.innerHTML = cardHTML(q[0]); deck.appendChild(top);
  attachDrag(top); setBtns(true);
}
function setBtns(on) { $('#passBtn').disabled = !on; $('#likeBtn').disabled = !on; }

function attachDrag(card) {
  let sx = 0, dx = 0, active = false;
  const stamps = () => { card.querySelector('.stamp.r').style.opacity = Math.max(0, Math.min(1, dx / 110)); card.querySelector('.stamp.l').style.opacity = Math.max(0, Math.min(1, -dx / 110)); };
  card.addEventListener('pointerdown', (e) => { if (e.target.closest('a,button')) return; active = true; sx = e.clientX; card.classList.add('dragging'); card.setPointerCapture(e.pointerId); });
  card.addEventListener('pointermove', (e) => { if (!active) return; dx = e.clientX - sx; card.style.transform = `translateX(${dx}px) rotate(${dx / 18}deg)`; stamps(); });
  const end = () => {
    if (!active) return; active = false; card.classList.remove('dragging');
    if (Math.abs(dx) > 110) commit(dx > 0 ? 'right' : 'left'); else { card.style.transform = ''; dx = 0; stamps(); }
  };
  card.addEventListener('pointerup', end); card.addEventListener('pointercancel', end);
}

function commit(dir) {
  if (busy) return; const q = queue(); if (!q.length) return;
  busy = true;
  const card = $('#deck .swipeCard:not(.next)');
  if (card) { card.classList.remove('dragging'); card.style.transform = `translateX(${dir === 'right' ? 700 : -700}px) rotate(${dir === 'right' ? 25 : -25}deg)`; card.style.opacity = 0; }
  const r = q[0];
  setTimeout(() => {
    if (dir === 'right') { addApp(r); } else { passed.push(r.role.id); store.set('passed', passed); }
    busy = false; renderSwipe();
  }, 230);
}
$('#passBtn').addEventListener('click', () => commit('left'));
$('#likeBtn').addEventListener('click', () => commit('right'));
document.addEventListener('keydown', (e) => {
  if ($('#view-swipe').hidden || e.target.closest('input,textarea,select') || $('#pack').open) return;
  if (e.key === 'ArrowLeft') commit('left'); if (e.key === 'ArrowRight') commit('right');
});
$('#orderMode').addEventListener('change', renderSwipe);
$('#showAll').addEventListener('change', renderSwipe);

$('#addJd').addEventListener('click', async () => {
  const btn = $('#addJd'); btn.disabled = true; setMsg('#jdMsg', 'Reading the job description…');
  try {
    const { role } = await api('/api/jd', { text: $('#jdText').value });
    extraRoles = [role, ...extraRoles]; store.set('extraRoles', extraRoles);
    await runMatch();
    const found = results.find((r) => r.role.id === role.id);
    setMsg('#jdMsg', found ? `Added: it's a ${found.tier === 'eligible' ? 'good' : 'stretch'} match and sits at the right place in your deck.` : 'Added, but you don\'t meet its hard requirements, so it isn\'t shown.', !found);
    $('#jdText').value = ''; $('#showAll').checked = true; renderSwipe();
  } catch (e) { setMsg('#jdMsg', e.message, true); } finally { btn.disabled = false; }
});

/* ---------- applications ---------- */
function addApp(r) {
  const app = { id: 'a' + Date.now(), role: r.role, tier: r.tier, category: r.category, status: 'Drafting', docs: null, error: null, addedAt: new Date().toISOString() };
  apps.push(app); saveApps(); toast(`Drafting your application to ${r.role.employer.replace(' (sample)', '')}…`); generate(app);
}
async function generate(app) {
  app.status = 'Drafting'; app.error = null; saveApps();
  try {
    app.docs = await api('/api/generate', { profile, role: app.role });
    app.status = 'Ready to apply'; toast(`Pack ready: ${app.role.title}`);
  } catch (e) { app.status = 'Draft failed'; app.error = e.message; }
  saveApps();
}
function saveApps() { store.set('apps', apps); $('#appCount').textContent = apps.length; if (!$('#view-tracker').hidden) renderTracker(); }

function renderTracker() {
  const list = $('#trackerList');
  if (!apps.length) { list.innerHTML = '<p class="empty">Nothing here yet. Swipe right on a role and its application pack will appear.</p>'; return; }
  const sorted = [...apps].sort((a, b) => (a.role.closes ? new Date(a.role.closes).getTime() : Infinity) - (b.role.closes ? new Date(b.role.closes).getTime() : Infinity));
  list.innerHTML = sorted.map((a) => {
    const d = a.role.closes ? daysLeft(a.role.closes) : null;
    const opts = [...new Set([a.status, ...STATUSES])].filter((s) => s !== 'Drafting' && s !== 'Draft failed' || s === a.status).map((s) => `<option ${s === a.status ? 'selected' : ''}>${esc(s)}</option>`).join('');
    return `<div class="card app" data-id="${esc(a.id)}">
      <div><h3>${esc(a.role.title)}</h3><div class="meta">${esc(a.role.employer)} · ${esc(a.category)} · ${a.role.closes ? 'closes '+esc(a.role.closes) : 'closing date unverified'} <span class="${d !== null && d <= 7 ? 'urgent' : ''}">${d === null ? '' : '('+(d > 0 ? d + ' days left' : 'closed')+')'}</span></div>${a.error ? `<div class="hint err">${esc(a.error)}</div>` : ''}</div>
      <div class="actions">
        ${a.status === 'Drafting' ? '<span class="hint">Drafting…</span>' : a.status === 'Draft failed' ? '<button class="btn" data-act="retry">Retry</button>' : `<select data-act="status" aria-label="Status">${opts}</select>${a.docs ? '<button class="btn" data-act="open">Open pack</button>' : '<button class="btn" data-act="draft">Draft application</button>'}`}
        ${a.role.applyUrl && a.role.applyUrl.startsWith("https://") ? `<a class="btn ghost" href="${esc(a.role.applyUrl)}" target="_blank" rel="noopener noreferrer">View job ↗</a>` : ""}<button class="btn ghost" data-act="remove" title="Remove from tracker">Remove</button>
      </div></div>`;
  }).join('');
}
$('#trackerList').addEventListener('click', (e) => {
  const act = e.target.dataset.act; if (!act || act === 'status') return;
  const app = apps.find((a) => a.id === e.target.closest('.app').dataset.id); if (!app) return;
  if (act === 'open' && app.docs) openPack(app);
  if (act === 'retry' || act === 'draft') { if(app.role.eligibilityUnverified && !confirm('Have you checked eligibility and the closing date on the original job advert?'))return; generate(app); renderTracker(); }
  if (act === 'remove') { apps = apps.filter((a) => a !== app); saveApps(); renderTracker(); }
});
$('#trackerList').addEventListener('change', (e) => {
  if (e.target.dataset.act !== 'status') return;
  const app = apps.find((a) => a.id === e.target.closest('.app').dataset.id); if (app) { app.status = e.target.value; saveApps(); }
});

/* ---------- pack viewer ---------- */
let current = null; let tab = 'cv';
const TABS = [['cv', 'Tailored CV'], ['letter', 'Cover letter'], ['docs', 'Supporting docs'], ['gaps', 'Close the gaps'], ['trace', 'Where each line came from']];
function packText(d, t) {
  if (t === 'cv') return d.cv || '';
  if (t === 'letter') return d.coverLetter || 'This employer does not ask for a cover letter.';
  if (t === 'docs') return (d.supportingDocs || []).map((x) => `[${x.status === 'have' ? 'have' : 'need'}] ${x.item}: ${x.note}`).join('\n') || 'No extra documents beyond your basic details.';
  if (t === 'gaps') return (d.gapPlan || []).map((x, i) => `${i + 1}. ${x.action}\n   Why: ${x.why}\n   Effort: ${x.effort}`).join('\n') || 'No gaps: you meet everything this role asks for.';
  return (d.traceability || []).map((x) => `- "${x.line}"\n   from: ${x.source}`).join('\n');
}
function openPack(app) {
  current = app; tab = 'cv';
  $('#packTitle').textContent = `${app.role.title}, ${app.role.employer}`;
  $('#packTabs').innerHTML = TABS.filter(([k]) => k !== 'letter' || app.docs.coverLetter !== null).map(([k, l]) => `<button data-t="${k}">${l}</button>`).join('');
  renderPack(); $('#pack').showModal();
}
function renderPack() {
  const d = current.docs;
  document.querySelectorAll('#packTabs button').forEach((b) => b.classList.toggle('active', b.dataset.t === tab));
  if (tab === 'docs') {
    const items = (d.supportingDocs || []).map((x) => `<li><span class="pill ${x.status === 'have' ? 'ok' : 'miss'} chip ${x.status === 'have' ? 'ok' : 'miss'}">${x.status === 'have' ? 'You have this' : 'To prepare'}</span> <b>${esc(x.item)}</b><br>${esc(x.note)}</li>`).join('');
    $('#packBody').innerHTML = items ? `<p class="hint">Beyond your name, address and the usual details, this application also wants:</p><ul>${items}</ul>` : '<p>No extra documents beyond your basic details.</p>';
  } else if (tab === 'cv' || tab === 'letter') {
    $('#packBody').innerHTML = `<p class="hint">Edit this draft before generating your PDF. Check every claim and detail.</p><textarea id="editPackText" rows="17" style="width:100%;box-sizing:border-box" aria-label="Edit ${tab === 'cv' ? 'CV' : 'cover letter'}">${esc(packText(d, tab))}</textarea>`;
  } else $('#packBody').innerHTML = `<pre>${esc(packText(d, tab))}</pre>`;
  $('#pdfControls').hidden = !(tab === 'cv' || tab === 'letter');
  if (d.mode === 'demo') $('#packBody').insertAdjacentHTML('afterbegin', '<p class="hint">Demo mode: templated from your CV lines. Add an Anthropic API key for fully tailored writing.</p>');
}
$('#packBody').addEventListener('input', (e) => { if (!current || e.target.id !== 'editPackText') return; if (tab === 'cv') current.docs.cv = e.target.value; else if (tab === 'letter') current.docs.coverLetter = e.target.value; saveApps(); });
$('#generatePdf').addEventListener('click', async () => {
  if (!current || !['cv','letter'].includes(tab)) return;
  const button = $('#generatePdf'); button.disabled = true; setMsg('#pdfMsg', 'Generating PDF…');
  try {
    const response = await fetch('/api/export-pdf', { method:'POST', headers:{ 'content-type':'application/json', 'X-CSRFToken': document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '' }, body:JSON.stringify({ kind:tab, text:packText(current.docs, tab), template:$('#pdfTemplate').value }) });
    if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(error.error || 'PDF export failed'); }
    const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url;
    link.download = `${current.role.employer.replace(/[^a-z0-9]+/gi, '-')}-${tab === 'cv' ? 'cv' : 'cover-letter'}.pdf`; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
    setMsg('#pdfMsg', 'PDF ready.');
  } catch (error) { setMsg('#pdfMsg', error.message, true); } finally { button.disabled = false; }
});
$('#packTabs').addEventListener('click', (e) => { if (e.target.dataset.t) { tab = e.target.dataset.t; renderPack(); } });
$('#packClose').addEventListener('click', () => $('#pack').close());
$('#packCopy').addEventListener('click', async () => { try { await navigator.clipboard.writeText(packText(current.docs, tab)); toast('Copied'); } catch { toast('Copy failed: select the text manually'); } });
$('#packDownload').addEventListener('click', () => {
  const d = current.docs;
  const md = [`# ${current.role.title}, ${current.role.employer}`, `Closes ${current.role.closes}`, '', '## Tailored CV', d.cv, '', d.coverLetter ? `## Cover letter\n${d.coverLetter}\n` : '', '## Supporting documents', packText(d, 'docs'), '', '## Close the gaps', packText(d, 'gaps'), '', '## Where each line came from', packText(d, 'trace')].join('\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([md], { type: 'text/markdown' }));
  a.download = `${current.role.employer.replace(/[^a-z0-9]+/gi, '-')}-pack.md`; a.click(); URL.revokeObjectURL(a.href);
});

/* ---------- boot ---------- */
(async function boot() {
  $('#appCount').textContent = apps.length;
  try {
    const { mode } = await api('/api/status');
    $('#modeBadge').textContent = mode === 'claude' ? 'AI: Claude' : 'AI: Templates';
    $('#modeBadge').title = mode === 'claude' ? 'Application writing uses Claude; job source is selected separately.' : 'Application writing uses templates; job source is selected separately.';
  } catch { $('#modeBadge').textContent = 'Server offline'; }
  const cv = store.get('cv', ''); if (cv) $('#cvText').value = cv;
  if (profile) {
    fillForm(profile);
    try { await runMatch(); } catch { /* user can press Find my roles again */ }
  }
})();
