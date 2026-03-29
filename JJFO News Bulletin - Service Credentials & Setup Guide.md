# JJFO News Bulletin - Service Credentials & Setup Guide

## Overview
This document contains the setup instructions and credentials for all services used in the JJFO News Bulletin system.

---

## 1. NewsAPI Setup

**Service**: NewsAPI (Free Tier)
**Purpose**: Scrape news articles for portfolio companies and competitors
**Free Tier Limit**: 100 requests/day

### Steps:
1. Go to: https://newsapi.org/
2. Click "Get API Key"
3. Sign up with your email
4. Copy your API key
5. Add to GitHub Secrets as: `NEWSAPI_API_KEY`

**API Key**: `[TO BE FILLED]`

---

## 2. Resend.dev Setup

**Service**: Resend (Free Tier)
**Purpose**: Send email digests to investment@jjfo.com
**Free Tier Limit**: 100 emails/day

### Steps:
1. Go to: https://resend.com/
2. Sign up with your email
3. Go to API Keys section
4. Create new API key
5. Copy the key
6. Add to GitHub Secrets as: `RESEND_API_KEY`

**API Key**: `[TO BE FILLED]`

---

## 3. Google Sheets Setup

**Service**: Google Sheets (Free)
**Purpose**: Store companies, competitors, recipients, and dispatch logs

### Step 1: Create Google Sheet
1. Go to: https://sheets.google.com/
2. Create a new spreadsheet named "JJFO News Bulletin"
3. Copy the Sheet ID from URL (between `/d/` and `/edit`)

**Sheet ID**: `[TO BE FILLED]`

### Step 2: Create Sheet Tabs
Rename/create the following tabs:

#### Tab 1: Companies
| Column | Type | Example |
|--------|------|---------|
| Company Name | Text | Agnikul |
| Sector | Text | SpaceTech |
| Competitors | Text | Skyroot Aerospace, Relativity Space |

#### Tab 2: Email_Recipients
| Column | Type | Example |
|--------|------|---------|
| Email | Text | investment@jjfo.com |

#### Tab 3: News_Items
| Column | Type | Example |
|--------|------|---------|
| Headline | Text | Agnikul raises $50M Series B |
| URL | Text | https://... |
| Source | Text | TechCrunch |
| Company | Text | Agnikul |
| Category | Text | portfolio_funding |
| Published_At | DateTime | 2024-03-26T10:00:00Z |

#### Tab 4: Dispatch_Logs
| Column | Type | Example |
|--------|------|---------|
| Timestamp | DateTime | 2024-03-26T08:00:00Z |
| Status | Text | Success |
| Yield | Text | 45 articles |
| Details | JSON | {"timestamp": "..."} |

---

## 4. Google Service Account Setup

**Purpose**: Allow GitHub Actions to read/write to Google Sheets

### Steps:
1. Go to: https://console.cloud.google.com/
2. Create a new project (name: "JJFO News Bulletin")
3. Enable Google Sheets API:
   - Search for "Google Sheets API"
   - Click Enable
4. Create Service Account:
   - Go to "Service Accounts"
   - Click "Create Service Account"
   - Name: "jjfo-news-bulletin"
   - Click Create
5. Create Key:
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Select JSON
   - Download the JSON file
6. Share Google Sheet:
   - Copy the service account email (from JSON: "client_email")
   - Open your Google Sheet
   - Click Share
   - Paste the service account email
   - Give Editor access
7. Add to GitHub Secrets:
   - Copy entire JSON content
   - Add to GitHub Secrets as: `GOOGLE_CREDENTIALS`

**Service Account Email**: `[TO BE FILLED]`

---

## 5. GitHub Setup

**Service**: GitHub (Free)
**Purpose**: Host code and run scheduled scraper via GitHub Actions

### Steps:
1. Go to: https://github.com/
2. Create new repository: "jjfo-news-bulletin"
3. Make it Private (for security)
4. Clone locally and push code
5. Add Secrets:
   - Go to Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `NEWSAPI_KEY`: [Your NewsAPI key]
     - `RESEND_API_KEY`: [Your Resend API key]
     - `GOOGLE_SHEETS_ID`: [Your Sheet ID]
     - `GOOGLE_CREDENTIALS`: [Your Google Service Account JSON]

**Repository**: `https://github.com/[username]/jjfo-news-bulletin`

---

## 6. GitHub Pages Setup (Optional Dashboard)

### Steps:
1. Go to repository Settings
2. Scroll to "Pages" section
3. Select "Deploy from a branch"
4. Select "main" branch
5. Click Save

Dashboard will be available at: `https://[username].github.io/jjfo-news-bulletin/`

---

## 7. Domain Setup (jjfo.in)

**Purpose**: Point your domain to the GitHub Pages dashboard

### Steps:
1. Go to your domain registrar (GoDaddy, Namecheap, etc.)
2. Access DNS settings
3. Add CNAME record:
   - Name: `app` (or `@` for root)
   - Value: `[username].github.io`
4. Add A records (GitHub Pages IPs):
   - 185.199.108.153
   - 185.199.109.153
   - 185.199.110.153
   - 185.199.111.153
5. Wait 24-48 hours for DNS propagation

Dashboard will be available at: `https://app.jjfo.in/` or `https://jjfo.in/`

---

## 8. Credentials Summary

| Service | Account | Key/ID | Status |
|---------|---------|--------|--------|
| NewsAPI | [Email] | [Key] | ⏳ Pending |
| Resend | [Email] | [Key] | ⏳ Pending |
| Google Sheets | [ID] | [ID] | ⏳ Pending |
| Google Service Account | [Email] | [JSON] | ⏳ Pending |
| GitHub | [Username] | [Token] | ⏳ Pending |
| Domain | jjfo.in | CNAME | ⏳ Pending |

---

## 9. Testing

### Manual Test:
```bash
# Run scraper locally
python scraper.py
```

### GitHub Actions Test:
1. Go to repository Actions tab
2. Click "JJFO Daily News Scraper"
3. Click "Run workflow"
4. Check logs for success

### Expected Output:
- Email sent to investment@jjfo.com
- Dispatch log recorded in Google Sheets
- No errors in GitHub Actions logs

---

## 10. Daily Schedule

**Time**: 8:00 AM IST (2:30 AM UTC)
**Frequency**: Every day
**Action**: Scrape news → Categorize → Send email

---

## Support & Troubleshooting

### Email not sending?
- Check Resend API key is correct
- Verify recipient email is in Email_Recipients sheet
- Check GitHub Actions logs for errors

### No news scraped?
- Verify NewsAPI key is correct
- Check company names match exactly in Google Sheets
- Verify NewsAPI free tier limit not exceeded

### GitHub Actions not running?
- Check cron schedule in `.github/workflows/daily-scrape.yml`
- Verify all secrets are set correctly
- Check GitHub Actions is enabled in repository settings

---

**Last Updated**: 2024-03-26
**Version**: 1.0
