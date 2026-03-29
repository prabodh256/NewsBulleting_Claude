#!/usr/bin/env python3
"""
Competitor Tracker Agent
Core logic: company search/disambiguation, sector detection,
competitor finding, and CSV storage helpers.
"""

import csv
import os
import re
import time
import requests
import feedparser
from urllib.parse import quote_plus

COMPANIES_FILE = os.path.join(os.path.dirname(__file__), 'companies.csv')
RECIPIENTS_FILE = os.path.join(os.path.dirname(__file__), 'recipients.csv')

# ─── Sector keyword mapping ───────────────────────────────────────────────────

SECTOR_KEYWORDS = {
    'FinTech':       ['fintech', 'financial technology', 'payment', 'lending', 'nbfc',
                      'neobank', 'insurtech', 'wealthtech', 'remittance', 'credit card',
                      'digital bank', 'loan', 'mortgage', 'invoice financing'],
    'InsurTech':     ['insurance', 'insurer', 'insurtech', 'policy', 'claim', 'underwriting',
                      'reinsurance', 'health insurance', 'life insurance'],
    'EdTech':        ['edtech', 'education technology', 'e-learning', 'online learning',
                      'tutoring', 'upskilling', 'skill development', 'test prep', 'lms'],
    'HealthTech':    ['health', 'healthtech', 'medical', 'healthcare', 'hospital', 'pharma',
                      'biotech', 'telemedicine', 'diagnostics', 'clinical', 'patient'],
    'SpaceTech':     ['space', 'satellite', 'rocket', 'aerospace', 'launch vehicle',
                      'spacetech', 'orbital', 'nanosatellite', 'cubesat'],
    'Logistics':     ['logistics', 'delivery', 'supply chain', 'freight', 'shipping',
                      'last-mile', 'warehouse', 'courier', 'fulfillment', 'trucking'],
    'E-commerce':    ['e-commerce', 'ecommerce', 'online retail', 'marketplace',
                      'd2c', 'direct-to-consumer', 'shopping', 'fashion', 'beauty'],
    'AI':            ['artificial intelligence', 'machine learning', 'deep learning',
                      'natural language', 'nlp', 'computer vision', 'generative ai',
                      'large language model', 'llm', 'ai startup'],
    'Cybersecurity': ['cybersecurity', 'cyber security', 'information security', 'firewall',
                      'endpoint', 'threat detection', 'zero trust', 'soc', 'siem'],
    'Mobility':      ['mobility', 'electric vehicle', ' ev ', 'ride-hailing', 'ride sharing',
                      'urban air', 'autonomous vehicle', 'fleet management', 'aviation'],
    'AgriTech':      ['agriculture', 'agritech', 'farming', 'crop', 'agri', 'seeds',
                      'fertilizer', 'precision farming', 'irrigation'],
    'HR Tech':       ['human resources', 'hr tech', 'hrtech', 'recruitment', 'talent',
                      'workforce', 'payroll', 'employee', 'staffing', 'hiring'],
    'B2B SaaS':      ['b2b', 'saas', 'enterprise software', 'business software',
                      'crm', 'erp', 'workflow automation', 'api platform'],
    'Media':         ['media', 'news', 'content', 'publishing', 'journalism',
                      'digital media', 'podcast', 'newsletter'],
    'GreenTech':     ['greentech', 'cleantech', 'solar', 'renewable energy',
                      'clean energy', 'sustainability', 'carbon', 'wind energy', 'ev charging'],
    'Gaming':        ['gaming', 'esports', 'e-sports', 'fantasy sports', 'game',
                      'mobile gaming', 'online gaming', 'video game'],
    'Entertainment': ['entertainment', 'streaming', 'ott', 'video streaming',
                      'music streaming', 'content platform', 'film', 'web series'],
    'Analytics':     ['analytics', 'data analytics', 'business intelligence', 'bi tool',
                      'data platform', 'insights', 'reporting', 'dashboard'],
    'Mental Health': ['mental health', 'therapy', 'meditation', 'mindfulness',
                      'counselling', 'counseling', 'wellbeing', 'stress'],
    'PetCare':       ['pet', 'animal health', 'veterinary', 'petcare', 'dog', 'cat'],
    'Networking':    ['network', 'sd-wan', 'router', 'switch', 'networking',
                      'telecom', 'wireless', 'broadband'],
    'Furniture':     ['furniture', 'home decor', 'interior design', 'home furnishing'],
    'Beverages':     ['beverage', 'alcohol', 'spirits', 'beer', 'wine', 'brewery',
                      'distillery', 'drink brand'],
    'Retail':        ['retail', 'supermarket', 'grocery', 'kirana', 'mart', 'store chain'],
}


