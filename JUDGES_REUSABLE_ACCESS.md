# Hackathon judge access

The reusable judge link is included as a clickable link in the submission PDF. It is not displayed on the public login page or stored as plaintext in this repository.

## First deployment

1. Merge this PR, then on PythonAnywhere Bash run:
   cd ~/ClaudeBuilderHackathon
   git pull --ff-only origin main
   workon hireationship-env
   python manage.py migrate
   python manage.py check
2. In PythonAnywhere Web, click Reload.
3. Open the judge link from the PDF in a private browser window. It should show an invitation registration form.
4. If you have not already created a Django superuser, run python manage.py createsuperuser.

## Managing access without Bash

Visit https://itkara.pythonanywhere.com/admin/ and sign in with your Django superuser account. Select Judge invites. The initial invite allows 15 registrations and expires 30 days after migration is applied.

- Increase max_signups to allow more judges.
- Uncheck active to revoke the link immediately.
- Change expires_at to extend or shorten its lifetime.
- View signups to see how many seats are used.

Existing accounts remain accessible after the invitation expires or is revoked. Judge accounts are regular users, not staff, and retain per-user daily generation limits.

## Notes

The link is a bearer invitation: anyone you forward it to can register until the seat cap or expiry. Avoid posting the full invitation URL in a public README. Judge onboarding instructions are shown on the registration page. The normal single-use invitation command remains available.
