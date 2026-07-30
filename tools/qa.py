"""Pre-flight QA for the SCTechIA site. Run from the repo root:  python tools/qa.py

Checks the things that have actually bitten this build: em dashes, dead
links, missing meta, broken structured data, missing image alt text,
unbalanced markup and stale content claims.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PAGES = ['index.html', 'join.html', 'join-form.html', 'privacy.html', 'terms.html']
fails, warns = [], []


def fail(page, msg):
    fails.append((page, msg))


def warn(page, msg):
    warns.append((page, msg))


def strip_code(s):
    return re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)


# ---- per-page checks -------------------------------------------------
for p in PAGES:
    s = open(p, encoding='utf-8').read()
    body = strip_code(s)

    if '—' in s or '&mdash;' in s:
        fail(p, 'contains an em dash')

    for tag, pat in [('title', r'<title>[^<]+</title>'),
                     ('meta description', r'<meta name="description" content="[^"]{40,}"'),
                     ('canonical', r'<link rel="canonical"'),
                     ('viewport', r'name="viewport"'),
                     ('og:title', r'og:title'),
                     ('og:image', r'og:image'),
                     ('og:url', r'og:url'),
                     ('twitter:card', r'twitter:card'),
                     ('lang attribute', r'<html lang=')]:
        if not re.search(pat, s):
            fail(p, 'missing ' + tag)

    o, c = len(re.findall(r'<div\b', body)), len(re.findall(r'</div>', body))
    if o != c:
        fail(p, 'unbalanced divs: %d open, %d close' % (o, c))

    for m in re.finditer(r'<img\b[^>]*>', body):
        if 'alt=' not in m.group(0):
            fail(p, 'image without alt: ' + m.group(0)[:70])

    for m in re.finditer(r'href="#"', body):
        fail(p, 'dead placeholder link href="#"')

    if re.search(r'REPLACE_|TODO|FIXME|LOREM|Lorem ipsum', s):
        fail(p, 'placeholder text left in source')

    h1s = re.findall(r'<h1[ >]', body)
    if len(h1s) != 1:
        warn(p, 'has %d h1 tags (expected exactly 1)' % len(h1s))

    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            json.loads(blk)
        except Exception as e:
            fail(p, 'invalid JSON-LD: %s' % e)

    # Internal links resolve to a real file
    for href in re.findall(r'href="([^"#?:]+\.html)"', s):
        if not os.path.exists(href.lstrip('/')):
            fail(p, 'link to missing file: ' + href)

    for src in re.findall(r'src="([^"#?:]+\.(?:png|jpg|jpeg|svg|webp))"', s):
        path = src.lstrip('/')
        if not path.startswith('http') and not os.path.exists(path):
            fail(p, 'missing image file: ' + src)


# ---- content integrity ----------------------------------------------
pricing = json.load(open('content/pricing.json', encoding='utf-8'))['tiers']
faqs = json.load(open('content/faq.json', encoding='utf-8'))['faqs']
board = json.load(open('content/board.json', encoding='utf-8'))['members']
members = json.load(open('content/members.json', encoding='utf-8'))['members']

RETIRED = ['member directory listing', 'monthly industry briefings',
           'enhanced company directory']
for t in pricing:
    for f in t['features']:
        if f.lower() in RETIRED or any(r in f.lower() for r in RETIRED):
            fail('pricing.json', '%s still lists a retired benefit: %s' % (t['name'], f))
    if t['ctaType'] == 'join' and t['priceMode'] != 'amount':
        fail('pricing.json', '%s has a join button but no price' % t['name'])
    if re.search(r'\b[23] named\b', t['period'] + ' ' + ' '.join(t['features'])):
        fail('pricing.json', '%s uses a digit where a word was requested' % t['name'])

for m in board:
    bio = m.get('bio') or ''
    if len(bio) > 130:
        fail('board.json', '%s bio is %d chars (max 130)' % (m['name'], len(bio)))
    if not os.path.exists(m['photo'].lstrip('/')):
        fail('board.json', 'missing photo for %s: %s' % (m['name'], m['photo']))

for m in members:
    if not os.path.exists(m['logo'].lstrip('/')):
        fail('members.json', 'missing logo file: ' + m['logo'])

if len(faqs) < 5:
    warn('faq.json', 'only %d questions' % len(faqs))

# FAQ schema on join.html must match faq.json exactly
s = open('join.html', encoding='utf-8').read()
blk = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
graph = json.loads(blk.group(1))['@graph']
fp = [n for n in graph if n.get('@type') == 'FAQPage']
if not fp:
    fail('join.html', 'no FAQPage schema')
elif len(fp[0]['mainEntity']) != len(faqs):
    fail('join.html', 'FAQ schema has %d questions, faq.json has %d. Run tools/build-schema.py'
         % (len(fp[0]['mainEntity']), len(faqs)))

svc = [n for n in graph if n.get('@type') == 'Service']
if svc:
    priced = [o for o in svc[0]['offers'] if 'price' in o]
    want = [t for t in pricing if t['priceMode'] == 'amount']
    if len(priced) != len(want):
        fail('join.html', 'offer schema has %d prices, pricing.json has %d. Run tools/build-schema.py'
             % (len(priced), len(want)))
    for o, t in zip(priced, want):
        if o['price'] != t['priceDisplay'].replace(',', ''):
            fail('join.html', 'schema price %s does not match %s' % (o['price'], t['priceDisplay']))

# ---- site files ------------------------------------------------------
for f in ['robots.txt', 'sitemap.xml', 'llms.txt', 'netlify.toml', 'admin/config.yml']:
    if not os.path.exists(f):
        fail('site', 'missing ' + f)

sm = open('sitemap.xml', encoding='utf-8').read()
for slug in ['/privacy', '/terms', '/join']:
    if slug not in sm:
        warn('sitemap.xml', 'does not list ' + slug)

if 'Disallow: /admin/' not in open('robots.txt', encoding='utf-8').read():
    warn('robots.txt', 'admin panel is not disallowed')

# ---- report ----------------------------------------------------------
print('=' * 66)
print('SCTechIA site QA')
print('=' * 66)
if fails:
    print('\nFAIL (%d)' % len(fails))
    for p, m in fails:
        print('  [%s] %s' % (p, m))
if warns:
    print('\nWARN (%d)' % len(warns))
    for p, m in warns:
        print('  [%s] %s' % (p, m))
if not fails and not warns:
    print('\nAll checks passed.')
elif not fails:
    print('\nNo failures. %d warning(s) above.' % len(warns))
print()
sys.exit(1 if fails else 0)