# ─── Company Search & Disambiguation ─────────────────────────────────────────

def search_company(name):
    """
    Search for a company using the DuckDuckGo Instant Answer API (free, no key).
    Returns a list of up to 5 possible matches:
      [{'name': str, 'description': str, 'url': str}]
    """
    results = []
    try:
        query = quote_plus(f"{name} company")
        url = (f"https://api.duckduckgo.com/?q={query}"
               f"&format=json&no_html=1&skip_disambig=0")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CompetitorTracker/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        # Primary result (knowledge panel)
        if data.get('Heading') and (data.get('AbstractText') or data.get('Abstract')):
            results.append({
                'name':        data['Heading'],
                'description': (data.get('AbstractText') or data.get('Abstract', ''))[:220],
                'url':         data.get('AbstractURL', ''),
            })

        # Disambiguation / related topics
        for topic in data.get('RelatedTopics', []):
            if not isinstance(topic, dict):
                continue
            text = topic.get('Text', '')
            if not text or len(text) < 10:
                continue
            # The name is usually before the first " - " separator
            candidate_name = text.split(' - ')[0].strip()
            if len(candidate_name) > 60:
                candidate_name = candidate_name[:60]
            results.append({
                'name':        candidate_name,
                'description': text[:220],
                'url':         topic.get('FirstURL', ''),
            })
            if len(results) >= 5:
                break

    except Exception as exc:
        print(f"[search_company] DuckDuckGo error: {exc}")

    # Fallback: always offer a manual option
    if not results:
        results.append({
            'name':        name,
            'description': ('No description found automatically. '
                            'Click "Confirm" to add this company as-is.'),
            'url':         '',
        })

    return results[:5]


# ─── Sector Detection ─────────────────────────────────────────────────────────

def detect_sector(description_text):
    """
    Infer the business sector from a plain-text company description.
    Returns the best-matching sector name, or 'Other'.
    """
    if not description_text:
        return 'Other'
    text = description_text.lower()
    best_sector = 'Other'
    best_count  = 0
    for sector, keywords in SECTOR_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count  = count
            best_sector = sector
    return best_sector


# ─── Competitor Discovery ─────────────────────────────────────────────────────

# Common English words / stop-words to exclude from extracted company names
_STOP_WORDS = {
    'The', 'A', 'An', 'In', 'Of', 'For', 'To', 'And', 'Or', 'By', 'With',
    'From', 'Is', 'Are', 'Was', 'Inc', 'Ltd', 'LLC', 'Corp', 'Co', 'India',
    'Indian', 'New', 'Top', 'Best', 'How', 'Why', 'This', 'That', 'Its',
    'Has', 'Not', 'Can', 'Will', 'More', 'Also', 'Into', 'After', 'Over',
    'Under', 'About', 'Other', 'Both', 'All', 'Any', 'Each', 'Read', 'Here',
    'Its', 'Such', 'Than', 'Then', 'They', 'These', 'Those', 'When', 'Where',
    'Which', 'While', 'Who', 'Whom', 'Your', 'Our', 'Their', 'Has', 'Have',
}

