from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file, make_response
import sqlite3
import pytz
from datetime import datetime
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

def get_cdrrmo_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT road_accident_cause, road_accident_type, driver_gender, vehicle_type, driver_age, road_condition, barangay, timestamp
        FROM (
            SELECT road_accident_cause, road_accident_type, driver_gender, vehicle_type, driver_age, road_condition, barangay, timestamp
            FROM barangay_response
            WHERE barangay = ?
            UNION ALL
            SELECT road_accident_cause, road_accident_type, driver_gender, vehicle_type, driver_age, road_condition, barangay, timestamp
            FROM cdrrmo_response
            WHERE barangay = ?
            UNION ALL
            SELECT road_accident_cause, road_accident_type, driver_gender, vehicle_type, driver_age, road_condition, barangay, timestamp
            FROM pnp_response
            WHERE barangay = ?
        )
    '''
    params = [barangay, barangay, barangay]
    if time_filter == 'today':
        query += " WHERE date(timestamp) = date(?)"
        params.append(base_time)
    elif time_filter == 'daily':
        query += " WHERE date(timestamp) = date(?)"
        params.append(base_time)
    elif time_filter == 'weekly':
        query += " WHERE strftime('%Y-%W', timestamp) = strftime('%Y-%W', ?)"
        params.append(base_time)
    elif time_filter == 'monthly':
        query += " WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', ?)"
        params.append(base_time)
    elif time_filter == 'yearly':
        query += " WHERE strftime('%Y', timestamp) = strftime('%Y', ?)"
        params.append(base_time)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    causes = {}; types = {}; genders = {}; vehicles = {}; ages = {}; conditions = {}; barangays = {}
    for row in rows:
        causes[row[0]] = causes.get(row[0], 0) + 1
        types[row[1]] = types.get(row[1], 0) + 1
        genders[row[2]] = genders.get(row[2], 0) + 1
        vehicles[row[3]] = vehicles.get(row[3], 0) + 1
        ages[row[4]] = ages.get(row[4], 0) + 1
        conditions[row[5]] = conditions.get(row[5], 0) + 1
        barangays[row[6]] = barangays.get(row[6], 0) + 1

    return {
        'barangay': {'labels': list(barangays.keys()) if barangays else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(barangays.values()) if barangays else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'cause': {'labels': list(causes.keys()) if causes else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(causes.values()) if causes else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'type': {'labels': list(types.keys()) if types else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(types.values()) if types else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'gender': {'labels': list(genders.keys()) if genders else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(genders.values()) if genders else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'vehicle': {'labels': list(vehicles.keys()) if vehicles else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(vehicles.values()) if vehicles else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]},
        'age': {'labels': list(ages.keys()) if ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(ages.values()) if ages else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'condition': {'labels': list(conditions.keys()) if conditions else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(conditions.values()) if conditions else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]}
    }

def cdrrmo_charts():
    if 'role' not in session or session['role'] != 'cdrrmo':
        logger.warning("Unauthorized access to cdrrmo_charts")
        return redirect(url_for('login'))
    barangays = load_barangays()
    return render_template('CDRRMOCharts.html', barangays=barangays, current_datetime=datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S'))

def cdrrmo_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_cdrrmo_chart_data(time_filter, barangay)
    return jsonify(data)

def handle_cdrrmo_response(data):
    from AlertNow import socketio, app  # Moved inside function
    chart_data = get_cdrrmo_chart_data('today', data.get('barangay'))
    socketio.emit('cdrrmo_response_update', chart_data, broadcast=True)