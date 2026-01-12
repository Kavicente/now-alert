from flask import request, jsonify, render_template, Flask, redirect, url_for, flash, session
from flask_socketio import socketio, emit, join_room
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

def get_barangay_chart_data(time_filter):
    from AlertNow import app  # Moved inside function
    conn = get_db_connection()
    conn = conn.cursor()
    query = "SELECT road_accident_cause, road_accident_type, driver_gender, vehicle_type, driver_age, road_condition, timestamp FROM barangay_response"
    manila = pytz.timezone('Asia/Manila')
    base_time = datetime.now(pytz.timezone('Asia/Manila'))
    if time_filter == 'today':
        conn.execute(query + " WHERE date(timestamp) = date(?)", (base_time.strftime('%Y-%m-%d'),))
    elif time_filter == 'daily':
        conn.execute(query + " GROUP BY date(timestamp)")
    elif time_filter == 'weekly':
        conn.execute(query + " GROUP BY strftime('%Y-%W', timestamp)")
    elif time_filter == 'monthly':
        conn.execute(query + " GROUP BY strftime('%Y-%m', timestamp)")
    elif time_filter == 'yearly':
        conn.execute(query + " GROUP BY strftime('%Y', timestamp)")
    rows = conn.fetchall()
    conn.close()

    causes = {}
    types = {}
    genders = {}
    vehicles = {}
    ages = {}
    conditions = {}
    for row in rows:
        causes[row[0]] = causes.get(row[0], 0) + 1
        types[row[1]] = types.get(row[1], 0) + 1
        genders[row[2]] = genders.get(row[2], 0) + 1
        vehicles[row[3]] = vehicles.get(row[3], 0) + 1
        ages[row[4]] = ages.get(row[4], 0) + 1
        conditions[row[5]] = conditions.get(row[5], 0) + 1

    return {
        'cause': {'labels': list(causes.keys()), 'datasets': [{'label': 'Count', 'data': list(causes.values()), 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'type': {'labels': list(types.keys()), 'datasets': [{'label': 'Count', 'data': list(types.values()), 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'gender': {'labels': list(genders.keys()), 'datasets': [{'label': 'Count', 'data': list(genders.values()), 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'vehicle': {'labels': list(vehicles.keys()), 'datasets': [{'label': 'Count', 'data': list(vehicles.values()), 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]},
        'age': {'labels': list(ages.keys()), 'datasets': [{'label': 'Count', 'data': list(ages.values()), 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'condition': {'labels': list(conditions.keys()), 'datasets': [{'label': 'Count', 'data': list(conditions.values()), 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]}
    }


def get_barangay_fire_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT fire_cause, fire_type, weather, fire_severity, barangay
        FROM barangay_fire_response
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

    causes = {}; types = {}; weathers = {}; severities = {}; barangays = {}
    for row in rows:
        causes[row[0]] = causes.get(row[0], 0) + 1
        types[row[1]] = types.get(row[1], 0) + 1
        weathers[row[2]] = weathers.get(row[2], 0) + 1
        severities[row[3]] = severities.get(row[3], 0) + 1
        barangays[row[4]] = barangays.get(row[4], 0) + 1

    return {
        'cause': {'labels': list(causes.keys()) if causes else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(causes.values()) if causes else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'type': {'labels': list(types.keys()) if types else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(types.values()) if types else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'weather': {'labels': list(weathers.keys()) if weathers else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(weathers.values()) if weathers else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'severity': {'labels': list(severities.keys()) if severities else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(severities.values()) if severities else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]},
        'barangay': {'labels': list(barangays.keys()) if barangays else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(barangays.values()) if barangays else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]}
    }

def get_barangay_health_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT barangay, health_type, health_cause, weather, patient_age, patient_gender
        FROM (
            SELECT barangay, health_type, health_cause, weather, patient_age, patient_gender,timestamp
            FROM health_response
            WHERE barangay = ?
            UNION ALL
            SELECT barangay, health_type, health_cause, weather, patient_age, patient_gender,  timestamp
            FROM barangay_health_response
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

    barangays = {}; health_types = {}; health_causes = {}; weathers = {}; ages = {}; genders = {}; responders = {}
    for row in rows:
        barangays[row[0]] = barangays.get(row[0], 0) + 1
        health_types[row[1]] = health_types.get(row[1], 0) + 1
        health_causes[row[2]] = health_causes.get(row[2], 0) + 1
        weathers[row[3]] = weathers.get(row[3], 0) + 1
        ages[row[4]] = ages.get(row[4], 0) + 1
        genders[row[5]] = genders.get(row[5], 0) + 1

    return {
        'barangay': {'labels': list(barangays.keys()) if barangays else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(barangays.values()) if barangays else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'health_type': {'labels': list(health_types.keys()) if health_types else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(health_types.values()) if health_types else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'health_cause': {'labels': list(health_causes.keys()) if health_causes else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(health_causes.values()) if health_causes else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']}]},
        'weather': {'labels': list(weathers.keys()) if weathers else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(weathers.values()) if weathers else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'patient_age': {'labels': list(ages.keys()) if ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(ages.values()) if ages else [0], 'backgroundColor': ['#36A2EB', '#FF6384', '#FFCE56', '#4BC0C0', '#9966FF'], 'borderColor': '#FF6384', 'fill': False}]},
        'patient_gender': {'labels': list(genders.keys()) if genders else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(genders.values()) if genders else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]}
    }
    
def get_barangay_crime_chart_data(time_filter, barangay=None):
    conn = get_db_connection()
    c = conn.cursor()
    manila = pytz.timezone('Asia/Manila')
    now = datetime.now(manila)
    base_time = now.strftime('%Y-%m-%d')
    query = '''
        SELECT crime_type, crime_cause, level, suspect_gender, victim_gender, suspect_age, victim_age, barangay, timestamp
        FROM barangay_crime_response
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
        'level': {'labels': list(levels.keys()) if levels else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(levels.values()) if levels else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']}]},
        'suspect_gender': {'labels': list(suspect_genders.keys()) if suspect_genders else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(suspect_genders.values()) if suspect_genders else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'victim_gender': {'labels': list(victim_genders.keys()) if victim_genders else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(victim_genders.values()) if victim_genders else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']}]},
        'suspect_age': {'labels': list(suspect_ages.keys()) if suspect_ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(suspect_ages.values()) if suspect_ages else [0], 'backgroundColor':['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]},
        'victim_age': {'labels': list(victim_ages.keys()) if victim_ages else ['No Data'], 'datasets': [{'label': 'Count', 'data': list(victim_ages.values()) if victim_ages else [0], 'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']}]}
    }
        
def barangay_charts():
    if 'role' not in session or session['role'] != 'barangay':
        logger.warning("Unauthorized access to barangay_charts")
        return redirect(url_for('login'))
    barangays = load_barangays()
    return render_template('BarangayCharts.html', barangays=barangays, current_datetime=datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S'))
def barangay_charts_data():
    from AlertNow import app  # Moved inside function
    time_filter = request.args.get('time_filter', 'today')
    data = get_barangay_chart_data(time_filter)
    return jsonify(data)

def handle_barangay_response(data):
    from AlertNow import socketio, app  # Moved inside function
    # Simulate database update and emit update
    chart_data = get_barangay_chart_data('today')
    socketio.emit('barangay_response_update', chart_data, broadcast=True)
    
def barangay_fire_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_barangay_fire_chart_data(time_filter, barangay)
    return jsonify(data)

def barangay_health_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_barangay_health_chart_data(time_filter, barangay)
    return jsonify(data)

def barangay_crime_charts_data():
    time_filter = request.args.get('time_filter', 'today')
    barangay = request.args.get('barangay')
    data = get_barangay_crime_chart_data(time_filter, barangay)
    return jsonify(data)

def handle_barangay_response(data):
    from AlertNow import socketio, app
    chart_data = get_barangay_chart_data('today', data.get('barangay'))
    socketio.emit('barangay_response_update', chart_data, broadcast=True)

def handle_barangay_fire_response(data):
    from AlertNow import socketio, app
    chart_data = get_barangay_fire_chart_data('today', data.get('barangay'))
    socketio.emit('bfp_response_update', chart_data, broadcast=True)

def handle_barangay_health_response(data):
    from AlertNow import socketio, app
    chart_data = get_barangay_health_chart_data('today', data.get('barangay'))
    socketio.emit('barangay_health_response_update', chart_data, broadcast=True)

def handle_barangay_crime_response(data):
    from AlertNow import socketio, app
    chart_data = get_barangay_crime_chart_data('today', data.get('barangay'))
    socketio.emit('barangay_crime_response_update', chart_data, broadcast=True)