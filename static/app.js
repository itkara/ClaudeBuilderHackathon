'use strict';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  data: {}, ready: false, timer: null, saving: Promise.resolve(),
  get(k, fallback) { return Object.hasOwn(this.data, k) ? this.data[k] : fallback; },
  set(k, value) {
    this.data[k] = value;
    if (!this.ready) return;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush(), 400);
  },
  flush() {
    if (!this.ready) return this.saving;
    clearTimeout(this.timer);
    const snapshot = JSON.stringify(this.data);
    this.saving = this.saving.catch(() => {}).then(async () => {
      const res = await fetch('/api/workspace', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || ''}, body:snapshot, keepalive:true});
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.error || 'Could not save workspace'); }
    }).catch(err => { console.error('Workspace save failed', err); toast('Could not save your changes. Please try again.'); });
    return this.saving;
  }
};
let aiMode = 'free';
let personalApiKey = '';
let fullAdvertReadsAvailable = true;
let fullAdvertReadNotice = '';
function connectionHeaders() {
  const headers = {'X-AI-Mode': aiMode};
  if (aiMode === 'personal') headers['X-Anthropic-Key'] = personalApiKey;
  return headers;
}
async function api(path, body) {
  const res = await fetch(path, {method: body ? 'POST' : 'GET', headers: {...connectionHeaders(), 'content-type': 'application/json', 'X-CSRFToken': document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || ''}, ...(body ? {body: JSON.stringify(body)} : {})});
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
  return json;
}
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 3200); }

$('#privacyOpen').addEventListener('click', () => $('#privacyDialog').showModal());
$('#privacyClose').addEventListener('click', () => $('#privacyDialog').close());
$('#privacyClear').addEventListener('click', async () => {
  if (!confirm('Permanently delete your CV, drafts, applications and swipe history from the Hireationship database?')) return;
  try {
    store.ready = false;
    clearTimeout(store.timer);
    await store.saving.catch(() => {});
    const res = await fetch('/api/workspace', {method:'DELETE', headers:{'X-CSRFToken':document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || ''}});
    if (!res.ok) throw new Error('Deletion failed');
    Object.keys(localStorage).filter(k => k.startsWith('hr.')).forEach(k => localStorage.removeItem(k));
    location.reload();
  } catch(e) { store.ready = true; alert('Could not delete your data. Please try again.'); }
});
const SUBJECT_TAGS = ['physics', 'maths', 'engineering', 'computer-science', 'chemistry', 'biology', 'economics', 'humanities', 'other'];
const STATUSES = ['Ready to apply', 'Applied', 'Online assessment', 'Interview', 'Offer', 'Rejected', 'Withdrawn'];
const FAMILY_NAMES = { 'quant-finance': 'Quant & finance', 'data-science': 'Data science', engineering: 'Engineering', consulting: 'Consulting', research: 'Research', 'policy-science-comms': 'Policy & science comms', 'patent-law': 'Patent law', software: 'Software', teaching: 'Teaching' };
const EXAMPLE_CV = `Alex Example
Fictional final-year demo CV, designed to match the maximum seven compatible sample roles.
BSc Physics, University of Exampleshire. Graduating 2027, predicted First.
Right to work in the UK without sponsorship.
github.com/alex-example

Experience
- Completed a research project using Python, statistics and SQL for data analysis of 40 hours of laboratory measurements.
- Applied problem solving to debug measurement errors and documented the findings through technical writing, checking units and references with attention to detail.
- Tutored six students in mechanics, practising communication and public speaking through weekly explanations and feedback.
- Managed the Astronomy Society budget in Excel and delivered a presentation on spending to 60 members.
- Produced science explainers for the student magazine, using writing and research to communicate physics to a general audience; created accompanying clips with video editing and managed social media posts.

Projects
- Used Python and MATLAB for modelling a three-body orbit with numerical methods and optimisation; wrote a technical report comparing simulated and measured results.
- Built a small Python and JavaScript data dashboard with Git version control, testing and documented algorithms.
- Developed a C++ sensor simulation for a systems engineering project, testing interfaces and documenting design requirements.
- Created a machine learning experiment and evaluated prediction uncertainty using probability and statistics.`;

