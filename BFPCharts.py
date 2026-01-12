from flask import request, jsonify, render_template, session, redirect, url_for
from flask_socketio import socketio, emit
import sqlite3
import pytz
from datetime import datetime, timedelta
import logging
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def load_barangays():
    barangays_path = os.path.join(os.path.dirname(__file__), 'assets', 'barangay.txt')
    barangays = []
    try:
        with open(barangays_path, 'r') as f:
            for line in f:
                if line.strip():
                    barangays.append(line.strip())
        logger.info(f"Loaded {len(barangays)} barangays from {barangays_path}")
    except FileNotFoundError:
        logger.error(f"Barangay file not found at {barangays_path}")
    except Exception as e:
        logger.error(f"Error loading barangays: {e}")
    return barangays

def get_bfp_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT fire_cause, fire_type, weather, fire_severity, barangay, timestamp
        FROM bfp_response
        WHERE barangay = ?
    '''
    params = [barangay]
    if time_filter == 'today':
        query += " AND date(timestamp) = date(?)"
        params.append(base_time)
    elif time_filter == 'daily':
        query += " AND date(timestamp) = date(?)"
        params.append(base_time)
    elif time_filter == 'weekly':
        query += " AND strftime('%Y-%W', timestamp) = strftime('%Y-%W', ?)"
        params.append(base_time)
    elif time_filter == 'monthly':
        query += " AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', ?)"
        params.append(base_time)
    elif time_filter == 'yearly':
        query += " AND strftime('%Y', timestamp) = strftime('%Y', ?)"
        params.append(base_time)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    causes = {}; types = {}; weathers = {}; severities = {}
    for row in rows:
        causes[row[0]] = causes.get(row[0], 0) + 1
        types[row[1]] = types.get(row[1], 0) + 1
        weathers[row[2]] = weathers.get(row[2], 0) + 1
        severities[row[3]] = severities.get(row[3], 0) + 1

    return {
        
        'cause': {'labels': list(causes.keys()) if causes else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(causes.values()) if causes else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'type': {'labels': list(types.keys()) if types else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(types.values()) if types else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'weather': {'labels': list(weathers.keys()) if weathers else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(weathers.values()) if weathers else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'severity': {'labels': list(severities.keys()) if severities else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(severities.values()) if severities else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]}
    }

def bfp_charts():
    if 'role' not in session or session['role'] != 'bfp':
        logger.warning("Unauthorized access to bfp_charts")
        return redirect(url_for('login'))
    barangays = load_barangays()
    return render_template('BFPCharts.html', barangays=barangays, current_datetime=datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S'))

def bfp_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_bfp_chart_data(time_filter, barangay)
    return jsonify(data)

def handle_bfp_response(data):
    chart_data = get_bfp_chart_data('today', data.get('barangay'))
    socketio.emit('bfp_charts_response_update', chart_data, broadcast=True)