"""Fetch public advert pages without accessing local/private network addresses."""
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 2_000_000


def advert_read_capability():
    import os
    configured=os.getenv('HIREATIONSHIP_FULL_ADVERT_FETCH_ENABLED','auto').lower()
    proxies=[os.getenv(name,'') for name in ('https_proxy','HTTPS_PROXY','http_proxy','HTTP_PROXY')]
    restricted=any(urlsplit(proxy).hostname == 'proxy.server' for proxy in proxies)
    enabled=configured=='1' or configured=='auto' and not restricted
    reason='' if enabled else 'This hosting environment cannot automatically read external job websites. Adzuna previews still work. Open the original advert, copy its description and paste it here for a free CV check.'
    return {'fullAdvertReadsAvailable':enabled, 'fullAdvertReadNotice':reason}


def public_target(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('Only public HTTPS advert links are supported.')
    addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    ips = list(dict.fromkeys(item[4][0] for item in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError('This advert address is not supported.')
    return parts, ips[0]


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname, ip, timeout):
        super().__init__(hostname, timeout=timeout, context=ssl.create_default_context())
        self.public_ip = ip

    def connect(self):
        sock = socket.create_connection((self.public_ip, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def fetch_page(url):
    deadline = time.monotonic() + 20
    for _ in range(6):
        parts, ip = public_target(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('The advert took too long to load. Paste its description instead.')
        conn = PinnedHTTPSConnection(parts.hostname, ip, min(remaining, 6))
        try:
            path = parts.path or '/'
            if parts.query:
                path += '?' + parts.query
            conn.request('GET', path, headers={'User-Agent':'Hireationship/1.0 (job description reader)', 'Accept':'text/html,application/xhtml+xml', 'Accept-Encoding':'identity'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    break
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError('The job site did not allow the advert to be read. Open it and paste the description instead.')
            if not any(kind in (response.getheader('Content-Type') or '').lower() for kind in ('text/html', 'application/xhtml+xml')):
                raise ValueError('This link did not return an HTML job advert.')
            chunks=[]; size=0
            while True:
                if time.monotonic() > deadline:
                    raise ValueError('The advert took too long to load.')
                chunk=response.read(min(65536, MAX_BYTES + 1 - size))
                if not chunk: break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('The advert page is too large. Paste its description instead.')
                chunks.append(chunk)
            charset=response.headers.get_content_charset() or 'utf-8'
            return b''.join(chunks).decode(charset, errors='replace'), url
        finally:
            conn.close()
    raise ValueError('Too many redirects. Open the advert and paste its description instead.')


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.json_scripts=[]; self.script=None; self.hidden=0; self.text=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == 'script':
            self.script=[] if 'ld+json' in attrs.get('type','').lower() else None
        if tag in ('script','style','noscript'): self.hidden += 1
        if tag in ('p','li','h1','h2','h3','div','br'): self.text.append('\n')
    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.json_scripts.append(''.join(self.script)); self.script=None
        if tag in ('script','style','noscript'): self.hidden=max(0,self.hidden-1)
        if tag in ('p','li','h1','h2','h3','div'): self.text.append('\n')
    def handle_data(self, data):
        if self.script is not None: self.script.append(data)
        if not self.hidden: self.text.append(data)


def plain_text(html):
    parser=PageParser(); parser.feed(html)
    return '\n'.join(line.strip() for line in ''.join(parser.text).splitlines() if line.strip())


def job_postings(value):
    if isinstance(value,list):
        for item in value: yield from job_postings(item)
    elif isinstance(value,dict):
        kind=value.get('@type',[])
        if kind == 'JobPosting' or isinstance(kind,list) and 'JobPosting' in kind: yield value
        for item in value.values():
            if isinstance(item,(list,dict)): yield from job_postings(item)


def extract_description(html, title=''):
    page=PageParser(); page.feed(html)
    postings=[]
    for script in page.json_scripts:
        try: postings.extend(job_postings(json.loads(script)))
        except (ValueError,TypeError): continue
    wanted=set(re.findall(r'\w+', title.lower()))
    postings.sort(key=lambda job: -len(wanted & set(re.findall(r'\w+',str(job.get('title','')).lower()))))
    for posting in postings:
        if not isinstance(posting.get('description'),str): continue
        if len(postings)>1 and wanted and len(wanted & set(re.findall(r'\w+',str(posting.get('title','')).lower()))) < max(1,len(wanted)//2):continue
        text=plain_text(posting['description'])
        if len(text)>=150: return text[:30000], 'structured job description'
    # Avoid mistaking navigation, bot challenges or a list of jobs for the advert.
    match=re.search(r'<(?:main|article)\b[^>]*>(.*?)</(?:main|article)>', html, re.I|re.S)
    if match:
        text=plain_text(match.group(1))
        overlap=wanted & set(re.findall(r'\w+',text[:1500].lower()))
        if len(text)>=300 and len(overlap)>=max(1,len(wanted)//2) and re.search(r'qualifications|requirements|responsibilities|essential skills',text,re.I):
            return text[:30000], 'visible advert text'
    raise ValueError('The page did not expose a readable job description. It may require JavaScript or block automated access. Paste the full description instead.')


def read_advert(url, title=''):
    try:
        html, final_url=fetch_page(url)
        text, source=extract_description(html,title)
        return {'text':text, 'source':source, 'url':final_url}
    except (OSError, http.client.HTTPException, UnicodeError, LookupError):
        raise ValueError('The original advert could not be loaded. Open it and paste the full description instead.') from None


def advert_cache_key(url, title=''):
    import hashlib
    return 'advert-text-v1:' + hashlib.sha256((str(url)+'\n'+str(title)).encode()).hexdigest()


def cached_advert(url, title=''):
    from django.core.cache import cache
    return cache.get(advert_cache_key(url,title))


def read_and_cache_advert(url, title=''):
    from django.core.cache import cache
    key=advert_cache_key(url,title)
    try:
        details=read_advert(url,title)
    except ValueError:
        # Cache failures briefly so inaccessible sites aren't repeatedly requested.
        cache.set(key,{'unavailable':True},600)
        raise
    cache.set(key,details,6*60*60)
    return details