let profile = store.get('profile', null);
let parsed = store.get('parsed', { experiences: [], projects: [] });
let apps = store.get('apps', []);
let passed = store.get('passed', []);
let passedHistory = store.get('passedHistory', []);
let extraRoles = store.get('extraRoles', []);
let families = [];
let results = [];
let excludedRoles = [];
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
  $('#f-rtw').value = p.rightToWork || '';
  if (p.preferences) fillPreferences(p.preferences);
  $('#f-skills').value = (p.skills || []).join(', ');
  $('#f-github').value = p.links?.github || '';
  $('#f-portfolio').value = p.links?.portfolio || '';
  document.querySelectorAll('#subjectTags input').forEach((i) => (i.checked = (p.subjectTags || []).includes(i.value)));
}
$('#roleInterests').innerHTML = Object.entries(FAMILY_NAMES).map(([id,name]) => `<label class="check"><input type="checkbox" value="${id}"> ${esc(name)}</label>`).join('');
function selectedInterests() { return [...document.querySelectorAll('#roleInterests input:checked')].map(input => input.value); }
function readPreferences() {
  return {interests:selectedInterests(), locationMode:$('#prefLocationMode').value,
    locations:$('#prefLocations').value.split(',').map(text => text.trim()).filter(Boolean),
    opportunityType:$('#prefOpportunity').value, source:$('#prefSource').value};
}
function fillPreferences(p) {
  $('#prefLocationMode').value = p.locationMode || 'uk';
  $('#prefLocations').value = (p.locations || []).join(', ');
  $('#prefLocationsLabel').hidden = $('#prefLocationMode').value !== 'locations';
  $('#prefOpportunity').value = p.opportunityType || 'auto';
  $('#prefSource').value = p.source || 'live';
  document.querySelectorAll('#roleInterests input').forEach(input => input.checked = (p.interests || []).includes(input.value));
}
function suggestInterests() {
  const skills = $('#f-skills').value.toLowerCase();
  const rules = {'software':['python','javascript','git','testing'],'data-science':['sql','statistics','data analysis','machine learning'],'engineering':['modelling','matlab','engineering'],'consulting':['communication','problem solving','excel'],'quant-finance':['probability','finance','statistics'],'research':['research','numerical methods'],'policy-science-comms':['writing','communication'],'patent-law':['technical writing','attention to detail'],'teaching':['tutoring','public speaking']};
  const suggestions = Object.entries(rules).map(([id,terms]) => [id,terms.filter(term => skills.split(',').map(s=>s.trim()).includes(term)).length]).filter(([,score])=>score>0).sort((a,b)=>b[1]-a[1]).slice(0,3).map(([id])=>id);
  document.querySelectorAll('#roleInterests input').forEach(input => input.checked = suggestions.includes(input.value));
}
function preferenceSummary(p) {
  const places = p.locationMode === 'remote' ? 'Remote (UK)' : p.locationMode === 'locations' ? (p.locations || []).join(' / ') : 'UK-wide';
  const interests = (p.interests || []).map(id => FAMILY_NAMES[id] || id).join(', ') || 'Interests suggested from your CV';
  return `${places} · ${interests} · ${{auto:'Opportunity type based on graduation stage',grad:'Graduate roles',internship:'Internships',placement:'Placements',insight:'Insight programmes'}[p.opportunityType || 'auto']}`;
}
$('#prefLocationMode').addEventListener('change', () => { $('#prefLocationsLabel').hidden = $('#prefLocationMode').value !== 'locations'; });
$('#suggestInterests').addEventListener('click', suggestInterests);
$('#editSearchPreferences').addEventListener('click', () => { show('profile'); $('#searchPreferences').scrollIntoView({behavior:'smooth',block:'center'}); });
function readForm() {
  return {
    name: $('#f-name').value.trim(), subject: $('#f-subject').value.trim(),
    gradYear: Number($('#f-gradYear').value) || null, classification: $('#f-class').value,
    rightToWork: $('#f-rtw').value,
    skills: $('#f-skills').value.split(',').map((s) => s.trim().toLowerCase()).filter(Boolean),
    subjectTags: [...document.querySelectorAll('#subjectTags input:checked')].map((i) => i.value),
    links: { github: $('#f-github').value.trim(), portfolio: $('#f-portfolio').value.trim(), linkedin: parsed.links?.linkedin || '' },
    experiences: parsed.experiences || [], projects: parsed.projects || [],
    preferences: readPreferences(),
  };
}
function setMsg(id, text, err) { const el = $(id); el.textContent = text; el.classList.toggle('err', Boolean(err)); }

async function readCv() {
  const cvText = $('#cvText').value;
  const btn = $('#readCv'); btn.disabled = true; setMsg('#readMsg', 'Reading your CV…');
  try {
    const { profile: p } = await api('/api/profile', { cvText });
    profile = null; results = []; liveJobs = []; reviewJobs = []; nextLivePage = null; liveSearchKey = ''; $('#loadMoreLiveJobs').hidden = true; store.set('profile', null);
    parsed = { experiences: p.experiences || [], projects: p.projects || [], links: p.links || {} };
    const current = readForm();
    fillForm({ ...p, subject: p.subject || current.subject, rightToWork: current.rightToWork });
    store.set('parsed', parsed); store.set('cv', cvText);
    if (!selectedInterests().length) suggestInterests();
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
    $('#f-rtw').value = 'UK';
    $('#showAll').checked = true;
    $('#prefSource').value = 'demo';
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
  if (p.preferences.interests.length > 3) return setMsg('#findMsg', 'Choose up to three role interests.', true);
  if (p.preferences.locations.length > 2 || (p.preferences.locationMode === 'locations' && !p.preferences.locations.length)) return setMsg('#findMsg', 'Enter one or two preferred locations, separated by a comma.', true);
  liveJobs = []; reviewJobs = []; results = []; nextLivePage = null; liveSearchKey = ''; $('#loadMoreLiveJobs').hidden = true;
  profile = p; store.set('profile', p);
  const btn = $('#findRoles'); btn.disabled = true; setMsg('#findMsg', 'Working out which roles suit you…');
  try { await runMatch(); setJobMode(p.preferences.source); setMsg('#findMsg', ''); show('swipe'); if (jobMode === 'live') await searchLiveJobs(); }
  catch (e) { setMsg('#findMsg', e.message, true); }
  finally { btn.disabled = false; }
});

