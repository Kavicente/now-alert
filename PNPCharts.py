from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file, make_response
from flask_socketio import SocketIO, emit, join_room
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

def get_pnp_chart_data(time_filter, barangay=None):
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
            FROM pnp_response
            WHERE barangay = ?
        )
    '''
    params = [barangay, barangay]
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
        'age': {'labels': list(ages.keys()) if ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(ages.values()) if ages else [0], 'backgroundColor': '#36A2EB', 'borderColor': '#FF6384', 'fill': False}]},
        'condition': {'labels': list(conditions.keys()) if conditions else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(conditions.values()) if conditions else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]}
    }

def get_pnp_fire_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT fire_type, fire_cause, fire_severity, barangay, timestamp
        FROM (
            SELECT fire_type, fire_cause, fire_severity, barangay, timestamp
            FROM barangay_fire_response
            WHERE barangay = ?
            UNION ALL
            SELECT fire_type, fire_cause, fire_severity, barangay, timestamp
            FROM pnp_fire_response
            WHERE barangay = ?
        )
    '''
    params = [barangay, barangay]
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

    fire_types = {}; fire_causes = {}; fire_severities = {}; barangays = {}
    for row in rows:
        fire_types[row[0]] = fire_types.get(row[0], 0) + 1
        fire_causes[row[1]] = fire_causes.get(row[1], 0) + 1
        fire_severities[row[2]] = fire_severities.get(row[2], 0) + 1
        barangays[row[3]] = barangays.get(row[3], 0) + 1

    return {
        'barangay': {'labels': list(barangays.keys()) if barangays else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(barangays.values()) if barangays else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'fire_type': {'labels': list(fire_types.keys()) if fire_types else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(fire_types.values()) if fire_types else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'fire_cause': {'labels': list(fire_causes.keys()) if fire_causes else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(fire_causes.values()) if fire_causes else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'fire_severity': {'labels': list(fire_severities.keys()) if fire_severities else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(fire_severities.values()) if fire_severities else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]}
    }

def get_pnp_crime_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT crime_type, crime_cause, level, suspect_gender, victim_gender, suspect_age, victim_age, barangay, timestamp
        FROM (
            SELECT crime_type, crime_cause, level, suspect_gender, victim_gender, suspect_age, victim_age, barangay, timestamp
            FROM barangay_crime_response
            WHERE barangay = ?
            UNION ALL
            SELECT crime_type, crime_cause, level, suspect_gender, victim_gender, suspect_age, victim_age, barangay, timestamp
            FROM pnp_crime_response
            WHERE emergency_type = ?
        )
    '''
    params = [barangay, barangay]
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

    crime_types = {}; crime_causes = {}; levels = {}; suspect_genders = {}; victim_genders = {}; suspect_ages = {}; victim_ages = {}; barangays = {}
    for row in rows:
        crime_types[row[0]] = crime_types.get(row[0], 0) + 1
        crime_causes[row[1]] = crime_causes.get(row[1], 0) + 1
        levels[row[2]] = levels.get(row[2], 0) + 1
        suspect_genders[row[3]] = suspect_genders.get(row[3], 0) + 1
        victim_genders[row[4]] = victim_genders.get(row[4], 0) + 1
        suspect_ages[row[5]] = suspect_ages.get(row[5], 0) + 1
        victim_ages[row[6]] = victim_ages.get(row[6], 0) + 1
        barangays[row[7]] = barangays.get(row[7], 0) + 1

    return {
        'barangay': {'labels': list(barangays.keys()) if barangays else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(barangays.values()) if barangays else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'crime_type': {'labels': list(crime_types.keys()) if crime_types else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(crime_types.values()) if crime_types else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'crime_cause': {'labels': list(crime_causes.keys()) if crime_causes else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(crime_causes.values()) if crime_causes else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'level': {'labels': list(levels.keys()) if levels else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(levels.values()) if levels else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'suspect_gender': {'labels': list(suspect_genders.keys()) if suspect_genders else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(suspect_genders.values()) if suspect_genders else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'victim_gender': {'labels': list(victim_genders.keys()) if victim_genders else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(victim_genders.values()) if victim_genders else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'suspect_age': {'labels': list(suspect_ages.keys()) if suspect_ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(suspect_ages.values()) if suspect_ages else [0], 'backgroundColor':['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'victim_age': {'labels': list(victim_ages.keys()) if victim_ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(victim_ages.values()) if victim_ages else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]}
    }

def pnp_charts():
    if 'role' not in session or session['role'] != 'pnp':
        logger.warning("Unauthorized access to pnp_charts")
        return redirect(url_for('login'))
    barangays = load_barangays()
    return render_template('PNPCharts.html', barangays=barangays, current_datetime=datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S'))

def pnp_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_pnp_chart_data(time_filter, barangay)
    return jsonify(data)

def pnp_fire_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_pnp_fire_chart_data(time_filter, barangay)
    return jsonify(data)

def pnp_crime_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_pnp_crime_chart_data(time_filter, barangay)
    return jsonify(data)

def handle_pnp_response(data):
    from AlertNow import socketio, app
    chart_data = get_pnp_chart_data('today', data.get('barangay'))
    socketio.emit('pnp_response_update', chart_data, broadcast=True)

def handle_pnp_fire_response(data):
    from AlertNow import socketio, app
    chart_data = get_pnp_fire_chart_data('today', data.get('barangay'))
    socketio.emit('pnp_fire_response_update', chart_data, broadcast=True)

def handle_pnp_crime_response(data):
    from AlertNow import socketio, app
    chart_data = get_pnp_crime_chart_data('today', data.get('barangay'))
    socketio.emit('pnp_crime_response_update', chart_data, broadcast=True)