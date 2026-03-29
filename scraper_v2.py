#!/usr/bin/env python3
"""
JJFO News Bulletin v2 - Direct Web Scraper
Scrapes real-time news directly from sources (no 24h delay)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from difflib import SequenceMatcher
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from resend import Resend
import feedparser
from bs4 import BeautifulSoup
import time

RESEND_API_KEY = os.getenv('RESEND_API_KEY')
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
RECIPIENT_EMAIL = 'investment@jjfo.com'

resend = Resend(RESEND_API_KEY)

def get_google_sheets():
    """Connect to Google Sheets"""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEETS_ID)

def get_companies(sheet):
    """Fetch companies from Google Sheets"""
    try:
        companies_sheet = sheet.worksheet('Companies')
        rows = companies_sheet.get_all_records()
        companies = {}
        for row in rows:
            name = row.get('Company Name', '').strip()
            if name:
                companies[name] = {
                    'sector': row.get('Sector', ''),
                    'competitors': [c.strip() for c in row.get('Competitors', '').split(',') if c.strip()]
                }
        return companies
    except:
        return {}

# RSS Feed Sources (Real-time, no API key needed)
RSS_FEEDS = {
    'TechCrunch': 'https://techcrunch.com/feed/',
    'Inc42': 'https://inc42.com/feed/',
    'Economic Times': 'https://economictimes.indiatimes.com/rssfeedstopics.cms?feedtype=json&feed_id=1715249553',
}

# Direct Scraping Sources
SOURCES = {
    'The Ken': 'https://the-ken.com/',
    'VCCircle': 'https://www.vccircle.com/',
    'The Captable': 'https://www.thecaptable.in/',
}

def scrape_rss_feeds(companies):
    """Scrape RSS feeds for real-time news"""
    news_items = defaultdict(list)
    
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:  # Last 20 articles
                headline = entry.get('title', '')
                link = entry.get('link', '')
                
                if not headline or not link:
                    continue
                
                # Check if article mentions any company
                for company_name in companies.keys():
                    if company_name.lower() in headline.lower():
                        news_items[company_name].append({
                            'headline': headline,
                            'url': link,
                            'source': source_name,
                            'published': entry.get('published', datetime.now().isoformat()),
                            'description': entry.get('summary', '')[:200]
                        })
                        break
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
        
        time.sleep(1)  # Rate limiting
    
    return news_items

def scrape_direct_sources(companies):
    """Scrape news directly from sources"""
    news_items = defaultdict(list)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for source_name, source_url in SOURCES.items():
        try:
            response = requests.get(source_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all article links (adjust selectors based on source)
            articles = soup.find_all('a', limit=30)
            
            for article in articles:
                headline = article.get_text(strip=True)
                link = article.get('href', '')
                
                if not headline or not link or len(headline) < 10:
                    continue
                
                # Make relative URLs absolute
                if link.startswith('/'):
                    link = source_url.rstrip('/') + link
                elif not link.startswith('http'):
                    link = source_url.rstrip('/') + '/' + link
                
                # Check if article mentions any company
                for company_name in companies.keys():
                    if company_name.lower() in headline.lower():
                        news_items[company_name].append({
                            'headline': headline,
                            'url': link,
                            'source': source_name,
                            'published': datetime.now().isoformat(),
                            'description': ''
                        })
                        break
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
        
        time.sleep(2)  # Rate limiting
    
    return news_items

def merge_news(rss_news, direct_news):
    """Merge news from all sources"""
    merged = defaultdict(list)
    for company, articles in rss_news.items():
        merged[company].extend(articles)
    for company, articles in direct_news.items():
        merged[company].extend(articles)
    return merged

def categorize_news(news_items, companies):
    """Categorize news by priority"""
    categories = {
        'portfolio_funding': [],
        'competitor_funding': [],
        'portfolio_ma': [],
        'competitor_ma': [],
        'sector_news': [],
        'other': []
    }
    
    keywords = {
        'funding': ['funding', 'raised', 'series', 'investment', 'seed', 'round', 'capital'],
        'ma': ['acquisition', 'acquired', 'merger', 'merged', 'buyout', 'ipo', 'exit'],
        'regulatory': ['regulation', 'compliance', 'policy', 'rbi', 'sebi', 'ban']
    }
    
    for company_name, news_list in news_items.items():
        is_portfolio = company_name in companies
        
        for news in news_list:
            headline_lower = news['headline'].lower()
            
            if any(kw in headline_lower for kw in keywords['funding']):
                if is_portfolio:
                    categories['portfolio_funding'].append(news)
                else:
                    categories['competitor_funding'].append(news)
            elif any(kw in headline_lower for kw in keywords['ma']):
                if is_portfolio:
                    categories['portfolio_ma'].append(news)
                else:
                    categories['competitor_ma'].append(news)
            elif any(kw in headline_lower for kw in keywords['regulatory']):
                categories['sector_news'].append(news)
            else:
                categories['other'].append(news)
    
    return categories

def deduplicate_news(news_list, threshold=0.75):
    """Remove duplicates using headline similarity"""
    unique = []
    seen = []
    
    for news in news_list:
        is_dup = False
        for seen_headline in seen:
            sim = SequenceMatcher(None, news['headline'].lower(), seen_headline.lower()).ratio()
            if sim > threshold:
                is_dup = True
                break
        
        if not is_dup:
            unique.append(news)
            seen.append(news['headline'])
    
    return unique

def format_email(categorized):
    """Format email body"""
    body = "Your daily curated news digest from India's most promising startups.\nStay ahead with the latest funding, M&A, and sector updates.\n\n"
    
    sections = [
        ('FUNDING - PORTFOLIO COMPANIES', 'portfolio_funding'),
        ('FUNDING - COMPETITORS', 'competitor_funding'),
        ('M&A - PORTFOLIO COMPANIES', 'portfolio_ma'),
        ('M&A - COMPETITORS', 'competitor_ma'),
        ('SECTOR NEWS', 'sector_news'),
        ('OTHER NEWS', 'other')
    ]
    
    for title, key in sections:
        news = deduplicate_news(categorized[key])
        if news:
            body += f"\n{title}\n" + "-" * 40 + "\n"
            for item in news[:5]:
                body += f"• {item['headline']}\n  {item['url']}\n\n"
    
    return body

def send_email(body):
    """Send via Resend"""
    try:
        email = resend.emails.send({
            "from": "JJFO News <noreply@jjfo.in>",
            "to": RECIPIENT_EMAIL,
            "subject": f"JJFO News Bulletin - {datetime.now().strftime('%B %d, %Y')}",
            "html": f"<pre>{body}</pre>"
        })
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def log_dispatch(sheet, status, count):
    """Log to Google Sheets"""
    try:
        logs = sheet.worksheet('Dispatch_Logs')
        logs.append_row([datetime.now().isoformat(), status, f"{count} articles", "{}"])
    except:
        pass

def main():
    try:
        print("Starting JJFO News Bulletin v2...")
        sheet = get_google_sheets()
        companies = get_companies(sheet)
        print(f"Found {len(companies)} companies")
        
        # Scrape all sources
        print("Scraping RSS feeds...")
        rss_news = scrape_rss_feeds(companies)
        
        print("Scraping direct sources...")
        direct_news = scrape_direct_sources(companies)
        
        # Merge and process
        all_news = merge_news(rss_news, direct_news)
        total = sum(len(v) for v in all_news.values())
        print(f"Total articles found: {total}")
        
        # Categorize and send
        categorized = categorize_news(all_news, companies)
        body = format_email(categorized)
        
        if send_email(body):
            log_dispatch(sheet, 'Success', total)
            print("Email sent successfully")
        else:
            log_dispatch(sheet, 'Failed', 0)
            print("Email failed")
    
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