async function runMatch() {
  const data = await api('/api/match', { profile, extraRoles });
  families = data.families; results = data.results; excludedRoles = data.excluded || [];
  $('#swipeSub').textContent = `You graduate in ${profile.gradYear}, so we're showing ${data.stage}-year opportunities meet all stated requirements for.`;
}



let liveJobs = [];
let reviewJobs = [];
let nextLivePage = null;
let liveSearchKey = '';
let autoCheckVersion = 0;
let autoCheckRunning = false;
let autoAttempted = new Set();
let liveSearchTotals = {fetched:0, unmet:0, unclear:0, skipped:0};
let jobMode = store.get('jobMode', 'demo') === 'live' ? 'live' : 'demo';
function setJobMode(mode) {
  jobMode = mode === 'live' ? 'live' : 'demo';
  if (jobMode === 'demo') { autoCheckVersion++; autoCheckRunning = false; }
  store.set('jobMode', jobMode);
  $('#demoModePanel').hidden = jobMode !== 'demo';
  $('#liveModePanel').hidden = jobMode !== 'live';
  $('#demoModeBtn').className = jobMode === 'demo' ? 'btn primary' : 'btn ghost';
  $('#liveModeBtn').className = jobMode === 'live' ? 'btn primary' : 'btn ghost';
  $('#demoModeBtn').setAttribute('aria-pressed', String(jobMode === 'demo'));
  $('#liveModeBtn').setAttribute('aria-pressed', String(jobMode === 'live'));
  $('#jobModeDescription').textContent = jobMode === 'live'
    ? 'Live: search real UK adverts and show only CV matches with supported eligibility.'
    : 'Demo: use the example student CV or a similar profile to match these fictional student and graduate roles.';
  $('#orderMode').disabled = jobMode === 'live';
  $('#showAll').disabled = jobMode === 'live';
  renderSwipe();
}
$('#demoModeBtn').addEventListener('click', () => setJobMode('demo'));
$('#liveModeBtn').addEventListener('click', () => { setJobMode('live'); if (profile && !liveJobs.length && !reviewJobs.length) searchLiveJobs(); });
setJobMode(jobMode);

async function searchLiveJobs(page = 1) {
  const button = $('#searchLiveJobs');
  const more = $('#loadMoreLiveJobs');
  button.disabled = true; more.disabled = true;
  setMsg('#liveJobsMsg', `Searching page ${page}…`);
  try {
    if (!profile?.gradYear) throw new Error('Review your CV profile and click Find my roles before searching.');
    const preferences = profile.preferences || {};
    $('#livePreferenceSummary').textContent = preferenceSummary(preferences);
    const searchProfile = profile;
    const searchKey = JSON.stringify({preferences, profile: searchProfile, aiMode});
    if (page > 1 && searchKey !== liveSearchKey) throw new Error('Your search or profile changed. Use Refresh matches to start a fresh search.');
    if (page === 1) {
      liveJobs = []; reviewJobs = []; nextLivePage = null; more.hidden = true;
      liveSearchKey = searchKey;
      autoCheckVersion++; autoCheckRunning = false; autoAttempted = new Set();
      $('#autoCheckStatus').textContent = ''; $('#checkMoreAdverts').hidden = true;
      liveSearchTotals = {fetched:0, unmet:0, unclear:0, skipped:0};
      $('#reviewLiveJobs').checked = false; renderSwipe();
    }
    const data = await api('/api/live-jobs', {profile: searchProfile, page});
    if (profile !== searchProfile || searchKey !== liveSearchKey) throw new Error('Your profile or mode changed. Search again to refresh eligibility.');
    if (typeof data.fullAdvertReadsAvailable === 'boolean') { fullAdvertReadsAvailable = data.fullAdvertReadsAvailable; fullAdvertReadNotice = data.fullAdvertReadNotice || ''; }
    const unique = jobs => [...new Map(jobs.map(job => [job.role.id,job])).values()];
    liveJobs = unique([...liveJobs, ...(data.jobs || []).filter(job => job.tier === 'eligible' && job.role?.id)]);
    const matchedIds = new Set(liveJobs.map(job => job.role.id));
    reviewJobs = unique([...reviewJobs, ...(data.reviewJobs || [])]).filter(job => !matchedIds.has(job.role.id));
    $('#reviewLiveCount').textContent = `(${reviewJobs.length})`;
    nextLivePage = data.nextPage;
    more.hidden = !nextLivePage;
    liveSearchTotals.fetched += data.fetchedCount || 0;
    liveSearchTotals.unmet += data.unmetCount || 0;
    liveSearchTotals.unclear += data.unclearCount || 0;
    liveSearchTotals.skipped += data.skippedCount || 0;
    const total = Number.isFinite(data.totalAvailable) ? `Adzuna reports ${data.totalAvailable.toLocaleString()} results for this search. ` : '';
    setMsg('#liveJobsMsg', `${total}${data.queryCount > 1 ? `Combined ${data.queryCount} searches for your selected interests and locations. ` : ''}Fetched ${liveSearchTotals.fetched} adverts across ${page} batch${page === 1 ? '' : 's'}: ${liveJobs.length} unique matches; ${liveSearchTotals.unmet} failed recognised criteria; ${liveSearchTotals.unclear} need review; ${liveSearchTotals.skipped} had unsupported links. ${nextLivePage ? 'Load more jobs to keep searching.' : 'No further pages for this search. Edit your preferences to broaden roles or locations.'}`);
    renderSwipe();
    if (!autoCheckRunning) autoCheckAdverts();
  } catch (error) { setMsg('#liveJobsMsg', error.message, true); }
  finally { button.disabled = false; more.disabled = false; }
}
$('#searchLiveJobs').addEventListener('click', () => searchLiveJobs());
$('#loadMoreLiveJobs').addEventListener('click', () => { if (nextLivePage) searchLiveJobs(nextLivePage); });

