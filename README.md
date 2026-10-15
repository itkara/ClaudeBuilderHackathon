# Hireationship

**Tired of being ghosted? Match with employers ready to commit.**

Most job platforms start from the jobs and leave you to work out whether you fit. Hireationship starts from *you*: it works out which roles you are actually eligible for, ranks them by how competitive they are, and lets you swipe. For every role you swipe right on, it writes the application: a tailored CV, a cover letter if the employer wants one, a checklist of the supporting documents you will need, and a plan for closing any gaps before the deadline.

Built for the **Better Student Life** track.

## How it works

1. **You.** Paste your base CV and confirm a few details (graduation year, classification, right to work, subject areas).
2. **Matching.** Roles are sorted into *eligible* (you meet everything), *stretch* (a close match) or *hidden* (you fail a hard requirement). Each eligible role is labelled **reach / target / safe** by comparing how strong a fit you are with how competitive the role is, and the deck is ordered most competitive first (or best fit first, your choice).
3. **Swipe.** Left = not for me. Right = draft my application. Drag the card, use the buttons, or press the arrow keys.
4. **Application pack** (right-swipes only):
   - a CV reordered and reworded for that role, using only what is in your real CV
   - a cover letter, if the employer asks for one
   - supporting documents beyond the basics (GitHub, portfolio, writing sample, transcript…), marked *you have this* or *to prepare*
   - a gap plan: concrete things to do before the deadline to close what is missing
   - a trace showing which line of your CV each claim came from
5. **Applications.** A tracker sorted by closing date, with status per application and the exact documents drafted for each.

## Design decisions worth knowing

- **Eligibility is deterministic, not guessed.** Hard requirements (stage, classification, subject, right to work, deadline) and required skills are checked by plain code in [`lib/matcher.js`](lib/matcher.js), with tests. Every card shows why it is there. Claude is used for the parts that need language: reading the CV, suggesting role families beyond the obvious, extracting requirements from pasted job descriptions, and writing the pack.
- **Stage comes from graduation year**, not "year 2 / year 3", because integrated masters and placement years make year numbers ambiguous.
- **The tailoring never invents experience.** The prompt forbids it, missing skills go into the gap plan instead of being hidden behind vague wording, and the trace tab lets you check every claim.
- **Competitiveness is an estimate.** There is no public acceptance-rate data, so each role carries a 1-5 estimate and the UI says so.

## Run it

Requires Node 18 or newer. No dependencies to install.

```bash
cp .env.example .env      # optional: add ANTHROPIC_API_KEY for Claude mode
npm start                 # http://localhost:3000
npm test
```

- **Claude mode** (API key set): CV reading, role-family suggestions, job-description import and the application pack are all written by Claude. The key stays on the server.
- **Demo mode** (no key): the whole flow works offline using rule-based matching and templated writing built from your own CV lines. Good for trying the app, not representative of the writing quality.

Your profile, swipes and applications are stored in your browser's local storage only.

## Honest limitations

- The roles in `data/roles.json` are **illustrative samples** with fictional employers, not live vacancies. Real listings need a data source (see roadmap). Each card says "Sample listing" and always tells you to confirm criteria and deadlines on the employer's own page.
- You can add a real role today by pasting a job description (Claude mode): it is extracted, checked against your profile and slotted into your deck.
- Local-storage persistence is per browser. There are no accounts.

## Roadmap

- Live role feed (employer career pages or an approved jobs API) in place of the sample file
- Upload CV as PDF/DOCX
- Export packs as .docx / PDF
- Per-role deadline reminders
- Optional accounts so the tracker follows you across devices

## Project layout

```
server.js          HTTP server and API routes (no framework)
lib/matcher.js     eligibility, reach/target/safe, ranking (tested)
lib/claude.js      Anthropic API calls and prompts
lib/demo.js        offline fallback used when no API key is set
data/roles.json    sample roles
public/            single-page front end (vanilla JS)
test/              unit tests (node --test)
```
