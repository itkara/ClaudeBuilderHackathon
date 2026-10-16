"""Explicit hosts plus hostnames supplied by the deployment platform."""
import os
import re


def host_settings(environ=None):
    env=os.environ if environ is None else environ
    hosts=[value.strip() for value in env.get('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1,itkara.pythonanywhere.com').split(',') if value.strip()]
    origins=['https://itkara.pythonanywhere.com']
    origins.extend(value.strip() for value in env.get('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if value.strip())
    for name in ('VERCEL_URL','VERCEL_BRANCH_URL','VERCEL_PROJECT_PRODUCTION_URL'):
        host=env.get(name,'').strip().lower()
        # These are server-side environment values, never a request's Host header.
        # Accept exact DNS names, rather than trusting every *.vercel.app tenant.
        if host and len(host)<=253 and re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',host):
            hosts.append(host)
            origins.append('https://'+host)
    return list(dict.fromkeys(hosts)),list(dict.fromkeys(origins))
