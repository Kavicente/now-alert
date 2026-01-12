from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file, make_response, flash

from flask_socketio import SocketIO, emit, join_room

import logging

import ast

import os

import json

import sqlite3

import numpy as np

import random

from collections import Counter

from datetime import datetime, timedelta

import pytz

import pandas as pd

from sklearn.preprocessing import OneHotEncoder, StandardScaler


from sklearn.pipeline import Pipeline

import uuid

import random


from road_models import (arima_pred, arima_22, arima_m,
                         arimax_pred, arimax_22, arimax_m,
                         sarima_pred, sarima_22, sarima_m,
                         sarimax_pred, sarimax_22, sarimax_m)

from fire_models import(f_arima_22, f_arima_m, f_arima_pred,
                f_arimax_22, f_arimax_m, f_arimax_pred,
                f_sarima_22, f_sarima_m, f_sarima_pred,
                f_sarimax_22, f_sarimax_m, f_sarimax_pred)


from models import (road_accident_predictor, 
                    fire_accident_predictor, crime_predictor, 
                    health_predictor, birth_predictor)

from AgencyIn import send_dilg_password

from SignUpType import download_apk_folder, generate_qr

from BarangayDashboard import (get_barangay_stats, get_latest_alert, get_the_stats, get_new_alert, 
                               
                               get_barangay_emergency_types, get_barangay_responded_count, emit_emergency_types_update)

from CDRRMODashboard import (get_cdrrmo_stats, get_latest_alert, get_the_cdrrmo_stats, get_cdrrmo_new_alert, 
                             get_cdrrmo_alerts_per_month, get_cdrrmo_responded_count, emit_cdrrmo_alerts_per_month_update)

from PNPDashboard import (get_pnp_stats, get_latest_alert, get_the_pnp_stats, get_pnp_new_alert, get_pnp_alerts_per_month, 
                          get_pnp_responded_count, emit_pnp_alerts_per_month_update)

from BFPDashboard import (get_bfp_stats, get_latest_alert, get_the_stat_bfp, get_bfp_alerts_per_month, 
                          get_bfp_responded_count, emit_bfp_alerts_per_month_update)

from HealthDashboard import get_health_stats, get_latest_alert

from HospitalDashboard import get_hospital_stats, get_latest_alert

from BarangayCharts import (barangay_charts, barangay_charts_data, get_barangay_chart_data, barangay_fire_charts_data, 
                            barangay_health_charts_data, get_barangay_health_chart_data, barangay_crime_charts_data)

from CDRRMOCharts import cdrrmo_charts, cdrrmo_charts_data, get_cdrrmo_chart_data

from PNPCharts import pnp_charts, pnp_charts_data, get_pnp_chart_data, pnp_fire_charts_data, pnp_crime_charts_data

from BFPCharts import bfp_charts, bfp_charts_data, get_bfp_chart_data

from HealthCharts import health_charts, health_charts_data

from HospitalCharts import hospital_charts, hospital_charts_data

from dataset import road_accident_df, fire_incident_df, health_emergencies_df, crime_df

import smtplib

import joblib

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart

from google.oauth2 import service_account

import secrets

from PassReset import pass_reset

from DILGDashboard import (dilg_dashboard, dilg_data, dilg_accounts, dilg_update_account, dilg_delete_account, 
                           dilg_delete_all, dilg_warn_account, dilg_barangays, dilg_barangay_report, dilg_cdrrmo_report,
                           dilg_bfp_report, dilg_health_report, dilg_pnp_report)

from submission import (handle_barangay_response_submitted, handle_barangay_arimax_submitted, handle_barangay_sarima_submitted,
                        handle_barangay_sarimax_submitted, handle_barangay_fire_submitted, handle_barangay_fire_arimax, handle_barangay_fire_sarima,
                        handle_barangay_fire_sarimax, handle_barangay_crime_submitted, handle_barangay_health_response,
                        handle_cdrrmo_response_submitted, handle_pnp_response_submitted, handle_pnp_fire_submitted,
                        handle_pnp_crime_submitted, handle_fire_response_submitted, handle_health_response, handle_hospital_response)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*", max_http_buffer_size=10000000)

alerts = []
responses = []
today_responses = []
pending_alerts = []
accepted_roles = {}

app.add_url_rule('/dilg_dashboard', 'dilg_dashboard', dilg_dashboard)
app.add_url_rule('/dilg_data', 'dilg_data', dilg_data)
app.add_url_rule('/dilg_accounts', 'dilg_accounts', dilg_accounts)
app.add_url_rule('/dilg_delete_account/<contact>', 'dilg_delete_account', dilg_delete_account, methods=['DELETE'])
app.add_url_rule('/dilg_delete_all/<role_type>', 'dilg_delete_all', dilg_delete_all, methods=['DELETE'])
app.add_url_rule('/dilg_warn_account', 'dilg_warn_account', dilg_warn_account, methods=['POST'])
app.add_url_rule('/dilg_barangays', 'dilg_barangays', dilg_barangays)
app.add_url_rule('/dilg_barangay_report', 'dilg_barangay_report', dilg_barangay_report)
app.add_url_rule('/dilg_cdrrmo_report', 'dilg_cdrrmo_report', dilg_cdrrmo_report)
app.add_url_rule('/dilg_bfp_report', 'dilg_bfp_report', dilg_bfp_report)
app.add_url_rule('/dilg_health_report', 'dilg_health_report', dilg_health_report)
app.add_url_rule('/dilg_pnp_report', 'dilg_pnp_report', dilg_pnp_report)

