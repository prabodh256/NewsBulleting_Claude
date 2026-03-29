#!/usr/bin/env python3
"""
JJFO Competitor Tracker — Daily News Scraper
Runs at 2:30 AM GMT every day (via PythonAnywhere scheduled task).

Priority order for email digest:
  1. Funding news — Portfolio Companies
  2. Funding news — Competitors
  3. M&A news    — Portfolio Companies
  4. M&A news    — Competitors
  5. Other News  (regulatory, product launches, partnerships, etc.)

Share price / stock market articles are filtered out entirely.
"""

import os
import csv
import time
import re
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher
from urllib.parse import quote_plus

import requests
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── Resend setup ──────────────────────────────────────────────────────────────
import resend as resend_lib
resend_lib.api_key = os.getenv('RESEND_API_KEY', '')

EMAIL_FROM      = os.getenv('EMAIL_FROM', 'noreply@example.com')
COMPANIES_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'companies.csv')
RECIPIENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recipients.csv')
DISPATCH_LOG    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dispatch_log.csv')

# ── News Sources ──────────────────────────────────────────────────────────────

RSS_FEEDS = {
    'Inc42':              'https://inc42.com/feed/',
    'YourStory':          'https://yourstory.com/feed',
    'Entrackr':           'https://entrackr.com/feed/',
    'VCCircle':           'https://www.vccircle.com/feed/',
    'StartupTalky':       'https://www.startuptalky.com/feed/',
    'TechCrunch':         'https://techcrunch.com/feed/',
    'TechCrunch India':   'https://techcrunch.com/tag/india/feed/',
    'Analytics India':    'https://analyticsindiamag.com/feed/',
    'IndianWeb2':         'https://indianweb2.com/feed/',
    'The Ken':            'https://the-ken.com/feed/',
    'BW Disrupt':         'https://www.bwdisrupt.com/feed/',
    'Economic Times':     'https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/13357270.cms',
    'Business Standard':  'https://www.business-standard.com/rss/companies-101.rss',
    'Mint Startups':      'https://www.livemint.com/rss/companies',
    'NDTV Profit':        'https://feeds.feedburner.com/ndtvprofit-latest',
    'Moneycontrol News':  'https://www.moneycontrol.com/rss/MCtopnews.xml',
    'Financial Express':  'https://www.financialexpress.com/feed/',
    'Hindu Business':     'https://www.thehindubusinessline.com/feeder/default.rss',
}

DIRECT_SOURCES = {
    'Moneycontrol Startups':      'https://www.moneycontrol.com/news/startups/',
    'Business Standard Startups': 'https://www.business-standard.com/startups',
    'Livemint Startups':          'https://www.livemint.com/companies/start-ups',
    'Inc42 Funding':              'https://inc42.com/buzz/funding/',
    'Entrackr Funding':           'https://entrackr.com/category/funding/',
}

# ── Keyword Classifiers ───────────────────────────────────────────────────────

FUNDING_KEYWORDS = [
    'funding', 'raised', 'series a', 'series b', 'series c', 'series d',
    'seed round', 'pre-seed', 'bridge round', 'investment', 'venture capital',
    'vc funding', 'angel round', 'capital raise', 'fundraise', 'fundraising',
    'closed round', 'secures funding', 'bags funding', 'gets funding',
    'million funding', 'crore funding', 'backed by', 'investor',
]

MA_KEYWORDS = [
    'acquisition', 'acquired', 'acquires', 'merger', 'merged', 'merges',
    'buyout', 'buy out', 'takeover', 'take over', 'ipo', 'initial public offering',
    'listed on', 'goes public', 'stake acquisition', 'strategic acquisition',
    'buys stake', 'acqui-hire', 'acquihire', 'reverse merger',
]

