#!/usr/bin/env python3
"""
Competitor Tracker — Flask Web Dashboard
Handles: add companies (with AI disambiguation), manage recipients, run scraper on demand.
"""

import os
import subprocess
import sys
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

from agent import (
    search_company,
    detect_sector,
    find_competitors,
    load_companies,
    save_company,
    delete_company,
    update_competitors,
    load_recipients,
    save_recipient,
    delete_recipient,
)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-me-to-something-random-123')

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    companies = load_companies()
    return render_template('index.html', companies=companies)


# ─── Add Company (two-phase: search → confirm) ────────────────────────────────

@app.route('/add', methods=['GET'])
def add_get():
    """Phase 1: show empty search form."""
    return render_template('add.html', query=None, results=None)


@app.route('/add', methods=['POST'])
def add_post():
    """Phase 1 submit: run disambiguation search, show options."""
    name = request.form.get('company_name', '').strip()
    if not name:
        flash('Please enter a company name.', 'warning')
        return redirect(url_for('add_get'))

    results = search_company(name)
    return render_template('add.html', query=name, results=results)


@app.route('/confirm', methods=['POST'])
def confirm():
    """
    Phase 2 submit: user picked one result (or typed a manual name).
    Auto-detect sector from its description, auto-find competitors, save.
    """
    chosen_name = request.form.get('chosen_name', '').strip()
    description = request.form.get('description', '').strip()
    manual_name = request.form.get('manual_name', '').strip()

    # If user selected "None of these", use the manually typed name
    if chosen_name == '__manual__':
        chosen_name = manual_name

    if not chosen_name:
        flash('No company selected — please try again.', 'warning')
        return redirect(url_for('add_get'))

    # Check if already tracked
    existing = load_companies()
    if chosen_name in existing:
        flash(f'"{chosen_name}" is already in your tracker.', 'info')
        return redirect(url_for('index'))

    # Auto-detect sector from the DuckDuckGo description
    sector = detect_sector(description)

    # Auto-find up to 5 competitors
    flash(f'Finding competitors for {chosen_name}… this takes ~10 seconds.', 'info')
    competitors = find_competitors(chosen_name, sector)

    save_company(chosen_name, sector, competitors)

    comp_str = ', '.join(competitors) if competitors else 'none found'
    flash(
        f'✅ Added <strong>{chosen_name}</strong> '
        f'(Sector: {sector}) — Competitors: {comp_str}',
        'success'
    )
    return redirect(url_for('index'))


# ─── Edit Company ─────────────────────────────────────────────────────────────

@app.route('/edit/<path:name>', methods=['POST'])
def edit(name):
    new_sector      = request.form.get('sector', '').strip()
    new_competitors = request.form.get('competitors', '').strip()
    companies = load_companies()
    if name in companies:
        companies[name]['sector']      = new_sector
        companies[name]['competitors'] = [c.strip() for c in new_competitors.split(',') if c.strip()]
        from agent import _write_companies
        _write_companies(companies)
        flash(f'Updated "{name}" successfully.', 'success')
    else:
        flash(f'Company "{name}" not found.', 'warning')
    return redirect(url_for('index'))


# ─── Delete Company ───────────────────────────────────────────────────────────

@app.route('/delete/<path:name>', methods=['POST'])
def delete(name):
    delete_company(name)
    flash(f'Deleted "{name}".', 'info')
    return redirect(url_for('index'))


# ─── Recipients ───────────────────────────────────────────────────────────────

@app.route('/recipients')
def recipients():
    emails = load_recipients()
    return render_template('recipients.html', recipients=emails)


@app.route('/recipients/add', methods=['POST'])
def recipients_add():
    email = request.form.get('email', '').strip().lower()
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'warning')
        return redirect(url_for('recipients'))
    save_recipient(email)
    flash(f'Added {email} to recipients.', 'success')
    return redirect(url_for('recipients'))


@app.route('/recipients/delete', methods=['POST'])
def recipients_delete():
    email = request.form.get('email', '').strip()
    delete_recipient(email)
    flash(f'Removed {email} from recipients.', 'info')
    return redirect(url_for('recipients'))


# ─── Run Scraper Manually ─────────────────────────────────────────────────────

@app.route('/run-now', methods=['POST'])
def run_now():
    """Trigger scraper.py in a subprocess and flash its output."""
    try:
        scraper_path = os.path.join(os.path.dirname(__file__), 'scraper.py')
        result = subprocess.run(
            [sys.executable, scraper_path],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=os.path.dirname(__file__),
        )
        output = (result.stdout or '') + (result.stderr or '')
        output = output.strip()[:500] or 'Scraper finished with no output.'
        flash(f'Scraper ran: {output}', 'info')
    except subprocess.TimeoutExpired:
        flash('Scraper timed out after 3 minutes.', 'warning')
    except Exception as exc:
        flash(f'Error running scraper: {exc}', 'danger')

    return redirect(url_for('index'))


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Local dev only — PythonAnywhere uses wsgi.py
    app.run(debug=True, port=5000)