/* ---------- swipe deck ---------- */
const byFit = (a, b) => b.fit - a.fit || b.role.competitiveness - a.role.competitiveness;
function queue() {
  const done = new Set([...passed, ...apps.map((a) => a.role.id)]);
  const showAll = $('#showAll').checked;
  if (jobMode === 'live') return [...liveJobs, ...($('#reviewLiveJobs').checked ? reviewJobs : [])].filter(j => !done.has(j.role.id));
  const list = results.filter((r) => r.tier === 'eligible' && !done.has(r.role.id) && (r.inFamily || showAll));
  return $('#orderMode').value === 'fit' ? list.sort(byFit) : list;
}
const daysLeft = (iso) => Math.ceil((new Date(iso) - Date.now()) / 864e5);
const dots = (n) => `<span class="dots" aria-label="${n} out of 5">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= n ? 'on' : ''}"></i>`).join('')}</span>`;

function cardHTML(r) {
  const ro = r.role;
  if (ro.source === 'Adzuna') {
    const summary = String(ro.summary || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    const salary = ro.salaryMin ? `£${Number(ro.salaryMin).toLocaleString('en-GB')}${ro.salaryMax && ro.salaryMax !== ro.salaryMin ? ` – £${Number(ro.salaryMax).toLocaleString('en-GB')}` : ''} / year` : 'Salary not supplied';
    const evidence = r.hardPasses.filter(t => !t.startsWith('Local screening')).slice(0, 3);
    return `<span class="stamp l">PASS</span><span class="stamp r">SAVE</span>
      <div class="liveCardTop"><span class="liveEyebrow">LIVE OPPORTUNITY · ADZUNA</span><span class="liveMatch">${ro.eligibilityUnverified ? (ro.fullRead ? 'Full advert · needs review' : ro.readFailed ? 'Website unavailable' : 'Requirements incomplete') : ro.matchingMode === 'rules' ? 'Free CV screening' : 'Claude screening'}</span></div>
      <h2 class="liveTitle">${esc(ro.title)}</h2><p class="liveEmployer">${esc(ro.employer || 'Employer not supplied')}</p>
      <div class="liveFacts"><span>⌖ ${esc(ro.location || 'Location not supplied')}</span><span>${esc(salary)}</span>${ro.posted ? `<span>Posted ${esc(ro.posted)}</span>` : ''}</div>
      <div class="liveSection"><h3>${ro.eligibilityUnverified ? 'Eligibility needs review' : 'Why it fits your CV'}</h3>${ro.eligibilityUnverified ? `<p class="liveSummary">${ro.fullRead ? 'The full advert has been read, but some requirements need your review.' : ro.readFailed ? 'The website could not be read automatically. Open the original advert or paste its description to check it.' : 'Full-description checks run in batches. This preview does not contain enough requirements to confirm eligibility.'}</p>` : ''}<div class="chips">${r.matched.map(skill => `<span class="chip ok">✓ ${esc(skill)}</span>`).join('')}</div><ul class="why">${evidence.map(t => `<li class="ok">${esc(t)}</li>`).join('')}</ul></div>
      <div class="liveSection"><h3>The opportunity</h3><p class="liveSummary">${esc(summary.slice(0, 420))}${summary.length > 420 ? '…' : ''}</p></div>
      <div class="liveFooter"><button class="btn primary" type="button" data-read-advert="${esc(ro.id)}">${fullAdvertReadsAvailable ? 'Read & check full advert' : 'Paste full advert to check'}</button>${ro.applyUrl?.startsWith('https://') ? `<a class="btn ghost" href="${esc(ro.applyUrl)}" target="_blank" rel="noopener noreferrer">Read full advert ↗</a>` : ''}<span>Swipe right to save · no uses spent</span></div>
      <p class="liveCaveat">${ro.eligibilityUnverified ? 'This is not a confirmed eligible match.' : ro.matchingMode === 'rules' ? 'Local rules check recognised criteria only.' : 'AI screening is an estimate.'} Confirm full requirements and closing date with the employer.</p>`;
  }
  if (ro.eligibilityUnverified) return `<span class="stamp l">PASS</span><span class="stamp r">SAVE</span><div><span class="pill">Live advert</span><span class="pill">Eligibility unverified</span></div><h2>${esc(ro.title)}</h2><p class="emp">${esc(ro.employer)} · ${esc(ro.location || '')}</p><p>${esc(ro.summary || 'No description supplied.')}</p><ul class="why"><li>Source: Adzuna job advertisement</li><li>Skills, eligibility and closing date must be checked on the original listing.</li></ul>${ro.applyUrl?.startsWith('https://') ? `<p><a href="${esc(ro.applyUrl)}" target="_blank" rel="noopener noreferrer">Read full job advert ↗</a></p>` : ''}<p class="deadline">Swipe right to save to Applications. You can draft an application after verifying the requirements.</p>`;
  const typeLabel = ro.type === 'grad' ? 'Graduate role' : ro.type === 'spring-week' ? 'Spring week' : 'Internship';
  const hard = [...r.hardPasses.map((t) => `<li class="ok">${esc(t)}</li>`)].join('');
  const chips = [...r.matched.map((s) => `<span class="chip ok">${esc(s)}</span>`), ...r.missingRequired.map((s) => `<span class="chip miss">needs ${esc(s)}</span>`), ...r.missingPreferred.map((s) => `<span class="chip">nice: ${esc(s)}</span>`)].join('');
  const d = daysLeft(ro.closes);
  const deadline = ro.closes ? `Closes ${esc(ro.closes)} (${d > 0 ? `in ${d} days` : 'closed'}).` : 'Closing date not supplied.';
  return `<span class="stamp l">PASS</span><span class="stamp r">LIKE</span>
    ${ro.sample ? '<span class="sampleTag" title="Illustrative listing, not a live vacancy">Sample listing</span>' : ''}
    <div><span class="pill ${r.tier}">${r.tier === 'eligible' ? (ro.matchingMode === 'rules' ? 'CV match · local rules' : 'Eligible') : 'Stretch'}</span><span class="pill ${r.category}">${r.category}</span><span class="pill">${typeLabel}</span></div>
    <h2>${esc(ro.title)}</h2>
    <p class="emp">${esc(ro.employer)} · ${esc(ro.location || '')}</p>
    <p>${esc(ro.summary || '')}</p>
    <div class="meter">Competitiveness (estimate) ${dots(ro.competitiveness)} · Fit ${r.fit}%</div>
    <ul class="why">${hard}</ul>
    <div class="chips">${chips}</div>
    <p class="deadline">${deadline} Always confirm the criteria and deadline on the employer's own page.</p>`;
}

