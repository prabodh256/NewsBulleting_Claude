#!/usr/bin/env python3
"""
Competitor Tracker — Flask Web Dashboard
Routes: dashboard, add company, edit, delete, recipients, run-now
"""

import os
import subprocess
from flask import (Flask, render_template, request, redirect,
                   url_for, flash)
from dotenv import load_dotenv

load_dotenv()

from agent import (
    search_company, detect_sector, find_competitors,
    save_company, delete_company, load_companies,
    load_recipients, save_recipient, delete_recipient,
    _write_companies,
)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret')


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    companies = load_companies()
    return render_template('index.html', companies=companies)


# ── Add Company (two-phase) ───────────────────────────────────────────────────

@app.route('/add', methods=['GET', 'POST'])
def add():
    results = []
    query   = ''
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            results = search_company(query)
    return render_template('add.html', results=results, query=query)


@app.route('/confirm', methods=['POST'])
def confirm():
    name        = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('No company name received.', 'danger')
        return redirect(url_for('add'))

    sector      = detect_sector(description)
    competitors = find_competitors(name, sector)

    save_company(name, sector, competitors)
    flash(f'"{name}" added — sector: {sector}, {len(competitors)} competitors found.', 'success')
    return redirect(url_for('index'))


# ── Edit (modal form — updates sector + competitors) ─────────────────────────

@app.route('/edit/<path:name>', methods=['POST'])
def edit(name):
    new_sector      = request.form.get('sector', '').strip()
    new_competitors = request.form.get('competitors', '').strip()

    companies = load_companies()
    if name in companies:
        companies[name]['sector']      = new_sector
        companies[name]['competitors'] = [
            c.strip() for c in new_competitors.split(',') if c.strip()
        ]
        _write_companies(companies)
        flash(f'Updated "{name}" successfully.', 'success')
    else:
        flash(f'Company "{name}" not found.', 'danger')

    return redirect(url_for('index'))


# ── Delete Company ────────────────────────────────────────────────────────────

@app.route('/delete/<path:name>', methods=['POST'])
def delete(name):
    delete_company(name)
    flash(f'"{name}" removed.', 'warning')
    return redirect(url_for('index'))


# ── Recipients ────────────────────────────────────────────────────────────────

@app.route('/recipients')
def recipients():
    emails = load_recipients()
    return render_template('recipients.html', recipients=emails)


@app.route('/recipients/add', methods=['POST'])
def recipients_add():
    email = request.form.get('email', '').strip().lower()
    if email and '@' in email:
        save_recipient(email)
        flash(f'{email} added.', 'success')
    else:
        flash('Please enter a valid email address.', 'danger')
    return redirect(url_for('recipients'))


@app.route('/recipients/delete', methods=['POST'])
def recipients_delete():
    email = request.form.get('email', '').strip()
    delete_recipient(email)
    flash(f'{email} removed.', 'warning')
    return redirect(url_for('recipients'))


# ── Run Scraper Now ───────────────────────────────────────────────────────────

@app.route('/run-now', methods=['POST'])
def run_now():
    try:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scraper.py')
        result = subprocess.run(
            ['python3', script],
            capture_output=True, text=True, timeout=300
        )
        output = (result.stdout or '') + (result.stderr or '')
        if result.returncode == 0:
            flash('Scraper finished. Check your inbox!', 'success')
        else:
            flash(f'Scraper exited with errors. Last output: {output[-400:]}', 'danger')
    except subprocess.TimeoutExpired:
        flash('Scraper is still running (timeout 5 min). Check your inbox in a few minutes.', 'warning')
    except Exception as exc:
        flash(f'Could not start scraper: {exc}', 'danger')
    return redirect(url_for('index'))


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