# Articles containing ANY of these are dropped entirely — share price noise
SHARE_PRICE_FILTER = [
    'share price', 'stock price', 'share rose', 'share fell', 'share up',
    'share down', 'stock rose', 'stock fell', 'stock up', 'stock down',
    'shares rise', 'shares fall', 'shares surge', 'shares plunge', 'shares jump',
    'shares slip', 'shares gain', 'shares lose', 'shares trade',
    '52-week high', '52-week low', 'trading at rs', 'trading at ₹',
    'target price', 'buy rating', 'sell rating', 'hold rating',
    'sensex', 'nifty', 'bse listed', 'nse listed', 'market capitalisation',
    'market cap', 'stock market', 'equity market', 'trade setup',
    'technical analysis', 'support level', 'resistance level',
]


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_companies():
    companies = {}
    try:
        with open(COMPANIES_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)          # skip header
            for row in reader:
                if not row:
                    continue
                name   = row[0].strip() if len(row) > 0 else ''
                sector = row[1].strip() if len(row) > 1 else ''
                if not name:
                    continue
                raw_competitors = row[2:]
                competitors = []
                for part in raw_competitors:
                    for c in part.split(','):
                        c = c.strip()
                        if c:
                            competitors.append(c)
                companies[name] = {
                    'sector':      sector,
                    'competitors': competitors,
                }
    except FileNotFoundError:
        print(f'WARNING: {COMPANIES_FILE} not found')
    return companies


def load_recipients():
    recipients = []
    try:
        with open(RECIPIENTS_FILE, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                email = row.get('Email', '').strip()
                if email:
                    recipients.append(email)
    except FileNotFoundError:
        print(f'WARNING: {RECIPIENTS_FILE} not found')
    return recipients


# ── Search Index ──────────────────────────────────────────────────────────────

def build_search_index(companies):
    """
    Returns: { search_term_lower: (portfolio_company_name, is_competitor) }
    Covers every portfolio company AND each of their stored competitors.
    """
    index = {}
    for name, data in companies.items():
        index[name.lower()] = (name, False)
        for comp in data['competitors']:
            if comp.lower() not in index:
                index[comp.lower()] = (name, True)
    return index


# ── Share Price Filter ────────────────────────────────────────────────────────

def is_share_price_article(headline):
    """Return True if the headline is about stock/share prices — skip these."""
    h = headline.lower()
    return any(kw in h for kw in SHARE_PRICE_FILTER)


# ── Scraping ──────────────────────────────────────────────────────────────────

def scrape_rss(search_index):
    news = defaultdict(list)

    # 1. Broad RSS feeds — scan headlines for any tracked term
    for source, feed_url in RSS_FEEDS.items():
        try:
            print(f'  RSS → {source}')
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:50]:
                headline = entry.get('title', '').strip()
                link     = entry.get('link', '').strip()
                if not headline or not link:
                    continue
                if is_share_price_article(headline):
                    continue
                headline_lower = headline.lower()
                for term, (portfolio_name, is_competitor) in search_index.items():
                    if term in headline_lower:
                        news[portfolio_name].append({
                            'headline':      headline,
                            'url':           link,
                            'source':        source,
                            'published':     entry.get('published', datetime.now().isoformat()),
                            'is_competitor': is_competitor,
                            'matched_term':  term,
                        })
                        break
        except Exception as exc:
            print(f'  RSS error ({source}): {exc}')
        time.sleep(0.3)

    # 2. Google News RSS — one targeted search per company + per competitor
    all_terms = list(search_index.keys())
    print(f'\n  Google News targeted search ({len(all_terms)} terms)...')
    for term, (portfolio_name, is_competitor) in search_index.items():
        try:
            q        = quote_plus(term)
            feed_url = f'https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
            feed     = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                headline = entry.get('title', '').strip()
                link     = entry.get('link', '').strip()
                if not headline or not link:
                    continue
                if is_share_price_article(headline):
                    continue
                news[portfolio_name].append({
                    'headline':      headline,
                    'url':           link,
                    'source':        'Google News',
                    'published':     entry.get('published', datetime.now().isoformat()),
                    'is_competitor': is_competitor,
                    'matched_term':  term,
                })
        except Exception:
            pass
        time.sleep(0.2)

    return news


def scrape_direct(search_index):
    news    = defaultdict(list)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36'
    }
    for source, source_url in DIRECT_SOURCES.items():
        try:
            print(f'  Direct → {source}')
            resp = requests.get(source_url, headers=headers, timeout=12)
            soup = BeautifulSoup(resp.content, 'html.parser')
            for a_tag in soup.find_all('a', limit=80):
                headline = a_tag.get_text(strip=True)
                link     = a_tag.get('href', '')
                if not headline or not link or len(headline) < 12:
                    continue
                if is_share_price_article(headline):
                    continue
                if link.startswith('/'):
                    from urllib.parse import urlparse
                    base = urlparse(source_url)
                    link = f'{base.scheme}://{base.netloc}{link}'
                elif not link.startswith('http'):
                    continue
                headline_lower = headline.lower()
                for term, (portfolio_name, is_competitor) in search_index.items():
                    if term in headline_lower:
                        news[portfolio_name].append({
                            'headline':      headline,
                            'url':           link,
                            'source':        source,
                            'published':     datetime.now().isoformat(),
                            'is_competitor': is_competitor,
                            'matched_term':  term,
                        })
                        break
        except Exception as exc:
            print(f'  Direct error ({source}): {exc}')
        time.sleep(1)
    return news