function renderSwipe() {
  $('#families').innerHTML = families.length ? '<span class="famLabel">Suggested for you (hover for why):</span>' + families.map((f) => `<span class="fam" title="${esc(f.why)}">${esc(FAMILY_NAMES[f.id] || f.id)}</span>`).join('') : '';
  const q = queue();
  const deck = $('#deck');
  $('#swipeTitle').textContent = jobMode === 'live' ? `${q.length} live role${q.length === 1 ? '' : 's'} to look at` : (profile ? `${q.length} role${q.length === 1 ? '' : 's'} to look at` : 'Your matches');
  $('#swipeSub').textContent = jobMode === 'live' ? 'CV matches based on recognised advert criteria. Free screening has limited coverage; confirm full requirements with the employer.' : (profile ? `Showing suggested roles for your graduation year ${profile.gradYear}.` : '');
  if (jobMode === 'demo' && !profile) { deck.innerHTML = '<p class="empty">Start with your profile, then your matches will appear here.</p>'; setBtns(false); return; }
  if (jobMode === 'demo' && !results.length) {
    deck.innerHTML = '<div class="card"><h3>No eligible demo roles for this profile</h3><p>The sample deck is limited. No roles meet all the requirements based on your reviewed profile. Check the extracted CV skills, graduation year, subject areas and work authorisation under Profile. Add only details supported by your experience.</p><details><summary>Why the sample roles were excluded</summary><ul>' + excludedRoles.map(r => `<li><strong>${esc(r.title)}</strong>: ${r.reasons.map(esc).join('; ')}</li>`).join('') + '</ul></details></div>';
    setBtns(false); return;
  }
  if (!q.length) { deck.innerHTML = jobMode === 'live' ? `<p class="empty">${reviewJobs.length ? `No confirmed matches in this batch. Tick “Review adverts needing manual checks” above to inspect ${reviewJobs.length} adverts. They are not confirmed eligible.` : 'Use Refresh matches to search from your saved preferences, or choose Edit preferences.'}</p>` : (results.some(r => !passed.includes(r.role.id) && !apps.some(a => a.role.id === r.role.id)) ? '<p class="empty">Eligible roles exist outside your suggested areas. Tick “Show eligible roles outside my suggested areas” to view them.</p>' : '<p class="empty">You have seen all current eligible demo matches. Check Applications or revisit your passed roles.</p>'); setBtns(false); return; }
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
    if (dir === 'right') { if (r.role.eligibilityUnverified) { apps.push({id:'a'+Date.now(),role:r.role,tier:'unverified',category:'unverified',status:'Saved — check eligibility',docs:null,error:null,addedAt:new Date().toISOString()}); saveApps(); toast('Saved to Applications. Check the full advert before drafting.'); } else addApp(r); } else { passed.push(r.role.id); store.set('passed', passed); passedHistory = [{role:r.role, passedAt:new Date().toISOString()}, ...passedHistory.filter(x => x.role.id !== r.role.id)]; store.set('passedHistory', passedHistory); }
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
  const app = { id: 'a' + Date.now(), role: r.role, tier: r.tier, category: r.category, status: 'Saved — ready to draft', docs: null, error: null, addedAt: new Date().toISOString() };
  apps.push(app); saveApps(); toast('Saved to Applications. Choose Draft application when ready; saving uses no generations.');
}
async function refreshGenerationQuota() {
  const element = $('#generationQuota');
  try {
    const quota = await api('/api/generation-quota');
    const remaining = quota.remaining;
    const limit = Math.max(0, Number(quota.limit) || 0);
    const full = limit > 0 && remaining === limit;
    const mood = remaining === 0 ? ['😭', 'Out of juice!'] : remaining === 1 ? ['😱', 'Last chance to impress!'] : full ? ['🔋', 'Fully charged, bestie!'] : ['💖', 'Still got some spark!'];
    element.dataset.remaining = String(remaining);
    element.dataset.limit = String(limit);
    element.querySelector('.quotaEmoji').textContent = mood[0];
    element.querySelector('.quotaTitle').textContent = mood[1];
    element.querySelector('.quotaCount').textContent = `${remaining}/${limit}`;
    element.querySelector('.quotaSubtitle').textContent = remaining === 0 ? 'Your free generations reset tomorrow' : 'Application generations remaining today · resets tomorrow';
    element.querySelector('.quotaFill').style.width = `${limit ? Math.max(0, Math.min(100, remaining / limit * 100)) : 0}%`;
    return quota;
  } catch {
    element.querySelector('.quotaTitle').textContent = 'Could not check your energy';
    element.querySelector('.quotaSubtitle').textContent = 'Please refresh to try again.';
    return null;
  }
}
async function generate(app) {
  const quota = await refreshGenerationQuota();
  if (quota && quota.remaining === 0) {
    app.status = 'Daily generation limit reached';
    app.error = 'You have used all your free generations today. Try again tomorrow.';
    saveApps();
    return;
  }
  if (quota && quota.remaining === 1 && !confirm('This is your last free application generation today. Continue?')) {
    app.status = 'Saved — ready to draft';
    saveApps();
    return;
  }
  app.status = 'Drafting'; app.error = null; saveApps();
  try {
    app.docs = await api('/api/generate', { profile, role: app.role });
    app.status = 'Ready to apply'; toast(`Pack ready: ${app.role.title}`);
  } catch (e) { app.status = 'Draft failed'; app.error = e.message; }
  saveApps();
  await refreshGenerationQuota();
}
function saveApps() { store.set('apps', apps); $('#appCount').textContent = apps.length; if (!$('#view-tracker').hidden) renderTracker(); }