# Sector-based fallback competitors for Indian startup ecosystem
SECTOR_DEFAULTS = {
    'FinTech':       ['Razorpay', 'Paytm', 'PhonePe', 'BharatPe', 'CRED'],
    'InsurTech':     ['Acko', 'Digit Insurance', 'PolicyBazaar', 'Tata AIG', 'Go Digit'],
    'EdTech':        ["Byju's", 'Unacademy', 'Vedantu', 'upGrad', 'Simplilearn'],
    'HealthTech':    ['Practo', '1mg', 'PharmEasy', 'Healthians', 'mFine'],
    'SpaceTech':     ['Skyroot Aerospace', 'Agnikul Cosmos', 'Pixxel', 'Dhruva Space', 'Bellatrix'],
    'Logistics':     ['Delhivery', 'Shadowfax', 'Xpressbees', 'Shiprocket', 'Ecom Express'],
    'E-commerce':    ['Nykaa', 'Meesho', 'Myntra', 'Flipkart', 'Amazon India'],
    'AI':            ['OpenAI', 'Google DeepMind', 'Anthropic', 'Sarvam AI', 'Krutrim'],
    'Cybersecurity': ['Palo Alto Networks', 'CrowdStrike', 'Fortinet', 'Quick Heal', 'Sequretek'],
    'Mobility':      ['Ather Energy', 'Ola Electric', 'Bounce', 'Rapido', 'BluSmart'],
    'AgriTech':      ['AgroStar', 'BigHaat', 'DeHaat', 'Ninjacart', 'Jio Kisan'],
    'HR Tech':       ['Darwinbox', 'greytHR', 'Keka', 'ZingHR', 'HROne'],
    'B2B SaaS':      ['Zoho', 'Freshworks', 'Chargebee', 'Postman', 'BrowserStack'],
    'GreenTech':     ['Waaree Energies', 'Adani Green', 'ReNew Power', 'Fourth Partner', 'Cleantech Solar'],
    'Gaming':        ['Dream11', 'MPL', 'WinZO', 'Gameskraft', 'Nazara Technologies'],
    'Media':         ['The Ken', 'Inc42', 'Entrackr', 'YourStory', 'The Morning Context'],
    'Analytics':     ['Mu Sigma', 'Fractal Analytics', 'Bridgei2i', 'LatentView', 'Tiger Analytics'],
    'Mental Health': ['Wysa', 'YourDOST', 'Vandrevala Foundation', 'iCall', 'Lissun'],
    'Retail':        ['Reliance Retail', 'DMart', 'Spencer\'s', 'V-Mart', 'Vishal Mega Mart'],
}


def _extract_names_from_text(text, seen, max_results=5):
    """Extract capitalised proper-noun phrases from free text."""
    results = []
    tokens = re.findall(
        r'\b[A-Z][a-zA-Z]+(?:[\s\-][A-Z][a-zA-Z]+){0,3}\b', text
    )
    for tok in tokens:
        tok = tok.strip()
        if (tok not in _STOP_WORDS
                and tok.lower() not in seen
                and len(tok) > 3
                and not tok.isupper()):          # skip ALL-CAPS abbreviations
            results.append(tok)
            seen.add(tok.lower())
            if len(results) >= max_results:
                break
    return results


def _wikipedia_competitors(company_name, seen):
    """
    Pull competitor names from the company's Wikipedia intro paragraph.
    Uses the free Wikipedia API — no key needed.
    """
    competitors = []
    try:
        # Step 1: find the Wikipedia page title
        search_url = (
            'https://en.wikipedia.org/w/api.php'
            f'?action=query&list=search&srsearch={quote_plus(company_name)}'
            '&format=json&srlimit=1'
        )
        headers = {'User-Agent': 'CompetitorTracker/1.0'}
        resp  = requests.get(search_url, headers=headers, timeout=10)
        pages = resp.json().get('query', {}).get('search', [])
        if not pages:
            return []

        title = pages[0]['title']

        # Step 2: fetch the intro extract
        extract_url = (
            'https://en.wikipedia.org/w/api.php'
            f'?action=query&titles={quote_plus(title)}'
            '&prop=extracts&exintro=1&explaintext=1&format=json'
        )
        resp    = requests.get(extract_url, headers=headers, timeout=10)
        p_data  = resp.json().get('query', {}).get('pages', {})
        extract = list(p_data.values())[0].get('extract', '')

        if not extract:
            return []

        # Step 3: look for explicit competitor sentences first
        competitor_patterns = [
            r'competes? (?:with|against) ([\w\s,&]+?)(?:\.|,|\band\b)',
            r'(?:rival|competitor)[s]? (?:include|such as|like) ([\w\s,&]+?)(?:\.|;)',
            r'(?:alongside|against) ([\w\s,&]+?) (?:in|for|on)',
        ]
        for pattern in competitor_patterns:
            for match in re.findall(pattern, extract, re.IGNORECASE):
                for part in re.split(r',|and', match):
                    name = part.strip().title()
                    if (len(name) > 3
                            and name.lower() not in seen
                            and name not in _STOP_WORDS):
                        competitors.append(name)
                        seen.add(name.lower())
                        if len(competitors) >= 5:
                            return competitors

        # Step 4: fall back to extracting capitalised names from the whole text
        if len(competitors) < 3:
            competitors += _extract_names_from_text(
                extract, seen, max_results=5 - len(competitors)
            )

    except Exception as exc:
        print(f"[wikipedia_competitors] error: {exc}")

    return competitors[:5]


