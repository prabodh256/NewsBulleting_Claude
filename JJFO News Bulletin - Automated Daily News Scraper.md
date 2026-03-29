# JJFO News Bulletin - Automated Daily News Scraper

**Real-time news scraping from 16 premium Indian startup news sources, delivered to your inbox every morning at 8 AM IST.**

## Features

✅ **16 Premium News Sources** - YourStory, Inc42, Entrackr, VCCircle, StartupTalky, IndianWeb2, TechCircle, The Ken, Analytics India, BW Disrupt, TechCrunch, Economic Times, Inc42 Plus, Moneycontrol, Business Standard, Livemint
✅ **Real-time Web Scraping** - No 24-hour delays
✅ **Completely Free** - No credit card needed
✅ **Fully Automatic** - Runs daily at 8 AM IST
✅ **CSV-Based** - Simple, no database needed
✅ **Categorized News** - Funding → M&A → Sector → Other
✅ **Duplicate Removal** - Smart headline matching

## News Sources

### RSS Feeds (12 sources - Real-time)
- **YourStory** - Indian startup ecosystem coverage
- **Inc42** - Venture capital and startup news
- **Entrackr** - Startup funding and exits
- **VCCircle** - VC, M&A, and funding
- **StartupTalky** - Startup stories and founders
- **IndianWeb2** - Indian internet and startups
- **TechCircle** - Technology startups and VC
- **The Ken** - Deep-dive business analysis
- **Analytics India Magazine** - AI and data science startups
- **BW Disrupt** - Disruptive startups and innovation
- **TechCrunch** - Global tech and startup news
- **Economic Times** - Business and startup coverage

### Direct Web Scraping (4 sources - Real-time)
- **Inc42 Plus** - Premium startup analysis
- **Moneycontrol Startups** - Startup news and IPOs
- **Business Standard Startups** - Startup business news
- **Livemint Startups** - Startup ecosystem coverage

## How It Works

1. **Daily Trigger** - GitHub Actions runs at 8 AM IST
2. **Scraping** - Collects news from 16 sources
3. **Matching** - Finds articles mentioning your companies
4. **Categorizing** - Prioritizes by funding, M&A, sector news
5. **Deduplication** - Removes similar articles
6. **Email** - Sends formatted digest via Resend
7. **Logging** - Records activity in dispatch_log.csv

## Email Format

```
Subject: JJFO News Bulletin - [Date]

Your daily curated news digest from India's most promising startups.
Stay ahead with the latest funding, M&A, and sector updates.

FUNDING - PORTFOLIO COMPANIES
• [Headline] - [Link]

FUNDING - COMPETITORS
• [Headline] - [Link]

M&A - PORTFOLIO COMPANIES
• [Headline] - [Link]

M&A - COMPETITORS
• [Headline] - [Link]

SECTOR NEWS
• [Headline] - [Link]

OTHER NEWS
• [Headline] - [Link]
```

## Quick Start (7 Steps, ~20 minutes)

### Step 1: Create Resend Account
- Go to https://resend.com/
- Sign up → Create API Key
- Copy the key

### Step 2: Create GitHub Repository
- Go to https://github.com/
- Create new private repo: "jjfo-news-bulletin"
- Clone to your computer

### Step 3: Add Project Files
- Copy all files to your repo
- Commit and push

### Step 4: Add GitHub Secret
- Settings → Secrets and variables → Actions
- Add secret: RESEND_API_KEY = [Your Resend key]

### Step 5: Customize Companies
- Edit companies.csv
- Add your 60+ companies
- Commit and push

### Step 6: Customize Recipients
- Edit recipients.csv
- Add email addresses
- Commit and push

### Step 7: Test
- Go to Actions tab
- Run workflow manually
- Check email (may take 2-3 minutes due to 16 sources)

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | Main scraping logic (16 sources) |
| `companies.csv` | Portfolio companies + competitors |
| `recipients.csv` | Email recipients |
| `dispatch_log.csv` | Daily execution logs |
| `requirements.txt` | Python dependencies |
| `.github/workflows/daily-scrape.yml` | GitHub Actions schedule |
| `DEPLOY.txt` | Deployment guide |
| `README.md` | This file |

## Configuration

### companies.csv
```
Company Name,Sector,Competitors
Agnikul,SpaceTech,Skyroot Aerospace, Relativity Space
Zouk,FinTech,Razorpay, Instamojo
```

### recipients.csv
```
Email
investment@jjfo.com
another@example.com
```

## Customization

### Change Time
Edit `.github/workflows/daily-scrape.yml`:
```yaml
- cron: '30 2 * * *'  # 8 AM IST
```

### Add News Source
Edit `scraper.py`:
```python
RSS_FEEDS = {
    'Source Name': 'https://source-url.com/feed',
}
```

### Change Email Format
Edit `scraper.py` function `format_email()`

## Troubleshooting

### Email not received?
- Check GitHub Actions logs
- Verify Resend API key
- Check recipients.csv
- Check spam folder
- Note: Scraping 16 sources takes 2-3 minutes

### No articles found?
- Check company names in companies.csv
- Verify RSS feeds are working
- Check GitHub Actions logs

### GitHub Actions not running?
- Verify cron schedule
- Check secrets are set
- Check GitHub Actions is enabled

### Scraper timing out?
- Scraping 16 sources takes 2-3 minutes
- GitHub Actions has 35-minute timeout (safe)
- Check internet connection if timeout occurs

## Cost

| Service | Limit | Your Usage | Cost |
|---------|-------|-----------|------|
| GitHub Actions | 2000 min/month | ~3 min/day = 90 min/month | FREE |
| Resend Email | 100 emails/day | 1 email/day | FREE |
| RSS Feeds | Unlimited | 12 feeds/day | FREE |
| Web Scraping | Unlimited | 4 sources/day | FREE |
| **TOTAL** | | | **$0/month** |

## Daily Workflow

```
8:00 AM IST
    ↓
GitHub Actions Triggers
    ↓
Scraper Runs
├─ Scrapes 12 RSS feeds
├─ Scrapes 4 web sources
└─ Finds matching articles
    ↓
Categorizes News
    ├─ Portfolio funding
    ├─ Competitor funding
    ├─ M&A news
    ├─ Sector news
    └─ Other news
    ↓
Removes Duplicates
    ↓
Formats Email
    ↓
Sends via Resend
    ↓
Logs to dispatch_log.csv
    ↓
Done!
```

## Requirements

- Python 3.7+
- GitHub account (free)
- Resend account (free)
- Internet connection

## Dependencies

- requests
- beautifulsoup4
- feedparser
- resend

Install: `pip install -r requirements.txt`

## License

MIT

## Support

See DEPLOY.txt for detailed setup instructions.

---

**Version**: 3.1 (16 Premium News Sources)
**Created**: 2024-03-26
**Status**: Production Ready
**Total Cost**: $0/month