function renderTracker() {
  const list = $('#trackerList');
  renderPassedHistory();
  refreshGenerationQuota();
  if (!apps.length) { list.innerHTML = '<p class="empty">Nothing here yet. Swipe right on a role to save it here.</p>'; return; }
  const sorted = [...apps].sort((a, b) => (a.role.closes ? new Date(a.role.closes).getTime() : Infinity) - (b.role.closes ? new Date(b.role.closes).getTime() : Infinity));
  list.innerHTML = sorted.map((a) => {
    const d = a.role.closes ? daysLeft(a.role.closes) : null;
    const opts = [...new Set([a.status, ...STATUSES])].filter((s) => s !== 'Drafting' && s !== 'Draft failed' || s === a.status).map((s) => `<option ${s === a.status ? 'selected' : ''}>${esc(s)}</option>`).join('');
    return `<div class="card app" data-id="${esc(a.id)}">
      <div><h3>${esc(a.role.title)}</h3><div class="meta">${esc(a.role.employer)} · ${esc(a.category)} · ${a.role.closes ? 'closes '+esc(a.role.closes) : 'closing date unverified'} <span class="${d !== null && d <= 7 ? 'urgent' : ''}">${d === null ? '' : '('+(d > 0 ? d + ' days left' : 'closed')+')'}</span></div>${a.error ? `<div class="hint err">${esc(a.error)}</div>` : ''}</div>
      <div class="actions">
        ${a.status === 'Drafting' ? '<span class="hint">Drafting…</span>' : a.status === 'Draft failed' ? '<button class="btn" data-act="retry">Retry</button>' : `<select data-act="status" aria-label="Status">${opts}</select>${a.docs ? '<button class="btn" data-act="open">Open pack</button>' : '<button class="btn" data-act="draft">Draft application · 1 use</button>'}`}
        ${a.role.applyUrl && a.role.applyUrl.startsWith("https://") ? `<a class="btn ghost" href="${esc(a.role.applyUrl)}" target="_blank" rel="noopener noreferrer">View job ↗</a>` : ""}<button class="btn ghost" data-act="remove" title="Remove from tracker">Remove</button>
      </div></div>`;
  }).join('');
}
function renderPassedHistory() {
  $('#passedCount').textContent = passedHistory.length;
  $('#passedList').innerHTML = passedHistory.length ? passedHistory.map((entry, i) =>
    `<div class="card app"><div><h3>${esc(entry.role.title)}</h3><p class="meta">${esc(entry.role.employer)} · ${esc(entry.role.location || '')} · Swiped left ${esc(entry.passedAt.slice(0,10))}</p></div><div class="actions">${entry.role.applyUrl?.startsWith('https://') ? `<a class="btn ghost" target="_blank" rel="noopener noreferrer" href="${esc(entry.role.applyUrl)}">View job ↗</a>` : ''}<button class="btn ghost" data-restore-passed="${i}">Restore to deck</button></div></div>`).join('') : '<p class="hint">No passed jobs recorded yet. Future left swipes will appear here.</p>';
}
$('#passedList').addEventListener('click', e => {
  const btn = e.target.closest('[data-restore-passed]');
  if (!btn) return;
  const item = passedHistory[Number(btn.dataset.restorePassed)];
  if (!item) return;
  passed = passed.filter(id => id !== item.role.id);
  store.set('passed', passed);
  passedHistory = passedHistory.filter(x => x.role.id !== item.role.id);
  store.set('passedHistory', passedHistory);
  if (item.role.source === 'Adzuna') toast('Search live jobs again to recheck this role against your current CV.');
  if (item.role.source === 'Adzuna') setJobMode('live'); else setJobMode('demo');
  renderPassedHistory();
  if (item.role.source !== 'Adzuna') toast('Job restored to swipe deck');
});
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
  try {
    const response = await api('/api/workspace');
    const serverData = response.data || {};
    const legacy = {};
    Object.keys(localStorage).filter(k => k.startsWith('hr.')).forEach(k => {
      try { legacy[k.slice(3)] = JSON.parse(localStorage.getItem(k)); } catch {}
    });
    store.data = Object.keys(serverData).length ? serverData : legacy;
    if (!Object.keys(serverData).length && Object.keys(legacy).length) {
      const res = await fetch('/api/workspace', {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || ''}, body:JSON.stringify(legacy)});
      if (!res.ok) throw new Error('Could not migrate existing browser data');
    }
    Object.keys(localStorage).filter(k => k.startsWith('hr.')).forEach(k => localStorage.removeItem(k));
    profile = store.get('profile', null);
    parsed = store.get('parsed', {experiences:[], projects:[]});
    apps = store.get('apps', []);
    passed = store.get('passed', []);
    passedHistory = store.get('passedHistory', []);
    extraRoles = store.get('extraRoles', []);
    setJobMode(store.get('jobMode', 'demo'));
    store.ready = true;
  } catch(e) {
    console.error('Workspace loading failed', e);
    alert('Could not load your private workspace. Please reload before making changes.');
    return;
  }
  $('#appCount').textContent = apps.length;
  await refreshGenerationQuota();
  try {
    const { mode, serverKeyAvailable, fullAdvertReadsAvailable: canRead, fullAdvertReadNotice: readNotice } = await api('/api/status');
    fullAdvertReadsAvailable = canRead !== false; fullAdvertReadNotice = readNotice || '';
    $('#aiMode option[value="server"]').hidden = !serverKeyAvailable;
    $('#modeBadge').textContent = mode === 'claude' ? 'AI: Claude' : 'AI: Templates';
    $('#modeBadge').title = mode === 'claude' ? 'Application writing uses Claude; job source is selected separately.' : 'Application writing uses templates; job source is selected separately.';
  } catch { $('#modeBadge').textContent = 'Server offline'; }
  const cv = store.get('cv', ''); if (cv) $('#cvText').value = cv;
  if (profile) {
    fillForm(profile);
    try { await runMatch(); } catch { /* user can press Find my roles again */ }
  }
})();