def _scrape_inc42(company_name, seen):
    """Search Inc42 for the company and pull competitor names from article snippets."""
    results = []
    try:
        query = quote_plus(company_name)
        url   = f"https://inc42.com/?s={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Extract text from article snippets / excerpts
        snippets = soup.find_all(['p', 'div'], class_=re.compile(r'excerpt|summary|desc|content', re.I))
        full_text = ' '.join(s.get_text(' ', strip=True) for s in snippets[:10])

        # Also grab all article titles
        titles = ' '.join(a.get_text(strip=True) for a in soup.find_all('h2')[:20])
        full_text += ' ' + titles

        results = _extract_names_from_text(full_text, seen, max_results=5)
    except Exception as exc:
        print(f"[inc42] error: {exc}")
    return results


def _scrape_yourstory(company_name, seen):
    """Search YourStory for the company and extract competitor mentions."""
    results = []
    try:
        query = quote_plus(company_name)
        url   = f"https://yourstory.com/search?q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = ' '.join(p.get_text(strip=True) for p in soup.find_all(['p', 'h2', 'h3'])[:30])
        results = _extract_names_from_text(text, seen, max_results=5)
    except Exception as exc:
        print(f"[yourstory] error: {exc}")
    return results


def _scrape_tracxn(company_name, seen):
    """
    Search Tracxn (free tier) for the company page and extract similar companies.
    Tracxn shows a 'Similar Companies' section without requiring login.
    """
    results = []
    try:
        # Use Google to find the Tracxn page for this company
        query = quote_plus(f"site:tracxn.com {company_name} startup")
        feed_url = (f"https://news.google.com/rss/search?q={query}"
                    f"&hl=en-IN&gl=IN&ceid=IN:en")
        feed  = feedparser.parse(feed_url)
        for entry in feed.entries[:5]:
            link = entry.get('link', '')
            if 'tracxn.com' not in link:
                continue
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36"
            }
            resp = requests.get(link, headers=headers, timeout=12)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for "Similar Companies" or "Competitors" section
            for section in soup.find_all(['section', 'div'],
                                          string=re.compile(r'similar|competitor', re.I)):
                text = section.get_text(' ', strip=True)
                results += _extract_names_from_text(text, seen, max_results=5)
            if results:
                break
            time.sleep(0.5)
    except Exception as exc:
        print(f"[tracxn] error: {exc}")
    return results[:5]


def find_competitors(company_name, sector=''):
    """
    Discover up to 5 competitor company names using these sources in order:
      1. Inc42  — India's top startup database
      2. YourStory — India's top startup media
      3. Wikipedia — global knowledge base
      4. Google News RSS — latest news headlines
      5. Sector-based smart defaults — always returns something useful
    Returns a deduplicated list of up to 5 names.
    """
    competitors = []
    seen = {company_name.lower()}

    # ── Method 1: Inc42 ───────────────────────────────────────────────────────
    try:
        inc42_results = _scrape_inc42(company_name, seen)
        competitors  += inc42_results
        print(f"  Inc42 found: {inc42_results}")
    except Exception as exc:
        print(f"[find_competitors] Inc42 error: {exc}")

    # ── Method 2: YourStory ───────────────────────────────────────────────────
    if len(competitors) < 3:
        try:
            ys_results  = _scrape_yourstory(company_name, seen)
            competitors += ys_results
            print(f"  YourStory found: {ys_results}")
        except Exception as exc:
            print(f"[find_competitors] YourStory error: {exc}")
        time.sleep(0.5)

    # ── Method 3: Wikipedia ───────────────────────────────────────────────────
    if len(competitors) < 3:
        try:
            wiki_results = _wikipedia_competitors(company_name, seen)
            competitors += wiki_results
            print(f"  Wikipedia found: {wiki_results}")
        except Exception as exc:
            print(f"[find_competitors] Wikipedia error: {exc}")

    # ── Method 4: Google News RSS ─────────────────────────────────────────────
    if len(competitors) < 3:
        try:
            query    = quote_plus(f"{company_name} India startup competitor alternative")
            feed_url = (f"https://news.google.com/rss/search?q={query}"
                        f"&hl=en-IN&gl=IN&ceid=IN:en")
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                headline = entry.get('title', '')
                competitors += _extract_names_from_text(
                    headline, seen, max_results=5 - len(competitors)
                )
                if len(competitors) >= 5:
                    break
            time.sleep(0.5)
        except Exception as exc:
            print(f"[find_competitors] Google News error: {exc}")

    # ── Method 5: Sector-based smart defaults ─────────────────────────────────
    if len(competitors) < 3 and sector in SECTOR_DEFAULTS:
        for default in SECTOR_DEFAULTS[sector]:
            if default.lower() not in seen and len(competitors) < 5:
                competitors.append(default)
                seen.add(default.lower())
        print(f"  Sector defaults used for '{sector}'")

    return competitors[:5]


