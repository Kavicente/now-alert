from flask import render_template, request, jsonify, session, redirect, url_for
from flask_socketio import socketio, emit, join_room
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_municipality_from_barangay(barangay):
    from AlertNow import get_municipality_from_barangay
    return get_municipality_from_barangay(barangay)

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

def health_charts():
    if 'role' not in session or session['role'] not in ['health', 'hospital']:
        logger.warning("Unauthorized access to health_charts")
        return redirect(url_for('login_agency'))
    barangays = load_barangays()
    return render_template('HealthCharts.html', barangays=barangays, current_datetime=datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S'))

def health_charts_data():
    try:
        time_filter = request.args.get('time_filter', 'today')
        barangay = request.args.get('barangay', '')
        logger.info(f"Fetching health chart data for time_filter: {time_filter}, barangay: {barangay}")

        conn = get_db_connection()
        current_time = datetime.now(pytz.timezone('Asia/Manila'))
        
        if time_filter == 'today':
            start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = current_time
        elif time_filter == 'daily':
            start_time = current_time - timedelta(days=1)
            end_time = current_time
        elif time_filter == 'weekly':
            start_time = current_time - timedelta(days=7)
            end_time = current_time
        elif time_filter == 'monthly':
            start_time = current_time - timedelta(days=30)
            end_time = current_time
        elif time_filter == 'yearly':
            start_time = current_time - timedelta(days=365)
            end_time = current_time
        else:
            start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = current_time

        query = '''
            SELECT health_type, health_cause, weather, patient_age, patient_gender, barangay
            FROM health_response
            WHERE timestamp BETWEEN ? AND ?
        '''
        params = [start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S')]
        
        if barangay:
            query += ' AND barangay = ?'
            params.append(barangay)

        health_rows = conn.execute(query, params).fetchall()
        conn.close()

        health_type_data = {}
        health_cause_data = {}
        weather_data = {}
        patient_age_data = {}
        patient_gender_data = {}

        for row in health_rows:
            barangay_val = row['barangay'] or 'Unknown'
            health_type = row['health_type'] or 'Unknown'
            health_cause = row['health_cause'] or 'Unknown'
            weather = row['weather'] or 'Unknown'
            patient_age = row['patient_age'] or 'Unknown'
            patient_gender = row['patient_gender'] or 'Unknown'

            health_type_data[health_type] = health_type_data.get(health_type, 0) + 1
            health_cause_data[health_cause] = health_cause_data.get(health_cause, 0) + 1
            weather_data[weather] = weather_data.get(weather, 0) + 1
            patient_age_data[patient_age] = patient_age_data.get(patient_age, 0) + 1
            patient_gender_data[patient_gender] = patient_gender_data.get(patient_gender, 0) + 1

        logger.info(f"Health chart data - Health Type: {health_type_data}, Health Cause: {health_cause_data}, Weather: {weather_data}, Patient Age: {patient_age_data}, Patient Gender: {patient_gender_data}")

        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD', '#D4A5A5', '#9B59B6', '#3498DB']

        chart_data = {
            'health_type': {
                'labels': list(health_type_data.keys()) or ['No Data'],
                'datasets': [{
                    'label': 'Health Emergency Type',
                    'data': list(health_type_data.values()) or [0],
                    'backgroundColor': colors[:len(health_type_data)] or ['#999999'],
                    'borderColor': colors[:len(health_type_data)] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'health_cause': {
                'labels': list(health_cause_data.keys()) or ['No Data'],
                'datasets': [{
                    'label': 'Health Emergency Cause',
                    'data': list(health_cause_data.values()) or [0],
                    'backgroundColor': colors[:len(health_cause_data)] or ['#999999'],
                    'borderColor': colors[:len(health_cause_data)] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'weather': {
                'labels': list(weather_data.keys()) or ['No Data'],
                'datasets': [{
                    'label': 'Weather Conditions',
                    'data': list(weather_data.values()) or [0],
                    'backgroundColor': colors[:len(weather_data)] or ['#999999'],
                    'borderColor': colors[:len(weather_data)] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'patient_age': {
                'labels': list(patient_age_data.keys()) or ['No Data'],
                'datasets': [{
                    'label': 'Patient Age',
                    'data': list(patient_age_data.values()) or [0],
                    'backgroundColor': colors[:len(patient_age_data)] or ['#999999'],
                    'borderColor': colors[:len(patient_age_data)] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'patient_gender': {
                'labels': list(patient_gender_data.keys()) or ['No Data'],
                'datasets': [{
                    'label': 'Patient Gender',
                    'data': list(patient_gender_data.values()) or [0],
                    'backgroundColor': colors[:len(patient_gender_data)] or ['#999999'],
                    'borderColor': colors[:len(patient_gender_data)] or ['#999999'],
                    'borderWidth': 1
                }]
            }
        }
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error in health_charts_data: {e}")
        return jsonify({
            'health_type': {'labels': ['No Data'], 'datasets': [{'label': 'Health Emergency Type', 'data': [0], 'backgroundColor': ['#999999'], 'borderColor': ['#999999'], 'borderWidth': 1}]},
            'health_cause': {'labels': ['No Data'], 'datasets': [{'label': 'Health Emergency Cause', 'data': [0], 'backgroundColor': ['#999999'], 'borderColor': ['#999999'], 'borderWidth': 1}]},
            'weather': {'labels': ['No Data'], 'datasets': [{'label': 'Weather Conditions', 'data': [0], 'backgroundColor': ['#999999'], 'borderColor': ['#999999'], 'borderWidth': 1}]},
            'patient_age': {'labels': ['No Data'], 'datasets': [{'label': 'Patient Age', 'data': [0], 'backgroundColor': ['#999999'], 'borderColor': ['#999999'], 'borderWidth': 1}]},
            'patient_gender': {'labels': ['No Data'], 'datasets': [{'label': 'Patient Gender', 'data': [0], 'backgroundColor': ['#999999'], 'borderColor': ['#999999'], 'borderWidth': 1}]}
        }), 500