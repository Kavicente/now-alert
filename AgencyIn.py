from flask import request, redirect, url_for, render_template, session, jsonify, flash, json
import requests
import sqlite3
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def send_dilg_password(password):
    """Render-proof email sender with fallback"""
    sender = "castillovinceb@gmail.com"
    receiver = "vncbcstll@gmail.com"
    
    # FIXED: Force load from all possible sources
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp-relay.brevo.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USERNAME', 'castillovinceb@gmail.com')  # ← DEFAULT TO YOUR EMAIL
    smtp_pass = os.environ.get('SMTP_PASSWORD', '')  # ← WILL BE SET BY RENDER

    # LOG FOR DEBUGGING — DELETE AFTER IT WORKS
    logger.info(f"SMTP CONFIG: server={smtp_server}, port={smtp_port}, user={smtp_user}, pass={'SET' if smtp_pass else 'MISSING'}")

    if not smtp_pass:
        logger.error("SMTP_PASSWORD is still empty — check Render Environment Variables!")
        return jsonify({'status': 'failed', 'error': 'SMTP_PASSWORD missing'})

    subject = "Your DILG Alert Now Login Password"
    body = f"""
    <h2>DILG Login Access Granted</h2>
    <p>Your temporary password is:</p>
    <h3 style="background:#f0f4f8;padding:15px;border-radius:8px;font-family:monospace;letter-spacing:2px;">
        {password}
    </h3>
    <p>Use this password with your municipality in the DILG login modal.</p>
    <p><small>Generated on {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</small></p>
    <hr>
    <p><em>Alert Now Emergency Response System</em></p>
    """

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        
        logger.info("DILG password sent successfully via Brevo!")
        return jsonify({'status': 'sent'})
        
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return jsonify({'status': 'failed', 'error': str(e)})

def login_agency():
    logger.debug("Accessing /login_agency with method: %s", request.method)
    if request.method == 'POST':
        role = request.form['role'].lower()
        if 'role' not in request.form:
            logger.error("Role field is missing in the form data")
            return "Role is required", 400
        assigned_municipality = request.form['municipality']
        contact_no = request.form['contact_no']
        password = request.form['password']
        assigned_hospital = request.form.get('assigned_hospital', '').lower() if role == 'hospital' else None
        
        if role not in ['cdrrmo', 'pnp', 'bfp', 'city health', 'hospital', 'dilg']:
            logger.error(f"Invalid role provided: {role}")
            return "Invalid role", 400
        
        logger.debug(f"Login attempt: role={role}, municipality={assigned_municipality}, contact_no={contact_no}")
        
        conn = get_db_connection()
        if role == 'dilg':
            # Allow login if password ends with 'DILG!' (generated)
            if password.endswith('DILG!'):
                session['role'] = 'dilg'
                session['municipality'] = assigned_municipality
                session['contact_no'] = 'DILG_ADMIN'
                conn.close()
                return redirect('/dilg_dashboard')
        elif role == 'hospital':
            user = conn.execute('''
                SELECT * FROM users WHERE role = ? AND contact_no = ? AND password = ? AND assigned_municipality = ? AND assigned_hospital = ?
            ''', (role, contact_no, password, assigned_municipality, assigned_hospital)).fetchone()
        else:
            user = conn.execute('''
                SELECT * FROM users WHERE role = ? AND contact_no = ? AND password = ? AND assigned_municipality = ?
            ''', (role, contact_no, password, assigned_municipality)).fetchone()
        conn.close()
        
        if user:
            unique_id = f"{role}_{assigned_municipality}_{contact_no}"
            session['unique_id'] = unique_id
            session['role'] = user['role']
            session['municipality'] = user['assigned_municipality']
            session['assigned_hospital'] = user['assigned_hospital'] if role == 'hospital' else None
            logger.debug(f"Web login successful for user: {unique_id} ({user['role']})")
            if user['role'] == 'cdrrmo':
                return redirect(url_for('cdrrmo_dashboard'))
            elif user['role'] == 'pnp':
                return redirect(url_for('pnp_dashboard'))
            elif user['role'] == 'bfp':
                return redirect(url_for('bfp_dashboard'))
            elif user['role'] == 'city health':
                return redirect(url_for('health_dashboard'))
            elif user['role'] == 'hospital':
                return redirect(url_for('hospital_dashboard'))
        logger.warning(f"Web login failed for assigned_municipality: {assigned_municipality}, contact: {contact_no}, role: {role}")
        return render_template('AgencyIn.html', error="Invalid credentials", cdrrmo_pnp_bfp_users=[])
    
    conn = get_db_connection()
    cdrrmo_pnp_bfp_users = conn.execute('SELECT role, assigned_municipality, contact_no, password, assigned_hospital FROM users WHERE role IN (?, ?, ?, ?, ?)', 
                                        ('cdrrmo', 'pnp', 'bfp', 'city health', 'hospital')).fetchall()
    logger.debug(f"Retrieved {len(cdrrmo_pnp_bfp_users)} users")
    conn.close()
    return render_template('AgencyIn.html', cdrrmo_pnp_bfp_users=cdrrmo_pnp_bfp_users)

def choose_login_type():
    return render_template('LoginType.html')

def go_to_cdrrmopnpin():
    return render_template('AgencyIn.html')