$('#aiMode').addEventListener('change', () => {
  $('#personalKeyPanel').hidden = $('#aiMode').value !== 'personal';
});
$('#applyApiOptions').addEventListener('click', async () => {
  const selected = $('#aiMode').value;
  const key = $('#anthropicKey').value.trim();
  if (selected === 'personal' && !key.startsWith('sk-ant-')) {
    setMsg('#apiOptionsMsg', 'Enter an Anthropic key or select free mode.', true); return;
  }
  aiMode = selected; personalApiKey = selected === 'personal' ? key : '';
  $('#anthropicKey').value = '';
  liveJobs = []; reviewJobs = []; nextLivePage = null; liveSearchKey = ''; $('#loadMoreLiveJobs').hidden = true; renderSwipe();
  try {
    const {mode} = await api('/api/status');
    $('#modeBadge').textContent = mode === 'claude' ? 'AI: Claude' : 'AI: Templates';
    $('#modeBadge').title = mode === 'claude' ? 'Optional Claude is enabled for this tab.' : 'Free local matching and template writing.';
    setMsg('#apiOptionsMsg', mode === 'claude' ? 'Claude selected. API charges may apply; the key will be checked on the next AI request.' : 'Free mode enabled. No paid AI calls.');
  } catch (error) { setMsg('#apiOptionsMsg', error.message, true); }
});

$('#claudeUpgrade').addEventListener('click', () => {
  show('profile');
  $('#apiOptions').open = true;
  $('#apiOptions').scrollIntoView({behavior: 'smooth', block: 'start'});
  $('#aiMode').focus({preventScroll: true});
});

$('#reviewLiveJobs').addEventListener('change', renderSwipe);