def get_db_connection():
    db_path = os.path.join('/database', 'users_web.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn




def get_municipality_from_barangay(barangay):
    for municipality, barangays in barangay_coords.items():
        if barangay in barangays:
            return municipality
    return None




@socketio.on('request_heatmap_data')
def handle_heatmap_data(role):
    try:
        conn = get_db_connection()
        if role == 'barangay':
            cursor = conn.execute('SELECT lat, lon FROM barangay_response')
        elif role == 'cdrrmo':
            cursor = conn.execute('SELECT lat, lon FROM cdrrmo_response')
        elif role == 'pnp':
            cursor = conn.execute('SELECT lat, lon FROM pnp_response')
        else:
            conn.close()
            return jsonify({'error': 'Invalid role'})

        heatmap_data = [[row['lat'], row['lon'], 1] for row in cursor.fetchall() if row['lat'] and row['lon']]
        conn.close()
        emit('heatmap_data', {'role': role, 'data': heatmap_data})
    except Exception as e:
        logger.error(f"Error in handle_heatmap_data: {e}")
        emit('heatmap_data', {'error': str(e)})


@socketio.on('alert')
def handle_new_alert(data):
    try:
        logger.info(f"New alert received: {data}")
        alert_id = str(uuid.uuid4())
        data['alert_id'] = alert_id
        data['timestamp'] = datetime.utcnow().isoformat()
        data['resident_barangay'] = data.get('barangay', 'Unknown')

        alerts.append(data)

        barangay_room = f"barangay_{data.get('barangay').lower() if data.get('barangay') else ''}"
        emit('new_alert', data, room=barangay_room)
        logger.info(f"Alert emitted to room {barangay_room}")

        map_data = {
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'barangay': data.get('barangay'),
            'emergency_type': data.get('emergency_type')
        }
        data['expired'] = False  # Mark as live
        emit('update_map', map_data, room=barangay_room)
    except Exception as e:
        logger.error(f"Error handling alert: {e}")

@socketio.on('forward_alert')
def handle_forward_alert(data):
    logger.info(f"Forward alert received: {data}")
    try:
        target_role = data.get('target_role').lower()
        municipality = get_municipality_from_barangay(data.get('barangay', 'Unknown'))
        alert_id = data.get('alert_id')
        alert_data = next((alert for alert in alerts if alert['alert_id'] == alert_id), None)
        if alert_data:
            emit('redirected_alert', alert_data, room=f"{target_role}_{municipality.lower()}")
            logger.info(f"Alert {alert_id} forwarded to {target_role}_{municipality.lower()}")
    except Exception as e:
        logger.error(f"Error forwarding alert: {e}")


def preprocess_input(input_data, required_columns):
    input_data = input_data.copy()  # Create a copy to avoid modifying original data
    # Ensure all columns are strings for categorical data to avoid type issues
    for col in required_columns:
        if col in input_data:
            # Convert to string and handle missing/unknown values
            input_data[col] = input_data[col].astype(str).replace(['Unknown', 'nan', ''], 'Unknown')
            # Convert to categorical codes
            input_data[col] = input_data[col].astype('category').cat.codes
    # Convert age columns to numeric, handling missing/invalid values
    for col in ['Driver_Age', 'Suspect_Age', 'Victim_Age', 'Patient_Age']:
        if col in input_data:
            input_data[col] = pd.to_numeric(input_data[col], errors='coerce').fillna(0).astype(int)
    # Fill any remaining NaN values with defaults
    input_data = input_data.fillna({'Barangay': 'Unknown', 'Weather': 'Unknown', 'Year': 0})
    return input_data

"""
@socketio.on('response')
def handle_submit(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        manila = pytz.timezone('Asia/Manila')
        timestamp = datetime.now(manila).strftime('%Y-%m-%d %H:%M:%S')
        current_year = int(datetime.now(manila).strftime('%Y'))

        prediction = 'N/A'

        if data.get('emergency_type') == 'Road Accident':
            cursor.execute('''
                INSERT INTO barangay_response (
                    alert_id, road_accident_cause, road_accident_type, weather, 
                    road_condition, vehicle_type, driver_age, driver_gender, 
                    lat, lon, barangay, emergency_type, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('road_accident_cause'), data.get('road_accident_type'),
                data.get('weather'), data.get('road_condition'), data.get('vehicle_type'),
                data.get('driver_age'), data.get('driver_gender'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp
            ))
            cursor.execute('''
                INSERT INTO cdrrmo_response (
                    alert_id, road_accident_cause, road_accident_type, weather, 
                    road_condition, vehicle_type, driver_age, driver_gender, 
                    lat, lon, barangay, emergency_type, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('road_accident_cause'), data.get('road_accident_type'),
                data.get('weather'), data.get('road_condition'), data.get('vehicle_type'),
                data.get('driver_age'), data.get('driver_gender'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp
            ))
            cursor.execute('''
                INSERT INTO pnp_response (
                    alert_id, road_accident_cause, road_accident_type, weather, 
                    road_condition, vehicle_type, driver_age, driver_gender, 
                    lat, lon, barangay, emergency_type, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('road_accident_cause'), data.get('road_accident_type'),
                data.get('weather'), data.get('road_condition'), data.get('vehicle_type'),
                data.get('driver_age'), data.get('driver_gender'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp
            ))
            try:
                input_data = pd.DataFrame([{
                    'Year': current_year,
                    'Barangay': data.get('barangay', 'Unknown'),  # Changed: Added default 'Unknown'
                    'Weather': data.get('weather', 'Unknown'),     # Changed: Added default 'Unknown'
                    'Road_Condition': data.get('road_condition', 'Unknown'),  # Changed: Added default 'Unknown'
                    'Vehicle_Type': data.get('vehicle_type', 'Unknown'),      # Changed: Added default 'Unknown'
                    'Driver_Age': data.get('driver_age', '0'),                # Consistent default
                    'Driver_Gender': data.get('driver_gender', 'Unknown'),    # Changed: Added default 'Unknown'
                    'Accident_Cause': data.get('road_accident_cause', 'Unknown'),  # Changed: Aligned key, added default
                    'Road_Accident_Type': data.get('road_accident_type', 'Unknown')  # Changed: Added default 'Unknown'
                }])
                required_columns = ['Weather', 'Road_Condition', 'Vehicle_Type', 'Driver_Gender', 'Accident_Cause', 'Road_Accident_Type']
                input_data = preprocess_input(input_data, required_columns)
                raw_prediction = road_accident_predictor.predict_proba(input_data)[0][1] * 100
                # Changed: Format prediction to match dashboard
                year_ranges = ['2-3 years', '4-5 years', '2 years', '3-4 years', '1-2 years', '5-6 years']
                random_range = year_ranges[random.randint(0, len(year_ranges)-1)]
                prediction = f"There will be a {raw_prediction:.1f}% chance of Road Accident Again in next {random_range}"
            except Exception as e:
                logger.error(f"Error predicting road accident: {e}")
                prediction = 'prediction_error'
            socketio.emit('barangay_response', {**data, 'prediction': str(prediction)})
            socketio.emit('cdrrmo_response', {**data, 'prediction': str(prediction)})
            socketio.emit('pnp_response', {**data, 'prediction': str(prediction)})

        elif data.get('emergency_type') == 'Fire Incident':
            cursor.execute('''
                INSERT INTO bfp_response (
                    alert_id, fire_type, fire_cause, weather, fire_severity, 
                    lat, lon, barangay, emergency_type, timestamp, responded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('fire_type'), data.get('fire_cause'),
                data.get('weather'), data.get('fire_severity'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp, True
            ))
            cursor.execute('''
                INSERT INTO barangay_fire_response (
                    alert_id, fire_type, fire_cause, weather, fire_severity, 
                    lat, lon, barangay, emergency_type, timestamp, responded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('fire_type'), data.get('fire_cause'),
                data.get('weather'), data.get('fire_severity'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp, True
            ))
            try:
                input_data = pd.DataFrame([{
                    'Year': current_year,
                    'Barangay': data.get('barangay', ''),
                    'Weather': data.get('weather', ''),
                    'Fire_Cause': data.get('fire_cause', ''),
                    'Fire_Type': data.get('fire_type', ''),
                    'Fire_Severity': data.get('fire_severity', '')
                }])
                required_columns = ['Weather', 'Fire_Cause', 'Fire_Type', 'Fire_Severity']
                input_data = preprocess_input(input_data, required_columns)
                raw_prediction = fire_accident_predictor.predict_proba(input_data)[0][1] * 100
                prediction = f"{raw_prediction:.1f}% chance in year {current_year}"
            except Exception as e:
                logger.error(f"Error predicting fire incident: {e}")
                prediction = 'prediction_error'
            socketio.emit('bfp_response', {**data, 'prediction': str(prediction)})
            socketio.emit('barangay_response', {**data, 'prediction': str(prediction)})

        elif data.get('emergency_type') == 'Crime Incident':
            cursor.execute('''
                INSERT INTO pnp_crime_response (
                    alert_id, crime_type, crime_cause, level, suspect_gender, victim_gender, 
                    suspect_age, victim_age, lat, lon, barangay, emergency_type, timestamp, responded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('crime_type'), data.get('crime_cause'),
                data.get('level'), data.get('suspect_gender'), data.get('victim_gender'),
                data.get('suspect_age'), data.get('victim_age'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp, True
            ))
            cursor.execute('''
                INSERT INTO barangay_crime_response (
                    alert_id, crime_type, crime_cause, level, suspect_gender, victim_gender, 
                    suspect_age, victim_age, lat, lon, barangay, emergency_type, timestamp, responded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('crime_type'), data.get('crime_cause'),
                data.get('level'), data.get('suspect_gender'), data.get('victim_gender'),
                data.get('suspect_age'), data.get('victim_age'), data.get('lat'), data.get('lon'),
                data.get('barangay'), data.get('emergency_type'), timestamp, True
            ))
            try:
                input_data = pd.DataFrame([{
                    'Year': current_year,
                    'Barangay': data.get('barangay', ''),
                    'Crime_Type': data.get('crime_type', ''),
                    'Crime_Cause': data.get('crime_cause', ''),
                    'Level': data.get('level', ''),
                    'Suspect_Gender': data.get('suspect_gender', ''),
                    'Victim_Gender': data.get('victim_gender', ''),
                    'Suspect_Age': data.get('suspect_age', '0'),
                    'Victim_Age': data.get('victim_age', '0')
                }])
                required_columns = ['Crime_Type', 'Crime_Cause', 'Level', 'Suspect_Gender', 'Victim_Gender']
                input_data = preprocess_input(input_data, required_columns)
                raw_prediction = crime_predictor.predict_proba(input_data)[0][1] * 100
                prediction = f"{raw_prediction:.1f}% chance in year {current_year}"
            except Exception as e:
                logger.error(f"Error predicting crime incident: {e}")
                prediction = 'prediction_error'
            socketio.emit('pnp_response', {**data, 'prediction': str(prediction)})
            socketio.emit('barangay_response', {**data, 'prediction': str(prediction)})

        elif data.get('emergency_type') in ['Health Emergency', 'Birth Emergency']:
            cursor.execute('''
                INSERT INTO health_response (
                    alert_id, health_type, health_cause, weather, patient_age, patient_gender, 
                    lat, lon, barangay, emergency_type, timestamp, responded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('health_type'), data.get('health_cause'),
                data.get('weather'), data.get('patient_age', '0'), data.get('patient_gender', ''),
                data.get('lat'), data.get('lon'), data.get('barangay'), data.get('emergency_type'),
                timestamp, True
            ))
            cursor.execute('''
                INSERT INTO hospital_response (
                    alert_id, health_type, health_cause, weather, patient_age, patient_gender, 
                    lat, lon, barangay, emergency_type, timestamp, responded, assigned_hospital
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('alert_id'), data.get('health_type'), data.get('health_cause'),
                data.get('weather'), data.get('patient_age', '0'), data.get('patient_gender', ''),
                data.get('lat'), data.get('lon'), data.get('barangay'), data.get('emergency_type'),
                timestamp, True, data.get('assigned_hospital', '')
            ))
            try:
                input_data = pd.DataFrame([{
                    'Year': current_year,
                    'Barangay': data.get('barangay', 'Unknown'),  # Changed: Added default 'Unknown'
                    'Weather': data.get('weather', 'Unknown'),     # Changed: Added default 'Unknown'
                    'Health_Type': data.get('health_type', 'Unknown'),  # Changed: Added default 'Unknown'
                    'Health_Cause': data.get('health_cause', 'Unknown'),  # Changed: Added default 'Unknown'
                    'Severity': data.get('severity', 'Unknown'),         # Changed: Added default 'Unknown'
                    'Patient_Age': data.get('patient_age', '0'),         # Consistent default
                    'Patient_Gender': data.get('patient_gender', 'Unknown')  # Changed: Added default 'Unknown'
                }])
                required_columns = ['Weather', 'Health_Type', 'Health_Cause', 'Severity', 'Patient_Gender']
                input_data = preprocess_input(input_data, required_columns)
                predictor = health_predictor if data.get('emergency_type') == 'Health Emergency' else birth_predictor
                raw_prediction = predictor.predict_proba(input_data)[0][1] * 100
                # Changed: Format prediction to match dashboard
                year_ranges = ['2-3 years', '4-5 years', '2 years', '3-4 years', '1-2 years', '5-6 years']
                random_range = year_ranges[random.randint(0, len(year_ranges)-1)]
                prediction = f"There will be a {raw_prediction:.1f}% chance of {data.get('emergency_type')} Again in next {random_range}"
            except Exception as e:
                logger.error(f"Error predicting {data.get('emergency_type')}: {e}")
                prediction = 'prediction_error'
            socketio.emit('health_response', {**data, 'prediction': str(prediction)})
            socketio.emit('hospital_response', {**data, 'prediction': str(prediction)})
            socketio.emit('barangay_response', {**data, 'prediction': str(prediction)})

        conn.commit()
        logger.info(f"Response saved for alert_id: {data.get('alert_id')}, emergency_type: {data.get('emergency_type')}")
    except Exception as e:
        logger.error(f"Error in handle_response: {e}")
    finally:
        conn.close()
"""

@socketio.on('submit_response')
def handle_submit_response(data):
    try:
        alert_id = data.get('alert_id', str(uuid.uuid4()))
        role = data.get('role', '').lower()
        barangay = data.get('barangay', '')
        municipality = get_municipality_from_barangay(barangay) or data.get('municipality', '')
        emergency_type = data.get('emergency_type', '')
        road_accident_cause = data.get('road_accident_cause', '')
        road_accident_type = data.get('road_accident_type', '')
        weather = data.get('weather', '')
        road_condition = data.get('road_condition', '')
        vehicle_type = data.get('vehicle_type', '')
        driver_age = data.get('driver_age', '')
        driver_gender = data.get('driver_gender', '')
        health_type = data.get('health_type', '')
        health_cause = data.get('health_cause', '')
        patient_age = data.get('patient_age', '')
        patient_gender = data.get('patient_gender', '')
        lat = data.get('lat', 0.0)
        lon = data.get('lon', 0.0)
        timestamp = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')  # Changed to string
        responded = True

        conn = get_db_connection()
        if role == 'barangay':
            conn.execute('''
                INSERT INTO barangay_response (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded))
        elif role == 'cdrrmo':
            conn.execute('''
                INSERT INTO cdrrmo_response (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded))
            prediction = handle_cdrrmo_response_submitted(data)
        elif role == 'pnp':
            conn.execute('''
                INSERT INTO pnp_response (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded))
            prediction = handle_pnp_response_submitted(data)
        elif role == 'bfp':
            # Existing BFP logic remains unchanged
            pass
        elif role == 'health':
            conn.execute('''
            INSERT INTO health_response (
                alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',(alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded))
            prediction = handle_health_response(data)
        elif role == 'hospital':
            conn.execute('''
            INSERT INTO hospital_response (
                alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded, assigned_hospital
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',(alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded, data.get('assigned_hospital')))
            prediction = handle_hospital_response(data)
        conn.commit()
        conn.close()

        # Emit response with prediction
        response_data = {
            'alert_id': alert_id,
            'role': role,
            'barangay': barangay,
            'municipality': municipality,
            'emergency_type': emergency_type,
            'prediction': prediction,
            'timestamp': timestamp  # Using the string timestamp
        }
        socketio.emit(f'{role}_response', response_data)
        logger.info(f"Response submitted for alert {alert_id} by {role}")
    except Exception as e:
        logger.error(f"Error in handle_submit_response: {e}")


@socketio.on('response_update')
def handle_response(data):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        manila = pytz.timezone('Asia/Manila')
        base_time = datetime.now(manila)
        c.execute('''
            INSERT INTO barangay_response (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('road_accident_cause'),
            data.get('road_accident_type'),
            data.get('weather'),
            data.get('road_condition'),
            data.get('vehicle_type'),
            data.get('driver_age'),
            data.get('driver_gender'),
            data.get('lat'),
            data.get('lon'),
            data.get('barangay'),
            data.get('emergency_type'),
            base_time.strftime('%Y-%m-%d %H:%M:%S'),
            data.get('responded', True)
        ))
        c.execute('''
            INSERT INTO bfp_response (alert_id, fire_type, fire_cause, weather, fire_severity, lat, lon, barangay, emergency_type, timestamp, responded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('fire_type'),
            data.get('fire_cause'),
            data.get('weather'),
            data.get('fire_severity'),
            data.get('lat'),
            data.get('lon'),
            data.get('barangay'),
            data.get('emergency_type'),
            base_time.strftime('%Y-%m-%d %H:%M:%S'),
            data.get('responded', True)
        ))
        c.execute('''
            INSERT INTO cdrrmo_response (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('road_accident_cause'),
            data.get('road_accident_type'),
            data.get('weather'),
            data.get('road_condition'),
            data.get('vehicle_type'),
            data.get('driver_age'),
            data.get('driver_gender'),
            data.get('lat'),
            data.get('lon'),
            data.get('barangay'),
            data.get('emergency_type'),
            base_time.strftime('%Y-%m-%d %H:%M:%S'),
            data.get('responded', True)
        ))
        c.execute('''
            INSERT INTO pnp_response (alert_id, road_accident_cause, road_accident_type, weather, road_condition, vehicle_type, driver_age, driver_gender, lat, lon, barangay, emergency_type, timestamp, responded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('road_accident_cause'),
            data.get('road_accident_type'),
            data.get('weather'),
            data.get('road_condition'),
            data.get('vehicle_type'),
            data.get('driver_age'),
            data.get('driver_gender'),
            data.get('lat'),
            data.get('lon'),
            data.get('barangay'),
            data.get('emergency_type'),
            base_time.strftime('%Y-%m-%d %H:%M:%S'),
            data.get('responded', True)
        ))
        c.execute('''
            INSERT INTO health_response (
                alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('health_type'),
            data.get('health_cause'),
            data.get('weather'),
            data.get('patient_age'),
            data.get('patient_gender'),
            data.get('lat'),
            data.get('lon'),
            data.get('barangay'),
            data.get('emergency_type'),
            base_time.strftime('%Y-%m-%d %H:%M:%S'),
            data.get('responded', True)
        ))
        c.execute('''
            INSERT INTO hospital_response (
                alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('health_type'),
            data.get('health_cause'),
            data.get('weather'),
            data.get('patient_age'),
            data.get('patient_gender'),
            data.get('lat'),
            data.get('lon'),
            data.get('barangay'),
            data.get('emergency_type'),
            base_time.strftime('%Y-%m-%d %H:%M:%S'),
            data.get('responded', True)
        ))
        conn.commit()
        logger.info(f"Response data inserted for alert_id: {data.get('alert_id')}")
        # Emit updates to respective chart pages
        from BarangayCharts import handle_barangay_response
        from BFPCharts import handle_bfp_response
        from CDRRMOCharts import handle_cdrrmo_response
        from PNPCharts import handle_pnp_response
        handle_barangay_response(data)
        handle_bfp_response(data)
        handle_cdrrmo_response(data)
        handle_pnp_response(data)
        handle_health_response(data)
        handle_hospital_response(data)
    except Exception as e:
        logger.error(f"Error inserting response data: {e}")
        conn.rollback()
    finally:
        conn.close()



@socketio.on('role_accepted')
def role_accepted(data):
    logger.info(f"Role {data['role']} accepted for alert {data['alert_id']}")
    try:
        alert_id = data['alert_id']
        role = data['role'].lower()
        if alert_id not in accepted_roles:
            accepted_roles[alert_id] = []
        if role not in accepted_roles[alert_id]:
            accepted_roles[alert_id].append(role)
            alert_data = next((alert for alert in alerts if alert['alert_id'] == alert_id), None)
            if alert_data:
                namespace = f'/{role}'
                socketio.emit('new_alert', alert_data, namespace=namespace)
                logger.info(f"Forwarded alert {alert_id} to {namespace}")
    except Exception as e:
        logger.error(f"Error in role_accepted: {e}")

@socketio.on('role_declined')
def role_declined(data):
    logger.info(f"Role {data['role']} declined for alert {data['alert_id']}")
    try:
        alert_id = data['alert_id']
        role = data['role'].lower()
        if alert_id in accepted_roles and role in accepted_roles[alert_id]:
            accepted_roles[alert_id].remove(role)
            logger.info(f"Removed {role} from accepted roles for alert {alert_id}")
    except Exception as e:
        logger.error(f"Error in role_declined: {e}")

@socketio.on('redirect_alert')
def handle_redirect_alert(data):
    logger.debug(f"Redirected alert received: {data}")
    try:
        target_role = data.get('target_role', '').lower()
        municipality = data.get('municipality', '').lower()
        barangay = data.get('barangay', '').lower()

        # Valid roles
        valid_roles = ['bfp', 'cdrrmo', 'pnp', 'health', 'hospital']
        
        if target_role not in valid_roles:
            logger.error(f"Invalid target role: {target_role}")
            return

        # Emit to primary target
        room = f"{target_role}_{municipality}"
        emit('redirected_alert', data, room=room)

        # Map update
        map_data = {
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'barangay': data.get('barangay'),
            'emergency_type': data.get('emergency_type')
        }
        data['expired'] = False
        emit('update_map', map_data, room=room)
        logger.info(f"Alert redirected to {room} with map update")

        # === AUTO SEND TO PNP WHEN CDRRMO OR BFP IS CHOSEN ===
        if target_role in ['cdrrmo', 'bfp']:
            pnp_room = f"pnp_{municipality}"
            pnp_data = data.copy()
            pnp_data['target_role'] = 'pnp'
            
            emit('pnp_redirect_alert', pnp_data, room=pnp_room)
            emit('update_map', map_data, room=pnp_room)
            emit('update_dashboard_emergency_type', {
                'alert_id': data.get('alert_id'),
                'emergency_type': data.get('emergency_type'),
                'barangay': data.get('barangay'),
                'municipality': data.get('municipality')
            }, room=pnp_room)
            logger.info(f"Auto forwarded to PNP: {pnp_room}")

        # === CRITICAL: SEND update_dashboard_emergency_type BACK TO BARANGAY ===
        # This triggers dropdowns on BarangayDashboard after clicking "Send to BFP & PNP"
        if target_role in ['bfp', 'cdrrmo']:
            barangay_room = f"barangay_{barangay}"
            emit('update_dashboard_emergency_type', {
                'alert_id': data.get('alert_id'),
                'emergency_type': data.get('emergency_type'),
                'barangay': data.get('barangay'),
                'municipality': data.get('municipality')
            }, room=barangay_room)
            logger.info(f"Dropdown trigger sent back to Barangay: {barangay_room}")

    except Exception as e:
        logger.error(f"Error in handle_redirect_alert: {e}")


@socketio.on('pnp_redirect_alert')
def handle_pnp_redirect_alert(data):
    logger.info(f"Received PNP redirect alert: {data}")
    timestamp = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
    data['timestamp'] = timestamp

    # Store in DB
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR IGNORE INTO pnp_alerts (
                alert_id, lat, lon, municipality, barangay, emergency_type, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('alert_id'),
            data.get('lat'),
            data.get('lon'),
            data.get('municipality'),
            data.get('barangay'),
            data.get('emergency_type'),
            timestamp
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error storing PNP alert: {e}")
    finally:
        conn.close()

    # Emit to PNP room
    pnp_room = f"pnp_{data.get('municipality', '').lower()}"
    emit('pnp_redirect_alert', data, room=pnp_room)
    emit('update_map', {
        'lat': data.get('lat'),
        'lon': data.get('lon'),
        'barangay': data.get('barangay'),
        'emergency_type': data.get('emergency_type')
    }, room=pnp_room)
    emit('update_dashboard_emergency_type', {
        'alert_id': data.get('alert_id'),
        'emergency_type': data.get('emergency_type'),
        'barangay': data.get('barangay'),
        'municipality': data.get('municipality')
    }, room=pnp_room)
    logger.info(f"PNP alert fully processed and emitted to {pnp_room}")

@socketio.on('health_redirected_alert')
def handle_health_redirected_alert(data):
    logger.info(f"Received health_redirected_alert: {data}")
    try:
        alert_id = data.get('alert_id')
        barangay = data.get('barangay')
        emergency_type = data.get('emergency_type', 'Health Emergency')
        if emergency_type != 'Health Emergency':
            emergency_type = 'Health Emergency'  # Enforce Health Emergency
        lat = data.get('lat')
        lon = data.get('lon')
        timestamp = datetime.now(pytz.timezone('Asia/Manila')).isoformat()
        resident_barangay = data.get('resident_barangay', barangay)
        image = data.get('image')

        if not alert_id or not barangay:
            logger.error("Missing required fields in health_redirected_alert")
            emit('error', {'message': 'Missing required fields'}, to=request.sid)
            return

        db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO health_responses (alert_id, barangay, emergency_type, lat, lon, timestamp, status, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (alert_id, barangay, emergency_type, lat, lon, timestamp, 'RESPONDED', image))
        conn.commit()
        conn.close()
        logger.info(f"Stored health_redirected_alert for alert_id: {alert_id}")

        emit('health_redirected_alert', {
            'alert_id': alert_id,
            'barangay': barangay,
            'emergency_type': emergency_type,
            'lat': lat,
            'lon': lon,
            'resident_barangay': resident_barangay,
            'image': image
        }, broadcast=True, include_self=False)
    except Exception as e:
        logger.error(f"Error in health_redirected_alert: {e}")
        emit('error', {'message': str(e)}, to=request.sid)

@socketio.on('hospital_redirect_alert')
def handle_hospital_redirect_alert(data):
    logger.info(f"Received hospital_redirect_alert: {data}")
    try:
        alert_id = data.get('alert_id')
        barangay = data.get('barangay')
        emergency_type = data.get('emergency_type', 'Health Emergency')
        lat = data.get('lat')
        lon = data.get('lon')
        health_type = data.get('health_type')
        health_cause = data.get('health_cause')
        patient_age = data.get('patient_age')
        patient_gender = data.get('patient_gender')
        selected_hospital = data.get('selected_hospital')
        timestamp = data.get('timestamp', datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S'))

        if not all([alert_id, barangay, selected_hospital]):
            logger.error("Missing required fields in hospital_redirect_alert")
            emit('error', {'message': 'Missing required fields'}, to=request.sid)
            return

        emit('hospital_redirect_alert', {
            'alert_id': alert_id,
            'barangay': barangay,
            'emergency_type': emergency_type,
            'lat': lat,
            'lon': lon,
            'health_type': health_type,
            'health_cause': health_cause,
            'patient_age': patient_age,
            'patient_gender': patient_gender,
            'selected_hospital': selected_hospital,
            'timestamp': timestamp
        }, room='hospital')
        logger.info("Hospital redirect alert emitted to room hospital")

        emit('update_map', {
            'lat': lat,
            'lon': lon,
            'barangay': barangay,
            'emergency_type': emergency_type
        }, room='hospital')
        logger.info(f"Map update emitted to room hospital for alert {alert_id}")
    except Exception as e:
        logger.error(f"Error in hospital_redirect_alert: {e}")
        emit('error', {'message': str(e)}, to=request.sid)



@socketio.on('hospital_alert')
def handle_hospital_alert(data):
    logger.info(f"Received hospital_alert: {data}")
    try:
        municipality = data.get('municipality', '').lower()
        hospital_room = f"hospital_{municipality}"
        emit('hospital_alert', data, room=hospital_room)
        logger.info(f"Hospital alert emitted to room {hospital_room}")
        emit('update_map', {
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'barangay': data.get('barangay'),
            'health_type': data.get('health_type'),
            'health_cause': data.get('health_cause'),
            'patient_age': data.get('patient_age'),
            'patient_gender': data.get('patient_gender'),
            'emergency_type': data.get('emergency_type')
        }, room=hospital_room)
        logger.info(f"Map update emitted to room {hospital_room} for alert {data.get('alert_id')}")
    except Exception as e:
        logger.error(f"Error in hospital_alert: {e}")
        emit('error', {'message': str(e)}, to=request.sid)

@socketio.on('hospital_alert_barangay')
def handle_hospital_alert_barangay(data):
    logger.info(f"Received hospital_alert_barangay: {data}")
    try:
        barangay = data.get('barangay', '').lower()
        barangay_room = f"barangay_{barangay}"
        emit('hospital_alert_barangay', data, room=barangay_room)
        logger.info(f"Hospital alert emitted to room {barangay_room} for alert {data.get('alert_id')}")
    except Exception as e:
        logger.error(f"Error in hospital_alert_barangay: {e}")
        emit('error', {'message': str(e)}, to=request.sid)

@socketio.on('update_dashboard_emergency_type')
def handle_update_dashboard_emergency_type(data):
    logger.info(f"Received update dashboard emergency type: {data}")
    
    
    
    barangay_room = f"barangay_{data.get('barangay').lower()}"
    pnp_room = f"pnp_{data.get('barangay').lower()}"
    
    emit('update_dashboard_emergency_type', {
        'alert_id': data.get('alert_id'),
        'emergency_type': data.get('emergency_type'),
        'barangay': data.get('barangay')
    }, room=barangay_room)
    
    emit('update_dashboard_emergency_type', {
        'alert_id': data.get('alert_id'),
        'emergency_type': data.get('emergency_type'),
        'barangay': data.get('barangay')
    }, room=pnp_room)
    
    logger.info(f"Emergency type update emitted to rooms {barangay_room} and {pnp_room}")
    
    pnp_room = f"pnp_{data.get('barangay').lower()}"
    emit('update_dashboard_emergency_type', {
        'alert_id': data.get('alert_id'),
        'emergency_type': data.get('emergency_type'),
        'barangay': data.get('barangay')
    }, room=pnp_room)
    logger.info(f"Emergency type update emitted to room {pnp_room}")

# After @socketio.on('response_update')



    
# New function get_road_condition
@socketio.on('update_response')
def handle_update_response(data):
    logger.info(f"Update response received: {data}")
    try:
        role = data.get('role', '').lower()
        barangay = data.get('barangay', '').lower()
        municipality = data.get('municipality', '').lower()
        emit('update_response', data, broadcast=True, include_self=True)
        logger.info(f"Broadcasted update_response for role {role}")
    except Exception as e:
        logger.error(f"Error broadcasting update_response: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")


@socketio.on('request_response_popup')
def handle_request_response_popup(data):
    logger.info(f"Request response popup received: {data}")
    try:
        role = data.get('role')
        barangay = data.get('barangay')
        municipality = data.get('municipality')
        alert_id = data.get('alert_id')
        emergency_type = data.get('emergency_type')
        lat = data.get('lat')
        lon = data.get('lon')
        timestamp = data.get('timestamp')

        if role == 'cdrrmo':
            room = f"cdrrmo_{municipality.lower()}"
            emit('request_response_popup', {
                'alert_id': alert_id,
                'barangay': barangay,
                'emergency_type': emergency_type,
                'lat': lat,
                'lon': lon,
                'timestamp': timestamp
            }, room=room)
            logger.info(f"Emitted request_response_popup to {room}")
        elif role == 'pnp':
            room = f"pnp_{municipality.lower()}"
            emit('request_response_popup', {
                'alert_id': alert_id,
                'barangay': barangay,
                'emergency_type': emergency_type,
                'lat': lat,
                'lon': lon,
                'timestamp': timestamp
            }, room=room)
            logger.info(f"Emitted request_response_popup to {room}")
    except Exception as e:
        logger.error(f"Error handling request_response_popup: {e}")

@socketio.on('register_role')
def handle_register_role(data):
    role = data.get('role')
    if role == 'barangay':
        barangay = data.get('barangay').lower() if data.get('barangay') else None
        if barangay:
            join_room(f"barangay_{barangay}")
            logger.info(f"Client {request.sid} joined room barangay_{barangay}")
    elif role == 'cdrrmo':
        municipality = data.get('municipality').lower() if data.get('municipality') else None
        if municipality:
            join_room(f"cdrrmo_{municipality}")
            logger.info(f"Client {request.sid} joined room cdrrmo_{municipality}")
    elif role == 'pnp':
        municipality = data.get('municipality').lower() if data.get('municipality') else None
        if municipality:
            join_room(f"pnp_{municipality}")
            logger.info(f"Client {request.sid} joined room pnp_{municipality}")
    elif role == 'bfp':
        municipality = data.get('municipality').lower() if data.get('municipality') else None
        if municipality:
            join_room(f"bfp_{municipality}")
            logger.info(f"Client {request.sid} joined room bfp_{municipality}")
    elif role == 'health':
            municipality = data.get('municipality').lower() if data.get('municipality') else None
            if municipality:
                join_room(f"health_{municipality}")
                logger.info(f"Client {request.sid} joined room health_{municipality}")
    elif role == 'hospital':
            municipality = data.get('municipality').lower() if data.get('municipality') else None
            if municipality:
                join_room(f"hospital_{municipality}")
                logger.info(f"Client {request.sid} joined room hospital_{municipality}")

accepted_roles = {'bfp': False, 'cdrrmo': False, 'health': False, 'hospital': False, 'pnp': False}


# For Sending Receiving, Displaying, Pin Map on Alerts, and Display Prediction



#Old handle_new_alert function



# /For Sending Receiving, Displaying, Pin Map on Alerts, and Display Prediction

# Barangay BFP, CDRRMO, City Health, Hospital, and PNP Preiction Display


TIME_RANGES = ['1-2 weeks', '2-4 weeks', '1 month', '2 months', '3-6 months', '1 year']

@app.route('/get_latest_prediction')
def get_latest_prediction():
    conn = get_db_connection()
    result = conn.execute('''
        SELECT prediction FROM barangay_response 
        WHERE prediction IS NOT NULL AND prediction LIKE '%2023%'
        ORDER BY timestamp DESC LIMIT 1
    ''').fetchone()
    conn.close()
    return jsonify({'prediction': result[0] if result else 'No prediction available'})

@app.route('/get_latest_fire_prediction')
def get_latest_fire_prediction():
    conn = get_db_connection()
    result = conn.execute('''
        SELECT prediction FROM barangay_fire_response 
        WHERE prediction IS NOT NULL AND prediction LIKE '%Fire%'
        ORDER BY timestamp DESC LIMIT 1
    ''').fetchone()
    conn.close()
    return jsonify({'prediction': result[0] if result else 'No fire prediction available'})


@socketio.on('barangay_response')
def barangay_arima_handler(data):
    handle_barangay_response_submitted(data) 

# === ARIMAX Handler (used first) ===
@socketio.on('barangay_arimax_submitted')
def barangay_arimax_handler(data):
    handle_barangay_arimax_submitted(data)

@socketio.on('barangay_sarima_submitted')
def barangay_sarima_handler(data):
    handle_barangay_sarima_submitted(data)
    
@socketio.on('barangay_sarimax_submitted')
def barangay_sarimax_handler(data):
    handle_barangay_sarimax_submitted(data)
      
    
@socketio.on('barangay_fire_submitted')
def barangay_fire_handler(data):
    handle_barangay_fire_submitted(data)

@socketio.on('barangay_fire_arimax')
def barangay_fire_arimax_handler(data):
    handle_barangay_fire_arimax(data)
    
@socketio.on('barangay_fire_sarima')
def barangay_fire_sarima_handler(data):
    handle_barangay_fire_sarima(data)
    
@socketio.on('barangay_fire_sarimax')
def barangay_fire_sarimax_handler(data):
    handle_barangay_fire_sarimax(data)

@socketio.on('barangay_crime_submitted')
def barangay_crime_handler(data):
    handle_barangay_crime_submitted(data)
    

@socketio.on('barangay_health_response')
def barangay_health_handler(data):
    handle_barangay_health_response(data)
    
@socketio.on('cdrrmo_response')
def cdrrmo_response_handler(data):
    handle_cdrrmo_response_submitted(data)


@socketio.on('pnp_response')
def pnp_response_handler(data):
    handle_pnp_response_submitted(data)


@socketio.on('pnp_fire_submitted')
def pnp_fire_handler(data):
    handle_pnp_fire_submitted(data)
    

@socketio.on('pnp_crime_submitted')
def pnp_crime_handler(data):
    handle_pnp_crime_submitted(data)

        
@socketio.on('fire_response_submitted')
def bfp_fire_response_handler(data):
    handle_fire_response_submitted(data)
    
    
@socketio.on('health_response')
def health_response_handler(data):
    handle_health_response(data)



@socketio.on('hospital_response')
def hospital_response_handler(data):  # sourcery skip: low-code-quality  # sourcery skip: low-code-quality
    handle_hospital_response(data)


# /Barangay BFP, CDRRMO, City Health, Hospital, and PNP Preiction Display

@socketio.on('submit_barangay_data')
def submit_barangay_data(data):
    
    try:
        barangay = data.get('barangay', '')
        response = {
            'timestamp': data.get('timestamp', datetime.now(pytz.timezone('Asia/Manila')).isoformat()),
            'emergency_type': data.get('emergency_type', 'unknown'),
            'role': 'barangay',
            'barangay': barangay,
            **{k: v for k, v in data.items() if k not in ['timestamp', 'emergency_type', 'role', 'barangay']}
        }
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'AlertNowLocal.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('INSERT INTO responses (data) VALUES (?)', (json.dumps(response),))
        conn.commit()
        conn.close()
        responses.append(response)
        socketio.emit('analytics_update', {'role': 'barangay', 'barangay': barangay, 'data': response}, room=f'barangay_analytics_{barangay}')
    except Exception as e:
        logger.error(f"Error in submit_barangay_data: {e}")

@socketio.on('submit_cdrrmo_data')
def submit_cdrrmo_data(data):
    try:
        municipality = data.get('municipality', '')
        response = {
            'timestamp': data.get('timestamp', datetime.now(pytz.timezone('Asia/Manila')).isoformat()),
            'emergency_type': data.get('emergency_type', 'unknown'),
            'role': 'cdrrmo',
            'municipality': municipality,
            **{k: v for k, v in data.items() if k not in ['timestamp', 'emergency_type', 'role', 'municipality']}
        }
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'AlertNowLocal.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('INSERT INTO responses (data) VALUES (?)', (json.dumps(response),))
        conn.commit()
        conn.close()
        responses.append(response)
        socketio.emit('analytics_update', {'role': 'cdrrmo', 'municipality': municipality, 'data': response}, room=f'cdrrmo_analytics_{municipality}')
    except Exception as e:
        logger.error(f"Error in submit_cdrrmo_data: {e}")

@socketio.on('submit_pnp_data')
def submit_pnp_data(data):
    try:
        municipality = data.get('municipality', '')
        response = {
            'timestamp': data.get('timestamp', datetime.now(pytz.timezone('Asia/Manila')).isoformat()),
            'emergency_type': data.get('emergency_type', 'unknown'),
            'role': 'pnp',
            'municipality': municipality,
            **{k: v for k, v in data.items() if k not in ['timestamp', 'emergency_type', 'role', 'municipality']}
        }
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'AlertNowLocal.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('INSERT INTO responses (data) VALUES (?)', (json.dumps(response),))
        conn.commit()
        conn.close()
        responses.append(response)
        socketio.emit('analytics_update', {'role': 'pnp', 'municipality': municipality, 'data': response}, room=f'pnp_analytics_{municipality}')
    except Exception as e:
        logger.error(f"Error in submit_pnp_data: {e}")

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyBSXRZPDX1x1d91Ck-pskiwGA8Y2-5gDVs')
barangay_coords = {}
try:
    with open(os.path.join(os.path.dirname(__file__), 'assets', 'coords.txt'), 'r') as f:
        barangay_coords = ast.literal_eval(f.read())
except FileNotFoundError:
    logger.error("coords.txt not found in assets directory. Using empty dict.")
except Exception as e:
    logger.error(f"Error loading coords.txt: {e}. Using empty dict.")

municipality_coords = {
    "San Pablo City": {"lat": 14.0642, "lon": 121.3233},
    "Quezon Province": {"lat": 13.9347, "lon": 121.9473},
}


@app.route('/export_users', methods=['GET'])
def export_users():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return jsonify([dict(user) for user in users])

@app.route('/download_db', methods=['GET'])
def download_db():
    db_path = os.path.join('/database', 'users_web.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    if not os.path.exists(db_path):
        return "Database file not found", 404
    logger.debug(f"Serving database from: {db_path}")
    return send_file(db_path, as_attachment=True, download_name='users_web.db')


def construct_unique_id(role, barangay=None, assigned_municipality=None, contact_no=None):
    if role == 'barangay':
        return f"{barangay}_{contact_no}"
    return f"{role}_{assigned_municipality}_{contact_no}"

@app.route('/')
def home():
    logger.debug("Rendering SignUpType.html")
    return render_template('SignUpType.html')

@app.route('/signup_barangay', methods=['GET', 'POST'])
def signup_barangay():
    if request.method == 'POST':
        barangay = request.form['barangay']
        assigned_municipality = request.form['municipality']
        province = request.form['province']
        contact_no = request.form['contact_no']
        password = request.form['password']
        unique_id = construct_unique_id('barangay', barangay=barangay, contact_no=contact_no)
        
        conn = get_db_connection()
        try:
            existing_user = conn.execute('SELECT * FROM users WHERE contact_no = ?', (contact_no,)).fetchone()
            if existing_user:
                logger.error("Signup failed: Contact number %s already exists", contact_no)
                return "Contact number already exists", 400
            
            conn.execute('''
                INSERT INTO users (barangay, role, contact_no, assigned_municipality, province, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (barangay, 'barangay', contact_no, assigned_municipality, province, password))
            conn.commit()
            logger.debug("User signed up successfully: %s", unique_id)
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            logger.error("IntegrityError during signup: %s", e)
            return "User already exists", 400
        except Exception as e:
            logger.error(f"Signup failed for {unique_id}: {e}")
            return f"Signup failed: {e}", 500
        finally:
            conn.close()
    return render_template('SignUpPage.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug("Accessing /login with method: %s", request.method)
    if request.method == 'POST':
        barangay = request.form['barangay']
        contact_no = request.form['contact_no']
        password = request.form['password']
        unique_id = construct_unique_id('barangay', barangay=barangay, contact_no=contact_no)
        
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE barangay = ? AND contact_no = ? AND password = ?
        ''', (barangay, contact_no, password)).fetchone()
        conn.close()
        
        if user:
            session['unique_id'] = unique_id
            session['role'] = user['role']
            logger.debug(f"Web login successful for barangay: {unique_id}")
            return redirect(url_for('barangay_dashboard'))
        logger.warning(f"Web login failed for unique_id: {unique_id}")
        return "Invalid credentials", 401
    return render_template('LogInPage.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    barangay = data.get('barangay')
    contact_no = data.get('contact_no')
    password = data.get('password')
    unique_id = construct_unique_id('barangay', barangay=barangay, contact_no=contact_no)
    
    conn = get_db_connection()
    user = conn.execute('''
        SELECT * FROM users WHERE barangay = ? AND contact_no = ? AND password = ?
    ''', (barangay, contact_no, password)).fetchone()
    conn.close()
    
    if user:
        logger.debug(f"API login successful for user: {unique_id} with role: {user['role']}")
        return jsonify({'status': 'success', 'role': user['role']})
    logger.warning(f"API login failed for unique_id: {unique_id}")
    return jsonify({'error': 'Invalid credentials'}), 401

# Update signup_agency
@app.route('/signup_agency', methods=['GET', 'POST'])
def signup_agency():
    if request.method == 'POST':
        role = request.form['role'].lower()
        assigned_municipality = request.form['municipality']
        contact_no = request.form['contact_no']
        password = request.form['password']
        assigned_hospital = request.form.get('assigned_hospital', '').lower() if role == 'hospital' else None
        unique_id = construct_unique_id(role, assigned_municipality=assigned_municipality, contact_no=contact_no)
        
        conn = get_db_connection()
        try:
            existing_user = conn.execute('SELECT * FROM users WHERE contact_no = ?', (contact_no,)).fetchone()
            if existing_user:
                logger.error("Signup failed: Contact number %s already exists", contact_no)
                return render_template('AgencyUp.html', error="Contact number already exists"), 400
            
            conn.execute('''
                INSERT INTO users (role, contact_no, assigned_municipality, password, assigned_hospital)
                VALUES (?, ?, ?, ?, ?)
            ''', (role, contact_no, assigned_municipality, password, assigned_hospital))
            conn.commit()
            logger.debug("User signed up successfully: %s", unique_id)
            return redirect(url_for('login_agency'))
        except sqlite3.IntegrityError as e:
            logger.error("IntegrityError during signup: %s", e)
            return render_template('AgencyUp.html', error="User already exists"), 400
        except Exception as e:
            logger.error(f"Signup failed for {unique_id}: {e}")
            return render_template('AgencyUp.html', error=f"Signup failed: {e}"), 500
        finally:
            conn.close()
    return render_template('AgencyUp.html')

# Update login_agency
@app.route('/login_agency', methods=['GET', 'POST'])
def login_agency():
    logger.debug("Accessing /login_agency with method: %s", request.method)
    if request.method == 'POST':
        role = request.form['role'].lower()
        if 'role' not in request.form:
            logger.error("Role field is missing in the form data")
            return render_template('AgencyIn.html', error="Role is required", cdrrmo_pnp_bfp_users=[]), 400
        assigned_municipality = request.form['municipality']
        contact_no = request.form['contact_no']
        password = request.form['password']
        assigned_hospital = request.form.get('assigned_hospital', '').lower() if role == 'hospital' else None
        
        if role not in ['cdrrmo', 'pnp', 'bfp', 'health', 'hospital']:
            logger.error(f"Invalid role provided: {role}")
            return render_template('AgencyIn.html', error="Invalid role", cdrrmo_pnp_bfp_users=[]), 400
        
        logger.debug(f"Login attempt: role={role}, municipality={assigned_municipality}, contact_no={contact_no}")
        
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND password = ? AND assigned_municipality = ? AND (assigned_hospital = ? OR assigned_hospital IS NULL)
        ''', (role, contact_no, password, assigned_municipality, assigned_hospital)).fetchone()
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
            elif user['role'] == 'health':
                return redirect(url_for('health_dashboard'))
            elif user['role'] == 'hospital':
                return redirect(url_for('hospital_dashboard'))
        logger.warning(f"Web login failed for assigned_municipality: {assigned_municipality}, contact: {contact_no}, role: {role}")
        return render_template('AgencyIn.html', error="Invalid credentials or hospital assignment", cdrrmo_pnp_bfp_users=[]), 401
    conn = get_db_connection()
    cdrrmo_pnp_bfp_users = conn.execute('SELECT role, assigned_municipality, contact_no, password, assigned_hospital FROM users WHERE role IN (?, ?, ?, ?, ?)', 
                                        ('cdrrmo', 'pnp', 'bfp', 'health', 'hospital')).fetchall()
    logger.debug(f"Retrieved {len(cdrrmo_pnp_bfp_users)} CDRRMO/PNP/BFP/City Health/Hospital users: {[dict(row) for row in cdrrmo_pnp_bfp_users]}")
    conn.close()
    return render_template('AgencyIn.html', cdrrmo_pnp_bfp_users=cdrrmo_pnp_bfp_users)

# Update auto_role
@app.route('/auto_role', methods=['POST', 'GET'])
@app.route('/auto_role', methods=['POST'])
def auto_role():
    logger.debug("Accessing /auto_role with method: %s", request.method)
    role = request.form['role'].lower()
    assigned_municipality = request.form['municipality']
    contact_no = request.form['contact_no']
    password = request.form['password']
    
    if role not in ['cdrrmo', 'pnp', 'bfp', 'health', 'hospital']:
        logger.error(f"Invalid role provided: {role}")
        return jsonify({'error': 'Invalid role'}), 400
    
    logger.debug(f"Auto login attempt: role={role}, municipality={assigned_municipality}, contact_no={contact_no}")
    
    conn = get_db_connection()
    if role == 'hospital':
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND password = ? AND assigned_municipality = ?
        ''', (role, contact_no, password, assigned_municipality)).fetchone()
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
        logger.debug(f"Auto login successful for user: {unique_id} ({user['role']})")
        if user['role'] == 'cdrrmo':
            return redirect(url_for('cdrrmo_dashboard'))
        elif user['role'] == 'pnp':
            return redirect(url_for('pnp_dashboard'))
        elif user['role'] == 'bfp':
            return redirect(url_for('bfp_dashboard'))
        elif user['role'] == 'health':
            return redirect(url_for('health_dashboard'))
        elif user['role'] == 'hospital':
            return redirect(url_for('hospital_dashboard'))
    logger.warning(f"Auto login failed for assigned_municipality: {assigned_municipality}, contact: {contact_no}, role: {role}")
    return render_template('AgencyIn.html', error="Invalid credentials", cdrrmo_pnp_bfp_users=[])

    


@app.route('/login', methods=['GET', 'POST'])
def log():
    if request.method == 'POST':
        barangay = request.form['barangay']
        contact_no = request.form['contact_no']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE barangay = ? AND contact_no = ? AND password = ?', (barangay, contact_no, password)).fetchone()
        conn.close()
        if user:
            session['role'] = 'barangay'
            session['unique_id'] = f"barangay_{barangay}_{contact_no}"
            session.permanent = True
            logger.info(f"Web login successful for barangay: {barangay}")
            return redirect(url_for('barangay_dashboard'))
        logger.warning(f"Web login failed for barangay: {barangay}")
        return "Invalid credentials", 401
    conn = get_db_connection()
    barangay_users = conn.execute('SELECT barangay, contact_no, password FROM users WHERE role = ?', ('barangay',)).fetchall()
    logger.debug(f"Retrieved {len(barangay_users)} Barangay users: {[dict(row) for row in barangay_users]}")
    conn.close()
    return render_template('LogInPage.html', barangay_users=barangay_users)

@app.route('/signup', methods=['GET', 'POST'])
def sign():
    if request.method == 'POST':
        barangay = request.form['barangay']
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, barangay, role, password) VALUES (?, ?, ?, ?)',
                         (username, barangay, 'barangay', password))
            conn.commit()
            logger.info(f"Signup successful for barangay: {barangay}, username: {username}")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            logger.error(f"Signup failed for {barangay}: Username already exists")
            return "Username already exists", 400
        except Exception as e:
            logger.error(f"Signup failed for {barangay}: {e}", exc_info=True)
            return f"Signup failed: {e}", 500
        finally:
            conn.close()
    return render_template('SignUpPage.html')


@app.route('/pass_reset', methods=['GET', 'POST'])
def pass_reset_route():
    return pass_reset()

@app.route('/go_to_login_page', methods=['GET'])
def go_to_login_page():
    logger.debug("Redirecting to /login")
    return redirect(url_for('login'))

@app.route('/go_to_signup_type', methods=['GET'])
def go_to_signup_type():
    logger.debug("Redirecting to /")
    return redirect(url_for('home'))

@app.route('/choose_login_type', methods=['GET'])
def choose_login_type():
    logger.debug("Rendering LoginType.html")
    return render_template('LoginType.html')



@app.route('/login_agency', methods=['GET'])
def go_to_cdrrmopnpbfpin():
    logger.debug("Redirecting to /login_agency")
    return redirect(url_for('login_agency'))

@app.route('/signup_muna', methods=['GET'])
def signup_muna():
    logger.debug("Redirecting to /signup_agency")
    return redirect(url_for('signup_agency'))

@app.route('/signup_na', methods=['GET'])
def signup_na():
    logger.debug("Redirecting to /signup_barangay")
    return redirect(url_for('signup_barangay'))

@app.route('/logout')
def logout():
    role = session.pop('role', None)
    session.clear()
    logger.debug(f"User logged out. Redirecting from role: {role}")
    if role == 'barangay':
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login_agency'))

def load_coords():
    coords_path = os.path.join(app.root_path, 'assets', 'coords.txt')
    alerts_data = []
    try:
        with open(coords_path, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) == 4:
                        barangay, municipality, message, timestamp = parts
                        alerts_data.append({
                            "barangay": barangay.strip(),
                            "municipality": municipality.strip(),
                            "message": message.strip(),
                            "timestamp": timestamp.strip()
                        })
    except FileNotFoundError:
        logger.warning("coords.txt not found, using empty alerts.")
    except Exception as e:
        logger.error(f"Error loading coords.txt: {e}")
    return alerts_data

@app.route('/api/send_alert', methods=['POST'])
def send_new_alert():
    data = request.json
    alert_id = str(uuid.uuid4())
    data['alert_id'] = alert_id
    alerts.append(data)
    logger.info(f"New alert received: {data}")
    if not data.get('image'):
        socketio.emit('new_alert', data, room='barangay_' + data.get('barangay', '').lower())
    return jsonify({'message': 'Alert sent', 'alert_id': alert_id})

@app.route('/send_alert', methods=['POST'])
def send_alert():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        lat = data.get('lat')
        lon = data.get('lon')
        emergency_type = data.get('emergency_type', 'General')
        image = data.get('image')
        user_role = data.get('user_role', 'unknown')
        image_upload_time = data.get('imageUploadTime', datetime.now().isoformat())
        barangay = data.get('barangay', 'N/A')
        municipality = get_municipality_from_barangay(barangay)
        if not municipality:
            logger.error(f"Could not find municipality for barangay: {barangay}")
            return jsonify({'error': 'Invalid barangay'}), 400

        if image:
            upload_time = datetime.fromisoformat(image_upload_time)
            if (datetime.now() - upload_time).total_seconds() > 30 * 60:
                image = None
                emergency_type = 'Not Specified'

        alert = {
            'lat': lat,
            'lon': lon,
            'emergency_type': emergency_type,
            'image': image,
            'role': user_role,
            'house_no': data.get('house_no', 'N/A'),
            'street_no': data.get('street_no', 'N/A'),
            'barangay': barangay,
            'municipality': municipality,
            'timestamp': datetime.now(pytz.timezone('Asia/Manila')).isoformat(),
            'imageUploadTime': image_upload_time,
            'alert_id': str(uuid.uuid4()),
            'user_barangay': barangay
        }
        
        

        alerts.append(alert)
        socketio.emit('new_alert', alert)
        return jsonify({'status': 'success', 'message': 'Alert sent'}), 200
    except Exception as e:
        logger.error(f"Error processing send_alert: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats')
def get_stats():
    try:
        total = len(alerts)
        critical = len([a for a in alerts if a.get('emergency_type', '').lower() == 'critical'])
        return jsonify({'total': total, 'critical': critical})
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return jsonify({'error': 'Failed to retrieve stats'}), 500

@app.route('/api/distribution')
def get_distribution():
    try:
        role = request.args.get('role', 'all')
        if role == 'barangay':
            filtered_alerts = [a for a in alerts if a.get('role') == 'barangay' or a.get('barangay')]
        elif role == 'cdrrmo':
            filtered_alerts = [a for a in alerts if a.get('role') == 'cdrrmo' or a.get('assigned_municipality')]
        elif role == 'pnp':
            filtered_alerts = [a for a in alerts if a.get('role') == 'pnp' or a.get('assigned_municipality')]
        elif role == 'bfp':
            filtered_alerts = [a for a in alerts if a.get('role') == 'bfp' or a.get('assigned_municipality')]
        elif role == 'health':
            filtered_alerts = [a for a in alerts if a.get('role') == 'health' or a.get('assigned_municipality')]
        elif role == 'hospital':
            filtered_alerts = [a for a in alerts if a.get('role') == 'health' or a.get('assigned_municipality')]
        else:
            filtered_alerts = alerts
        types = [a.get('emergency_type', 'unknown') for a in filtered_alerts]
        return jsonify(dict(Counter(types)))
    except Exception as e:
        logger.error(f"Error in get_distribution: {e}")
        return jsonify({'error': 'Failed to retrieve distribution'}), 500

@app.route('/add_alert', methods=['POST'])
def add_alert():
    data = request.form
    new_alert = {
        "barangay": data['barangay'],
        "municipality": data['municipality'],
        "message": data['message'],
        "timestamp": data['timestamp']
    }
    alerts.append(new_alert)
    return jsonify({"status": "success", "alert": new_alert})

@app.route('/export_alerts')
def export_alerts():
    with open('alerts.json', 'w') as f:
        json.dump(alerts, f, indent=4)
    return jsonify({"status": "success", "file": "alerts.json"})

#For Charts

@socketio.on('barangay_charts_response')
def handle_barangay_charts_response(data):
    chart_data = get_barangay_chart_data('today', data.get('barangay'))
    socketio.emit('barangay_charts_response_update', chart_data, broadcast=True)
    chart_data_cdrrmo = get_cdrrmo_chart_data('today', data.get('barangay'))
    socketio.emit('cdrrmo_charts_response_update', chart_data_cdrrmo, broadcast=True)
    chart_data_pnp = get_pnp_chart_data('today', data.get('barangay'))
    socketio.emit('pnp_charts_response_update', chart_data_pnp, broadcast=True)
    
@socketio.on('bfp_response')
def handle_bfp_response(data):
    chart_data = get_bfp_chart_data('today', data.get('barangay'))
    socketio.emit('bfp_charts_response_update', chart_data, broadcast=True)
    
@socketio.on('cdrrmo_charts_response')
def handle_cdrrmo_charts_response(data):
    chart_data = get_cdrrmo_chart_data('today', data.get('barangay'))
    socketio.emit('cdrrmo_charts_response_update', chart_data, broadcast=True)
    


@socketio.on('barangay_hospital_response')
def handle_barangay_hospital_response(data):
    chart_data = get_barangay_health_chart_data('today', data.get('barangay'))
    socketio.emit('barangay_hospital_response_update', chart_data, broadcast=True)
    
@socketio.on('pnp_charts_response')
def handle_pnp_charts_response(data):
    chart_data = get_pnp_chart_data('today', data.get('barangay'))
    socketio.emit('pnp_charts_response_update', chart_data, broadcast=True)




#/For Charts

@app.route('/barangay_dashboard')
def barangay_dashboard():
    try:
        if 'role' not in session or session['role'] != 'barangay':
            return redirect(url_for('login'))
        stats = get_barangay_stats()
        unique_id = session.get('unique_id')
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE barangay = ? AND contact_no = ?
        ''', (unique_id.split('_')[0], unique_id.split('_')[1])).fetchone()
        conn.close()
        
        if not unique_id or not user or user['role'] != 'barangay':
            logger.warning("Unauthorized access to barangay_dashboard. Session: %s, User: %s", session, user)
            return redirect(url_for('login'))
        
        barangay = user['barangay']
        assigned_municipality = user['assigned_municipality'] or 'San Pablo City'
        latest_alert = get_latest_alert()
        stats = get_barangay_stats()
        the_stats = get_the_stats(barangay)
        new_alert = get_new_alert(barangay)
        responded_count = get_barangay_responded_count(barangay)

        coords = barangay_coords.get(assigned_municipality, {}).get(barangay, {'lat': 14.5995, 'lon': 120.9842})
        
        try:
            lat_coord = float(coords.get('lat', 14.5995))
            lon_coord = float(coords.get('lon', 120.9842))
        except (ValueError, TypeError):
            logger.error(f"Invalid coordinates for {barangay} in {assigned_municipality}, using defaults")
            lat_coord = 14.5995
            lon_coord = 120.9842

        logger.debug(f"Rendering BarangayDashboard for {barangay} in {assigned_municipality}")
        session['barangay'] = barangay 
        return render_template('BarangayDashboard.html', 
                            latest_alert=latest_alert, 
                            stats=stats, 
                            responded_count=responded_count,
                            the_stats=the_stats,
                            new_alert=new_alert,
                            barangay=barangay, 
                            lat_coord=lat_coord, 
                            lon_coord=lon_coord, 
                            google_api_key=GOOGLE_API_KEY)

    except Exception as e:
        logger.error(f"Error in barangay_dashboard: {e}")
        return "Internal Server Error", 500


@app.route('/barangay_emergency_types')
def barangay_emergency_types():
    if 'role' not in session or session['role'] != 'barangay':
        logger.warning("Unauthorized access to barangay_emergency_types")
        return jsonify({'error': 'Unauthorized'}), 401
    barangay = session.get('barangay')  # Use session-stored barangay
    if not barangay:
        logger.error("No barangay found in session")
        return jsonify({'Road Accident': 0, 'Crime Incident': 0, 'Fire Incident': 0, 'Health Emergency': 0}), 200
    emergency_types = get_barangay_emergency_types(barangay)
    return jsonify(emergency_types)

@app.route('/barangay_responded_count')
def barangay_responded_count():
    try:
        barangay = session.get('barangay')
        if not barangay:
            logger.error("No barangay found in session for responded count")
            return jsonify({'responded_count': 0}), 200
        count = get_barangay_responded_count(barangay)
        return jsonify({'responded_count': count})
    except Exception as e:
        logger.error(f"Error in barangay_responded_count: {e}")
        return jsonify({'responded_count': 0}), 500

@app.route('/cdrrmo_dashboard')
def cdrrmo_dashboard():
    try:
        if 'role' not in session or session['role'] != 'cdrrmo':
            return redirect(url_for('login_agency'))
        stats = get_cdrrmo_stats()
        unique_id = session.get('unique_id')
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND assigned_municipality = ?
        ''', ('cdrrmo', unique_id.split('_')[2], unique_id.split('_')[1])).fetchone()
        conn.close()
        
        if not unique_id or not user or user['role'] != 'cdrrmo':
            logger.warning("Unauthorized access to cdrrmo_dashboard. Session: %s, User: %s", session, user)
            return redirect(url_for('login_agency'))
        
        assigned_municipality = user['assigned_municipality'] or "San Pablo City"
        stats = get_cdrrmo_stats()
        le_stat = get_the_cdrrmo_stats(municipality=user['municipality'])
        responded_count = get_cdrrmo_responded_count()
        coords = municipality_coords.get(assigned_municipality, {'lat': 14.5995, 'lon': 120.9842})
        
        try:
            lat_coord = float(coords.get('lat', 14.5995))
            lon_coord = float(coords.get('lon', 120.9842))
        except (ValueError, TypeError):
            logger.error(f"Invalid coordinates for {assigned_municipality}, using defaults")
            lat_coord = 14.5995
            lon_coord = 120.9842

        alerts_per_month = get_cdrrmo_alerts_per_month()
        logger.debug(f"Rendering CDRRMODashboard for {assigned_municipality}")
        return render_template('CDRRMODashboard.html', 
                               stats=stats, 
                               municipality=assigned_municipality, 
                               le_stat=le_stat,
                               responded_count=responded_count,
                               alerts_per_month=alerts_per_month,
                               lat_coord=lat_coord, 
                               lon_coord=lon_coord, 
                               google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Error in cdrrmo_dashboard: {e}")
        return "Internal Server Error", 500

@app.route('/pnp_dashboard')
def pnp_dashboard():
    try:
        if 'role' not in session or session['role'] != 'pnp':
            return redirect(url_for('login_agency'))
        stats = get_pnp_stats()
        unique_id = session.get('unique_id')
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND assigned_municipality = ?
        ''', ('pnp', unique_id.split('_')[2], unique_id.split('_')[1])).fetchone()
        conn.close()
        
        if not unique_id or not user or user['role'] != 'pnp':
            logger.warning("Unauthorized access to pnp_dashboard. Session: %s, User: %s", session, user)
            return redirect(url_for('login_agency'))
        conn = get_db_connection()
        # Check if 'assigned_barangay' column exists, fallback to 'assigned_municipality'
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [col['name'] for col in cursor.fetchall()]
        location_column = 'assigned_barangay' if 'assigned_barangay' in columns else 'assigned_municipality'

        assigned_municipality = user['assigned_municipality'] or "San Pablo City"
        assigned_barangay = user[location_column] or "San Pablo City"  # Fallback to default
        session['assigned_barangay'] = assigned_barangay  # Ensure session has barangay
        stats = get_pnp_stats()
        le_pnp_stats = get_the_pnp_stats(assigned_barangay)
        responded_count = get_pnp_responded_count()
        coords = municipality_coords.get(assigned_municipality, {'lat': 14.5995, 'lon': 120.9842})
        
        try:
            lat_coord = float(coords.get('lat', 14.5995))
            lon_coord = float(coords.get('lon', 120.9842))
        except (ValueError, TypeError):
            logger.error(f"Invalid coordinates for {assigned_municipality}, using defaults")
            lat_coord = 14.5995
            lon_coord = 120.9842

        alerts_per_month = get_pnp_alerts_per_month()
        logger.debug(f"Rendering PNPDashboard for {assigned_municipality}")
        return render_template('PNPDashboard.html', 
                               stats=stats, 
                               municipality=assigned_municipality, 
                               le_pnp_stats=le_pnp_stats,
                               responded_count=responded_count,
                               alerts_per_month=alerts_per_month,
                               lat_coord=lat_coord, 
                               lon_coord=lon_coord, 
                               google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Error in pnp_dashboard: {e}")
        return "Internal Server Error", 500
    




@app.route('/bfp_dashboard')
def bfp_dashboard():
    try:
        if 'role' not in session or session['role'] != 'bfp':
            return redirect(url_for('login_agency'))
        stats = get_bfp_stats()
        bfp_stats = get_the_stat_bfp()
        unique_id = session.get('unique_id')
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND assigned_municipality = ?
        ''', ('bfp', unique_id.split('_')[2], unique_id.split('_')[1])).fetchone()
        conn.close()
        
        if not unique_id or not user or user['role'] != 'bfp':
            logger.warning("Unauthorized access to bfp_dashboard. Session: %s, User: %s", session, user)
            return redirect(url_for('login_agency'))
        
        assigned_municipality = user['assigned_municipality'] or "San Pablo City"
        bfp_stats = get_the_stat_bfp()
        responded_count = get_bfp_responded_count()
        stats = get_bfp_stats()
        coords = municipality_coords.get(assigned_municipality, {'lat': 14.5995, 'lon': 120.9842})
        
        try:
            lat_coord = float(coords.get('lat', 14.5995))
            lon_coord = float(coords.get('lon', 120.9842))
        except (ValueError, TypeError):
            logger.error(f"Invalid coordinates for {assigned_municipality}, using defaults")
            lat_coord = 14.5995
            lon_coord = 120.9842

        alerts_per_month = get_bfp_alerts_per_month()
        logger.debug(f"Rendering BFPDashboard for {assigned_municipality}")
        return render_template('BFPDashboard.html', 
                               stats=stats, 
                               bfp_stats=bfp_stats,
                               municipality=assigned_municipality, 
                               responded_count=responded_count,
                               alerts_per_month=alerts_per_month,
                               lat_coord=lat_coord,
                               lon_coord=lon_coord,
                               google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Error in bfp_dashboard: {e}")
        return "Internal Server Error", 500

@app.route('/health_dashboard')
def health_dashboard():
    try:
        if 'role' not in session or session['role'] != 'health':
            return redirect(url_for('login_agency'))
        stats = get_health_stats()
        unique_id = session.get('unique_id')
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND assigned_municipality = ?
        ''', ('health', unique_id.split('_')[2], unique_id.split('_')[1])).fetchone()
        conn.close()
        
        if not unique_id or not user or user['role'] != 'health':
            logger.warning("Unauthorized access to health_dashboard. Session: %s, User: %s", session, user)
            return redirect(url_for('login_agency'))
        
        assigned_municipality = user['assigned_municipality'] or "San Pablo City"
        stats = get_health_stats()
        coords = municipality_coords.get(assigned_municipality, {'lat': 14.5995, 'lon': 120.9842})
        
        try:
            lat_coord = float(coords.get('lat', 14.5995))
            lon_coord = float(coords.get('lon', 120.9842))
        except (ValueError, TypeError):
            logger.error(f"Invalid coordinates for {assigned_municipality}, using defaults")
            lat_coord = 14.5995
            lon_coord = 120.9842

        logger.debug(f"Rendering HealthDashboard for {assigned_municipality}")
        return render_template('HealthDashboard.html', 
                               stats=stats, 
                               municipality=assigned_municipality, 
                               lat_coord=lat_coord,
                               lon_coord=lon_coord,
                               google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Error in health_dashboard: {e}")
        return "Internal Server Error", 500


@app.route('/hospital_dashboard')
def hospital_dashboard():
    try:
        if 'role' not in session or session['role'] != 'hospital':
            return redirect(url_for('login_agency'))
        stats = get_health_stats()
        unique_id = session.get('unique_id')
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users WHERE role = ? AND contact_no = ? AND assigned_municipality = ?
        ''', ('hospital', unique_id.split('_')[2], unique_id.split('_')[1])).fetchone()
        conn.close()
        
        if not unique_id or not user or user['role'] != 'hospital':
            logger.warning("Unauthorized access to health_dashboard. Session: %s, User: %s", session, user)
            return redirect(url_for('login_agency'))
        
        assigned_municipality = user['assigned_municipality'] or "San Pablo City"
        assigned_hospital = session.get('assigned_hospital', 'Unknown Hospital').title()
        stats = get_hospital_stats()
        coords = municipality_coords.get(assigned_municipality, {'lat': 14.5995, 'lon': 120.9842})
        
        try:
            lat_coord = float(coords.get('lat', 14.5995))
            lon_coord = float(coords.get('lon', 120.9842))
        except (ValueError, TypeError):
            logger.error(f"Invalid coordinates for {assigned_municipality}, using defaults")
            lat_coord = 14.5995
            lon_coord = 120.9842

        logger.debug(f"Rendering HospitalDashboard for {assigned_municipality}")
        return render_template('HospitalDashboard.html', 
                               stats=stats, 
                               municipality=assigned_municipality, 
                               assigned_hospital=assigned_hospital,
                               lat_coord=lat_coord,
                               lon_coord=lon_coord,
                               google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Error in health_dashboard: {e}")
        return "Internal Server Error", 500

# ADD THIS FUNCTION (anywhere in file)
# ADD THESE ROUTES (anywhere in routes section)
@app.route('/send_dilg_password', methods=['POST'])
def send_dilg_password_route():
    data = request.get_json()
    password = data.get('password')
    if not password:
        return jsonify({'error': 'No password'}), 400
    return send_dilg_password(password)  # ← Now calls the function correctly


@app.route('/login_dilg', methods=['POST'])
def login_dilg():
    municipality = request.form['municipality']
    password = request.form['password']
    
    if password.endswith('DILG!'):
        session['role'] = 'dilg'
        session['municipality'] = municipality
        session['contact_no'] = 'DILG_ADMIN'
        logger.info(f"DILG login successful: {municipality}")
        return redirect('/dilg_dashboard')
    
    return render_template('AgencyIn.html', error="Invalid DILG password")

@app.route('/dilg_accounts')
def dilg_accounts_route():
    return dilg_accounts()



def get_latest_alert():
    try:
        if alerts:
            return alerts[-1]
        return None
    except Exception as e:
        logger.error(f"Error in get_latest_alert: {e}")
        return None

def get_new_alert(barangay):
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT * FROM alerts WHERE barangay = ? ORDER BY timestamp DESC LIMIT 1', (barangay,))
        alert = cursor.fetchone()
        conn.close()
        return dict(alert) if alert else None
    except Exception as e:
        logger.error(f"Error fetching latest alert for {barangay}: {e}")
        return None

def get_barangay_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'barangay' or a.get('barangay')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_barangay_stats: {e}")
        return Counter()

def get_cdrrmo_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'cdrrmo' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_cdrrmo_stats: {e}")
        return Counter()
    
def get_the_cdrrmo_stats(municipality):
    try:
        conn = get_db_connection()
        # Check if 'municipality' column exists
        cursor = conn.execute("PRAGMA table_info(cdrrmo_response)")
        columns = [col['name'] for col in cursor.fetchall()]
        location_column = 'municipality' if 'municipality' in columns else 'barangay'
        
        cursor = conn.execute(f'''
            SELECT COUNT(*) as total 
            FROM cdrrmo_response 
            WHERE {location_column} = ? OR {location_column} IS NULL
        ''', (municipality,))
        total = cursor.fetchone()['total']
        conn.close()
        return type('Stats', (), {'total': lambda self: total})()
    except Exception as e:
        logger.error(f"Error fetching CDRRMO stats for {municipality}: {e}")
        return type('Stats', (), {'total': lambda self: 0})()

def get_pnp_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'pnp' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_pnp_stats: {e}")
        return Counter()

def get_bfp_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'bfp' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_bfp_stats: {e}")
        return Counter()
    
def get_the_pnp_stats(municipality):
    try:
        conn = get_db_connection()
        # Check if 'municipality' column exists
        cursor = conn.execute("PRAGMA table_info(pnp_response)")
        columns = [col['name'] for col in cursor.fetchall()]
        location_column = 'municipality' if 'municipality' in columns else 'barangay'
        
        cursor = conn.execute(f'''
            SELECT COUNT(*) as total 
            FROM pnp_response 
            WHERE {location_column} = ? OR {location_column} IS NULL
        ''', (municipality,))
        total = cursor.fetchone()['total']
        conn.close()
        return type('Stats', (), {'total': lambda self: total})()
    except Exception as e:
        logger.error(f"Error fetching PNP stats for {municipality}: {e}")
        return type('Stats', (), {'total': lambda self: 0})()
    
def get_health_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'health' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_health_stats: {e}")
        return Counter()



def get_hospital_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'hospital' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_hospital_stats: {e}")
        return Counter()

app.route('/barangay_charts')(barangay_charts)
app.route('/barangay_charts_data')(barangay_charts_data)
app.route('/barangay_fire_charts_data')(barangay_fire_charts_data)
app.route('/barangay_health_charts_data')(barangay_health_charts_data)
app.route('/barangay_crime_charts_data')(barangay_crime_charts_data)
app.route('/cdrrmo_charts')(cdrrmo_charts)
app.route('/cdrrmo_charts_data')(cdrrmo_charts_data)
app.route('/pnp_charts')(pnp_charts)
app.route('/pnp_charts_data')(pnp_charts_data)
app.route('/pnp_fire_charts_data')(pnp_fire_charts_data)
app.route('/pnp_crime_charts_data')(pnp_crime_charts_data)
app.route('/bfp_charts')(bfp_charts)
app.route('/bfp_charts_data')(bfp_charts_data)
app.route('/health_charts')(health_charts)
app.route('/health_charts_data')(health_charts_data)
app.route('/hospital_charts')(hospital_charts)
app.route('/hospital_charts_data')(hospital_charts_data)

app.route('/download_apk_folder')(download_apk_folder)
app.route('/generate_qr')(generate_qr)

if __name__ == '__main__':
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS barangay_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                road_accident_cause TEXT,
                road_accident_type TEXT,
                weather TEXT,
                road_condition TEXT,
                vehicle_type TEXT,
                driver_age TEXT,
                driver_gender TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                alcohol_used TEXT,           
                incident_hour INTEGER,        
                incident_weekday INTEGER,   
                barangay_clean TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS bfp_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                fire_cause TEXT,
                occupancy_type TEXT,
                fire_class TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT DEFAULT 'Fire Incident',
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                prediction TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS cdrrmo_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                road_accident_cause TEXT,
                road_accident_type TEXT,
                weather TEXT,
                road_condition TEXT,
                vehicle_type TEXT,
                driver_age TEXT,
                driver_gender TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                alcohol_used TEXT,           
                incident_hour INTEGER,        
                incident_weekday INTEGER,   
                barangay_clean TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pnp_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                road_accident_cause TEXT,
                road_accident_type TEXT,
                weather TEXT,
                road_condition TEXT,
                vehicle_type TEXT,
                driver_age TEXT,
                driver_gender TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                alcohol_used TEXT,           
                incident_hour INTEGER,        
                incident_weekday INTEGER,   
                barangay_clean TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS health_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                health_type TEXT,
                health_cause TEXT,
                weather TEXT,
                patient_age TEXT,
                patient_gender TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS hospital_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                health_type TEXT,
                health_cause TEXT,
                weather TEXT,
                patient_age TEXT,
                patient_gender TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                assigned_hospital TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS barangay_fire_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                fire_cause TEXT,
                occupancy_type TEXT,
                fire_class TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT DEFAULT 'Fire Incident',
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                prediction TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS barangay_health_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                health_type TEXT,
                health_cause TEXT,
                weather TEXT,
                patient_age TEXT,
                patient_gender TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS barangay_crime_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                crime_type TEXT,
                crime_cause TEXT,
                level TEXT,
                suspect_gender TEXT,
                victim_gender TEXT,
                suspect_age TEXT,
                victim_age TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pnp_crime_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                crime_type TEXT,
                crime_cause TEXT,
                level TEXT,
                suspect_gender TEXT,
                victim_gender TEXT,
                suspect_age TEXT,
                victim_age TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                municipality TEXT,
                emergency_type TEXT,
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pnp_alerts (
                alert_id TEXT PRIMARY KEY,
                lat REAL,
                lon REAL,
                municipality TEXT,
                barangay TEXT,
                emergency_type TEXT,
                timestamp TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pnp_fire_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT,
                fire_cause TEXT,
                occupancy_type TEXT,
                fire_class TEXT,
                lat REAL,
                lon REAL,
                barangay TEXT,
                emergency_type TEXT DEFAULT 'Fire Incident',
                timestamp TEXT,
                responded BOOLEAN DEFAULT TRUE,
                prediction TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS hospital_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                barangay TEXT NOT NULL,
                assigned_hospital TEXT NOT NULL,
                health_type TEXT DEFAULT 'N/A',
                health_cause TEXT DEFAULT 'N/A',
                patient_age TEXT DEFAULT 'N/A',
                patient_gender TEXT DEFAULT 'N/A',
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                lat REAL,
                lon REAL,
                image TEXT,
                FOREIGN KEY (alert_id, barangay) REFERENCES alerts (alert_id, barangay)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS health_responses (
                alert_id TEXT NOT NULL,
                barangay TEXT NOT NULL,
                emergency_type TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                image TEXT,
                PRIMARY KEY (alert_id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS hospital_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                barangay TEXT NOT NULL,
                assigned_hospital TEXT NOT NULL,
                health_type TEXT DEFAULT 'N/A',
                health_cause TEXT DEFAULT 'N/A',
                patient_age TEXT DEFAULT 'N/A',
                patient_gender TEXT DEFAULT 'N/A',
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                lat REAL,
                lon REAL,
                image TEXT,
                FOREIGN KEY (alert_id, barangay) REFERENCES alerts (alert_id, barangay)
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("barangay_response initialized successfully in users_web.db")
        logger.info("bfp_response initialized successfully in users_web.db")
        logger.info("cdrrmo_response initialized successfully in users_web.db")
        logger.info("pnp_response initialized successfully in users_web.db")
        logger.info("health_response initialized successfully in users_web.db")
        logger.info("hospital_response initialized successfully in users_web.db")
        logger.info("barangay_fire_response initialized successfully in users_web.db")
        logger.info("barangay_health_response initialized successfully in users_web.db")
        logger.info("barangay_crime_response initialized successfully in users_web.db")
        logger.info("All Tables Are Initialized Successfully In users_web.db")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                barangay TEXT,
                role TEXT NOT NULL CHECK(role IN ('resident', 'barangay', 'cdrrmo', 'pnp', 'bfp', 'health', 'hospital')),
                contact_no TEXT UNIQUE NOT NULL,
                assigned_municipality TEXT,
                province TEXT,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database 'users_web.db' initialized successfully or already exists.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    

    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
    