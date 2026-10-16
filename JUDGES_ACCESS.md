# Judge access and invitation links — Hireationship

Hireationship uses invitation-only accounts to protect limited API credits. Each invitation creates one regular user account with the normal daily generation allowance.

## First-time setup (only once)

1. Merge [PR #11](https://github.com/itkara/ClaudeBuilderHackathon/pull/11) into `main`.
2. Open **PythonAnywhere → Consoles → Bash**.
3. Run:

```bash
cd ~/ClaudeBuilderHackathon
workon hireationship-env
git pull --ff-only origin main
python manage.py migrate
python manage.py check
```

4. Open **PythonAnywhere → Web → Reload** to activate the registration page.

## Generate a private judge invitation

In the same PythonAnywhere Bash console, run:

```bash
cd ~/ClaudeBuilderHackathon
python manage.py create_invite --days 30
```

The command prints a private link resembling:

```text
https://itkara.pythonanywhere.com/register/?invite=YOUR_UNIQUE_TOKEN
```

**Copy the entire URL and send it privately to the judge.** The token is shown only once. Each link can be used by **one person only**, and a judge link created with `--days 30` expires after **30 days**.

For another judge, repeat:

```bash
python manage.py create_invite --days 30
```

There is **no need to migrate or reload** each time you create another invitation.

Do **not** paste real invitation links into the public GitHub repository, README, issues or screenshots. Consider generating a spare link for yourself and testing registration in a private browsing window before sharing judges' links.

## Enable “Request an invitation” on the login page

To let visitors email you requesting access:

```bash
cd ~/ClaudeBuilderHackathon
nano .env
```

Add this line, replacing the placeholder with an inbox you check:

```dotenv
HIREATIONSHIP_INVITE_CONTACT_EMAIL=your-contact-email@example.com
```

Save in nano with **Ctrl+O**, **Enter**, then **Ctrl+X**. Keep existing secrets and API keys unchanged. Reload from **PythonAnywhere → Web → Reload**.

The login page will then show **Request an invitation**. Clicking it opens the visitor's email application with a prefilled message; no requests are stored on the server. Without this environment setting, the page instead asks visitors to contact the project team or organisers.

## Respond to an access request

1. Read the incoming email.
2. Run `python manage.py create_invite` (defaults to **7 days**) or `python manage.py create_invite --days 30` for a judge.
3. Copy the printed private link and reply with it.
4. The recipient opens the link, chooses a username and password, and can then sign in.

Suggested reply:

> **Subject: Your invitation to Hireationship**
>
> Hi,
>
> Thanks for your interest in Hireationship! You can create an account using this private registration link:
>
> [PASTE UNIQUE LINK HERE]
>
> The invitation can be used once and expires in [7/30] days. Once registered, you can explore the graduate job matching and application-generation features. Daily generation limits apply during the hackathon preview.
>
> Please let me know if you have trouble accessing the app.
>
> Best wishes

## Troubleshooting

- `Unknown command: 'create_invite'`: PR #11 has not been merged/pulled onto PythonAnywhere yet.
- `no such table: matching_invitation`: run `python manage.py migrate`.
- No “Request an invitation” link: check `HIREATIONSHIP_INVITE_CONTACT_EMAIL` is set in `.env`, then reload the Web app.
- An invitation is invalid: it may have expired or already been redeemed; generate a new one.

**Note:** This is manual invitation approval, not open registration or automatic email delivery. Never share your `.env` file or API keys.