# ── Merge & Deduplicate ───────────────────────────────────────────────────────

def merge(rss_news, direct_news):
    merged = defaultdict(list)
    for company, articles in rss_news.items():
        merged[company].extend(articles)
    for company, articles in direct_news.items():
        merged[company].extend(articles)
    return merged


def deduplicate(news_list, threshold=0.78):
    unique, seen = [], []
    for item in news_list:
        is_dup = any(
            SequenceMatcher(None, item['headline'].lower(), h.lower()).ratio() > threshold
            for h in seen
        )
        if not is_dup:
            unique.append(item)
            seen.append(item['headline'])
    return unique


# ── Categorise (strict priority order) ───────────────────────────────────────

def categorise(all_news):
    """
    Priority buckets (in order):
      1. portfolio_funding  — funding news about portfolio companies
      2. competitor_funding — funding news about competitors
      3. portfolio_ma       — M&A news about portfolio companies
      4. competitor_ma      — M&A news about competitors
      5. other              — everything else (no share-price articles)
    """
    cats = {k: [] for k in (
        'portfolio_funding', 'competitor_funding',
        'portfolio_ma',      'competitor_ma',
        'other',
    )}

    for company_name, articles in all_news.items():
        for item in articles:
            h    = item['headline'].lower()
            comp = item.get('is_competitor', False)

            if any(kw in h for kw in FUNDING_KEYWORDS):
                cats['competitor_funding' if comp else 'portfolio_funding'].append(item)
            elif any(kw in h for kw in MA_KEYWORDS):
                cats['competitor_ma' if comp else 'portfolio_ma'].append(item)
            else:
                cats['other'].append(item)

    return cats


# ── HTML Email ────────────────────────────────────────────────────────────────

SECTION_META = [
    ('portfolio_funding', '💰 Funding — Portfolio Companies',  '#1a7a4a'),
    ('competitor_funding','💸 Funding — Competitors',          '#c0392b'),
    ('portfolio_ma',      '🤝 M&A — Portfolio Companies',      '#1a5c8a'),
    ('competitor_ma',     '⚔️  M&A — Competitors',             '#7d3c98'),
    ('other',             '📰 Other News',                      '#555555'),
]

MAX_ARTICLES_PER_SECTION = 8


def build_html_email(categorised):
    today = datetime.now().strftime('%B %d, %Y')
    total = 0
    sections_html = ''

    for key, title, colour in SECTION_META:
        items = deduplicate(categorised[key])[:MAX_ARTICLES_PER_SECTION]
        if not items:
            continue
        total += len(items)
        rows = ''.join(
            f'''<tr>
              <td style="padding:10px 0 10px 12px;border-bottom:1px solid #f0f0f0;">
                <a href="{item["url"]}"
                   style="color:#1a1a1a;font-weight:600;text-decoration:none;font-size:14px;
                          line-height:1.4;">{item["headline"]}</a><br>
                <span style="color:#999;font-size:12px;margin-top:3px;display:block;">
                  {item.get("source","")}
                  &nbsp;·&nbsp;
                  {item.get("matched_term","").title()}
                </span>
              </td>
            </tr>'''
            for item in items
        )
        sections_html += f'''
        <tr>
          <td style="padding:20px 12px 6px;">
            <span style="background:{colour};color:#fff;padding:5px 12px;
                  border-radius:4px;font-size:13px;font-weight:700;
                  letter-spacing:.3px;">{title}</span>
          </td>
        </tr>
        {rows}
        '''

    if not sections_html:
        sections_html = '''<tr><td style="padding:24px;color:#999;font-size:14px;">
          No relevant news found today. The scraper ran successfully —
          no new articles matched your tracked companies.</td></tr>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f0f2f5">
 <tr><td align="center" style="padding:32px 16px;">
  <table width="620" cellpadding="0" cellspacing="0"
         style="background:#fff;border-radius:10px;overflow:hidden;
                box-shadow:0 2px 12px rgba(0,0,0,.10);">

   <!-- Header -->
   <tr>
    <td style="background:#111827;padding:28px 28px 24px;">
     <table width="100%"><tr>
      <td>
       <div style="color:#fff;font-size:20px;font-weight:700;letter-spacing:.3px;">
        📊 JJFO Daily News Bulletin
       </div>
       <div style="color:#9ca3af;font-size:13px;margin-top:5px;">{today}</div>
      </td>
      <td align="right" style="color:#6b7280;font-size:12px;vertical-align:bottom;">
       {total} articles
      </td>
     </tr></table>
    </td>
   </tr>

   <!-- Intro -->
   <tr>
    <td style="padding:20px 28px 8px;color:#6b7280;font-size:13px;
               border-bottom:2px solid #f3f4f6;">
     Your daily curated digest — funding, M&amp;A and key news for your portfolio
     companies and their competitors. Share price articles excluded.
    </td>
   </tr>

   <!-- News sections -->
   <tr>
    <td style="padding:0 16px 16px;">
     <table width="100%" cellpadding="0" cellspacing="0">
      {sections_html}
     </table>
    </td>
   </tr>

   <!-- Footer -->
   <tr>
    <td style="background:#f9fafb;padding:14px 28px;border-top:1px solid #e5e7eb;
               color:#9ca3af;font-size:11px;">
     Sent daily at 2:30 AM GMT &nbsp;·&nbsp; JJFO Competitor Tracker
    </td>
   </tr>

  </table>
 </td></tr>
</table>
</body>
</html>'''

    return html, total