let detailsRole = null;
let detailsProfile = null;
let detailsVersion = 0;
async function checkFullAdvert(text) {
  const version = ++detailsVersion;
  const role = detailsRole;
  const checkedProfile = detailsProfile;
  $('#checkJobDetails').disabled = true;
  $('#jobDetailsStatus').textContent = text === undefined ? 'Reading the original advert…' : 'Checking the full description…';
  $('#jobDetailsReasons').innerHTML = '';
  try {
    const data = await api('/api/job-details', {role, profile: checkedProfile, ...(text === undefined ? {} : {text})});
    if (version !== detailsVersion || !$('#jobDetailsDialog').open) return;
    if (profile !== checkedProfile) throw new Error('Your profile changed. Close this window and check the role again.');
    $('#jobDetailsText').value = data.description;
    const labels = {matched:'Recognised requirements match your profile.', ineligible:'Your profile does not meet the recognised requirements.', unverified:'Description loaded; eligibility still needs review.'};
    $('#jobDetailsStatus').textContent = `${labels[data.outcome]} Source: ${data.descriptionSource}. Confirm the full criteria with the employer.`;
    $('#jobDetailsReasons').innerHTML = (data.reasons || []).map(reason => `<li>${esc(reason)}</li>`).join('') + (data.mentionedSkills?.length ? `<li>Skills mentioned in advert: ${data.mentionedSkills.map(esc).join(', ')}. Mentions may include preferred skills.</li><li>Supported by your profile: ${data.supportedSkills.map(esc).join(', ') || 'None recognised'}.</li>` : '');
    applyFullCheck(role, data);
    renderSwipe();
  } catch (error) {
    if (version === detailsVersion) $('#jobDetailsStatus').textContent = error.message;
  } finally {
    if (version === detailsVersion) $('#checkJobDetails').disabled = false;
  }
}
$('#deck').addEventListener('click', event => {
  const button = event.target.closest('[data-read-advert]');
  if (!button) return;
  const result = [...liveJobs, ...reviewJobs].find(job => job.role.id === button.dataset.readAdvert);
  if (!result) return;
  detailsRole = result.role; detailsProfile = profile;
  $('#jobDetailsTitle').textContent = result.role.title;
  $('#jobDetailsText').value = '';
  $('#originalJobLink').href = result.role.applyUrl;
  $('#jobDetailsDialog').showModal();
  if (fullAdvertReadsAvailable) checkFullAdvert();
  else { $('#jobDetailsStatus').textContent = fullAdvertReadNotice; $('#jobDetailsReasons').innerHTML = ''; $('#checkJobDetails').disabled = false; }
});
$('#closeJobDetails').addEventListener('click', () => { detailsVersion++; $('#jobDetailsDialog').close(); });
$('#jobDetailsDialog').addEventListener('cancel', () => { detailsVersion++; });
$('#checkJobDetails').addEventListener('click', () => checkFullAdvert($('#jobDetailsText').value));


function applyFullCheck(role, data) {
  if (data.outcome === 'matched' && data.evaluation) {
    data.evaluation.role.fullRead = true;
    liveJobs = [data.evaluation, ...liveJobs.filter(job => job.role.id !== role.id)];
    reviewJobs = reviewJobs.filter(job => job.role.id !== role.id);
  } else if (data.outcome === 'ineligible') {
    liveJobs = liveJobs.filter(job => job.role.id !== role.id);
    reviewJobs = reviewJobs.filter(job => job.role.id !== role.id);
  } else {
    reviewJobs = reviewJobs.map(job => job.role.id === role.id ? {...job, role:{...job.role, fullRead:true, descriptionSource:data.descriptionSource, summary:data.description}} : job);
  }
  $('#reviewLiveCount').textContent = `(${reviewJobs.length})`;
}
async function autoCheckAdverts() {
  if (!fullAdvertReadsAvailable) { $('#autoCheckStatus').textContent = fullAdvertReadNotice + ' No advert-reading attempts or pack generations have been spent.'; $('#checkMoreAdverts').hidden = true; return; }
  if (autoCheckRunning || !profile || !liveSearchKey) return;
  const batch = reviewJobs.filter(job => !autoAttempted.has(job.role.id)).slice(0,5);
  if (!batch.length) { $('#checkMoreAdverts').hidden = true; return; }
  autoCheckRunning = true;
  const version = autoCheckVersion;
  const searchKey = liveSearchKey;
  const checkedProfile = profile;
  let index = 0, completed = 0, matched = 0, excluded = 0, unreadable = 0, limited = false;
  $('#checkMoreAdverts').hidden = true;
  function current() { return version === autoCheckVersion && searchKey === liveSearchKey && checkedProfile === profile; }
  function progress() { $('#autoCheckStatus').textContent = `Reading full adverts: ${completed}/${batch.length} checked · ${completed-unreadable} descriptions read · ${matched} matched · ${excluded} excluded · ${unreadable} could not be read. No pack-generation uses spent.`; }
  progress();
  async function worker() {
    while (index < batch.length && current() && !limited) {
      const role = batch[index++].role;
      autoAttempted.add(role.id);
      try {
        const data = await api('/api/job-details', {role, profile:checkedProfile});
        if (!current()) return;
        applyFullCheck(role,data);
        if (data.outcome === 'matched') matched++;
        if (data.outcome === 'ineligible') excluded++;
      } catch (error) {
        if (!current()) return;
        if (/allowance|limit reached/i.test(error.message)) limited = true;
        unreadable++;
        reviewJobs = reviewJobs.map(job => job.role.id === role.id ? {...job, role:{...job.role, readFailed:true}} : job);
      }
      completed++; progress(); renderSwipe();
    }
  }
  await Promise.all([worker(),worker()]);
  if (!current()) return;
  autoCheckRunning = false;
  const remaining = reviewJobs.filter(job => !autoAttempted.has(job.role.id)).length;
  $('#checkMoreAdverts').hidden = !remaining || limited;
  $('#autoCheckStatus').textContent += limited ? ' Daily checking allowance reached; paste descriptions to continue.' : ` ${remaining ? `${remaining} more can be checked with “Check next 5 full adverts”.` : 'Batch complete.'} ${reviewJobs.length} adverts still need review.`;
}
$('#checkMoreAdverts').addEventListener('click', autoCheckAdverts);