def update_competitors(company_name, new_competitors_str):
    """
    Manually update competitors for a company.
    new_competitors_str: comma-separated string e.g. "Paytm, PhonePe, Razorpay"
    """
    companies = load_companies()
    if company_name not in companies:
        return False
    new_list = [c.strip() for c in new_competitors_str.split(',') if c.strip()]
    companies[company_name]['competitors'] = new_list
    _write_companies(companies)
    return True


# ─── CSV Helpers ──────────────────────────────────────────────────────────────

def load_companies():
    """
    Load companies.csv → returns dict:
      { company_name: {'sector': str, 'competitors': [str, ...]} }

    Handles both formats:
      - Old (unquoted):  Agnikul,SpaceTech,Skyroot Aerospace, Relativity Space, Axiom Space
      - New (quoted):    Agnikul,SpaceTech,"Skyroot Aerospace, Relativity Space, Axiom Space"
    """
    companies = {}
    try:
        with open(COMPANIES_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, None)   # skip header row
            for row in reader:
                if not row:
                    continue
                name   = row[0].strip() if len(row) > 0 else ''
                sector = row[1].strip() if len(row) > 1 else ''
                if not name:
                    continue
                # Everything from column 3 onwards = competitors
                # This handles both "col3, col4, col5" (unquoted) and
                # a single quoted "col3" containing commas (quoted).
                raw_competitors = row[2:]          # list of remaining fields
                competitors = []
                for part in raw_competitors:
                    # Each part may itself be a comma-separated string (quoted CSV)
                    for c in part.split(','):
                        c = c.strip()
                        if c:
                            competitors.append(c)
                companies[name] = {
                    'sector':      sector,
                    'competitors': competitors,
                }
    except FileNotFoundError:
        pass
    return companies


def save_company(name, sector, competitors_list):
    """
    Add or update a company row in companies.csv.
    If the company already exists its sector + competitors are overwritten.
    """
    companies = load_companies()
    companies[name] = {
        'sector':      sector,
        'competitors': competitors_list,
    }
    _write_companies(companies)


def delete_company(name):
    """Remove a company from companies.csv by exact name."""
    companies = load_companies()
    companies.pop(name, None)
    _write_companies(companies)


def _write_companies(companies_dict):
    with open(COMPANIES_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Company Name', 'Sector', 'Competitors'])
        for name, data in companies_dict.items():
            writer.writerow([name, data['sector'], ', '.join(data['competitors'])])


# ── Recipients ────────────────────────────────────────────────────────────────

def load_recipients():
    """Return list of email strings from recipients.csv."""
    recipients = []
    try:
        with open(RECIPIENTS_FILE, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                email = row.get('Email', '').strip()
                if email:
                    recipients.append(email)
    except FileNotFoundError:
        pass
    return recipients


def save_recipient(email):
    """Append an email to recipients.csv (no duplicates)."""
    recipients = load_recipients()
    if email not in recipients:
        recipients.append(email)
    _write_recipients(recipients)


def delete_recipient(email):
    """Remove an email from recipients.csv."""
    recipients = [r for r in load_recipients() if r != email]
    _write_recipients(recipients)


def _write_recipients(recipients_list):
    with open(RECIPIENTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Email'])
        for email in recipients_list:
            writer.writerow([email])