# ── Send via Resend ───────────────────────────────────────────────────────────

def send_email(html_body, recipients):
    if not resend_lib.api_key:
        print('ERROR: RESEND_API_KEY not set in .env')
        return False
    if not recipients:
        print('WARNING: No recipients found in recipients.csv')
        return False
    today = datetime.now().strftime('%B %d, %Y')
    success = True
    for recipient in recipients:
        try:
            resend_lib.Emails.send({
                'from':    EMAIL_FROM,
                'to':      recipient,
                'subject': f'JJFO News Bulletin — {today}',
                'html':    html_body,
            })
            print(f'  ✓ Sent to {recipient}')
        except Exception as exc:
            print(f'  ✗ Failed for {recipient}: {exc}')
            success = False
    return success


# ── Dispatch Log ──────────────────────────────────────────────────────────────

def log_dispatch(status, article_count, recipient_count):
    try:
        with open(DISPATCH_LOG, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([
                datetime.now().isoformat(), status, article_count, recipient_count
            ])
    except Exception as exc:
        print(f'Log error: {exc}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f'\n{"="*60}')
    print(f'  JJFO News Scraper  —  {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}')
    print(f'{"="*60}')

    companies  = load_companies()
    recipients = load_recipients()

    if not companies:
        print('No companies found — add some via the web dashboard first.')
        log_dispatch('skipped-no-companies', 0, 0)
        return

    total_competitors = sum(len(d['competitors']) for d in companies.values())
    search_index      = build_search_index(companies)

    print(f'\n  Portfolio companies : {len(companies)}')
    print(f'  Total competitors   : {total_competitors}')
    print(f'  Unique search terms : {len(search_index)}')
    print(f'  Recipients          : {len(recipients)}')
    print(f'  RSS sources         : {len(RSS_FEEDS)}')
    print(f'  Direct sources      : {len(DIRECT_SOURCES)}')

    print('\n[1/4] Scraping RSS feeds + Google News...')
    rss_news = scrape_rss(search_index)

    print('\n[2/4] Scraping direct sources...')
    direct_news = scrape_direct(search_index)

    print('\n[3/4] Merging, categorising, deduplicating...')
    all_news    = merge(rss_news, direct_news)
    raw_count   = sum(len(v) for v in all_news.values())
    categorised = categorise(all_news)

    for key, title, _ in SECTION_META:
        count = len(deduplicate(categorised[key]))
        print(f'  {title:<40} {count} articles')

    print('\n[4/4] Sending email digest...')
    html_body, article_count = build_html_email(categorised)
    print(f'  Total articles in digest: {article_count}')

    success = send_email(html_body, recipients)
    status  = 'success' if success else 'email-failed'
    log_dispatch(status, article_count, len(recipients))

    print(f'\n  Status : {status.upper()}')
    print(f'{"="*60}\n')


if __name__ == '__main__':
    main()
