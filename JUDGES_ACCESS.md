# Judge access — Hireationship

Hireationship uses invitation-only accounts so that API credits cannot be consumed through unrestricted public sign-ups.

## Recommended hackathon submission

Provide the judges with a **private single-use registration link for each judge**, or ask the organisers how many accounts they require. Do not publish invitation links in a public repository or screenshot: each link can only be redeemed once.

Generate a link on PythonAnywhere after deployment:

```bash
cd ~/ClaudeBuilderHackathon
python manage.py create_invite --days 30
```

Send the printed URL privately to a judge or organiser. Run the command again for each additional judge. The link expires after 30 days and creates a regular non-admin user. For public visitors, the login page can offer **Request an invitation** via email, if configured.

## Enable the access-request link

In the PythonAnywhere `.env` file, set:

```dotenv
HIREATIONSHIP_INVITE_CONTACT_EMAIL=your-contact-email@example.com
```

Replace the example with an inbox you actually check. Restart/reload the web app. The login page will display **Request an invitation**, which opens the visitor's email client with a prefilled request. No request data is stored in Hireationship. If the environment variable is missing, the page tells visitors to contact the team or organisers instead.

## Approving a request

1. Check the request in your email inbox.
2. Run `python manage.py create_invite` on PythonAnywhere.
3. Reply privately with the printed URL.
4. The invitee chooses their own username/password, and the standard free daily generation quota applies.

There is no automated email delivery, no payment tier, and no unrestricted sign-up. Email-client-based requests require the visitor to have an email app configured.
