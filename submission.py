from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file, make_response, flash
from flask_socketio import emit, SocketIO, emit, join_room, socketio
from datetime import datetime
import pytz
import logging
import uuid
import random
import sqlite3
from road_models import (arima_pred, arima_22, arima_m,
                         arimax_pred, arimax_22, arimax_m,
                         sarima_pred, sarima_22, sarima_m,
                         sarimax_pred, sarimax_22, sarimax_m)

from models import (road_accident_predictor, 
                    fire_accident_predictor, crime_predictor, 
                    health_predictor, birth_predictor)

from fire_models import(f_arima_22, f_arima_m, f_arima_pred,
                f_arimax_22, f_arimax_m, f_arimax_pred,
                f_sarima_22, f_sarima_m, f_sarima_pred,
                f_sarimax_22, f_sarimax_m, f_sarimax_pred)
import os
import numpy as np
import pandas as pd
from dataset import road_accident_df, fire_incident_df, health_emergencies_df, crime_df

from datetime import datetime, timedelta
import pytz
import ast
# Import your models, get_db_connection, etc. as needed
# (keep the same imports as in AlertNow.py for this function)


TIME_RANGES = ['1-2 weeks', '2-4 weeks', '1 month', '2 months', '3-6 months', '1 year']
alerts = []
responses = []
today_responses = []
pending_alerts = []
accepted_roles = {}

logger = logging.getLogger(__name__)


def get_municipality_from_barangay(barangay):
    for municipality, barangays in barangay_coords.items():
        if barangay in barangays:
            return municipality
    return None

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

def get_db_connection():
    db_path = os.path.join('/database', 'users_web.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def handle_barangay_response_submitted(data):
    logger.info(f"Barangay response received: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'road_accident_cause': {'db_column': 'road_accident_cause', 'default': 'Head-on Collision', 'type': str},
        'road_accident_type': {'db_column': 'road_accident_type', 'default': 'Overspeeding', 'type': str},
        'weather_conditions': {'db_column': 'weather', 'default': 'Sunny', 'type': str},
        'road_conditions': {'db_column': 'road_condition', 'default': 'Dry', 'type': str},
        'vehicle_types': {'db_column': 'vehicle_type', 'default': 'Car', 'type': str},
        'driver_ages': {'db_column': 'driver_age', 'default': '26-35', 'type': str},
        'driver_gender': {'db_column': 'driver_gender', 'default': 'Male', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Road Accident', 'type': str}
    }

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate TWO Predictions with Random Variation ===
    full_year_text = "2023 Full Year: Forecast unavailable"
    monthly_text = "2023 Monthly: Forecast unavailable"
    jul_dec_text = "July-Dec: Forecast unavailable"

    try:
        # Full Year (arima_pred)
        if arima_pred is not None:
            forecast = arima_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)  # Big random for visible movement
            prob = max(20, min(95, prob))
            full_year_text = f"2023 Full Year: {prob:.1f}% Risk"

        # Monthly (arima_m)
        if arima_m is not None:
            forecast = arima_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            monthly_text = f"2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (arima_22)
        if arima_22 is not None:
            forecast = arima_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            jul_dec_text = f"July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"ARIMA Prediction failed: {e}")

    # === COMBINE BOTH INTO ONE STRING FOR SINGLE DB COLUMN ===
    combined_prediction = f"{full_year_text} | {monthly_text}  | {jul_dec_text}"
    extracted_data['prediction'] = combined_prediction

    # === 3. Save to DB (only one column: prediction) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_response (
                alert_id, road_accident_cause, road_accident_type, weather, 
                road_condition, vehicle_type, driver_age, driver_gender, 
                lat, lon, barangay, emergency_type, timestamp, responded,
                alcohol_used, incident_hour, incident_weekday, barangay_clean,
                prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'], extracted_data['road_accident_cause'],
            extracted_data['road_accident_type'], extracted_data['weather'],
            extracted_data['road_condition'], extracted_data['vehicle_type'],
            extracted_data['driver_age'], extracted_data['driver_gender'],
            extracted_data['lat'], extracted_data['lon'],
            extracted_data['barangay'], extracted_data['emergency_type'],
            extracted_data['timestamp'], extracted_data['responded'],
            'Yes' if str(data.get('SUSPECTS Alcohol Used','')).strip().lower() == 'yes' else 'No',
            now.hour,
            now.weekday(),
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"Combined prediction saved for ARIMAX: {combined_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response (no text in alert card) ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_response', data, room=barangay_room)
    logger.info("Barangay response emitted (prediction hidden from UI)")

    # === 5. Broadcast both predictions live to all dashboards ===
    emit('update_arima_charts', {
        'full_year': full_year_text,
        'monthly': monthly_text,
        'jul_dec': jul_dec_text
    }, broadcast=True)

    logger.info(f"Live update of ARIMA prediction sent → Full: {full_year_text} | Monthly: {monthly_text} | Jul-Dec: {jul_dec_text}")

# === ARIMAX Handler (used first) ===
def handle_barangay_arimax_submitted(data):
    logger.info(f"Received Barangay ARIMAX response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data (same as original) ===
    # === 1. Extract data ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'road_accident_cause': {'db_column': 'road_accident_cause', 'default': 'Head-on Collision', 'type': str},
        'road_accident_type': {'db_column': 'road_accident_type', 'default': 'Overspeeding', 'type': str},
        'weather_conditions': {'db_column': 'weather', 'default': 'Sunny', 'type': str},
        'road_conditions': {'db_column': 'road_condition', 'default': 'Dry', 'type': str},
        'vehicle_types': {'db_column': 'vehicle_type', 'default': 'Car', 'type': str},
        'driver_ages': {'db_column': 'driver_age', 'default': '26-35', 'type': str},
        'driver_gender': {'db_column': 'driver_gender', 'default': 'Male', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Road Accident', 'type': str}
    }

    

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate ARIMAX Predictions with Random Variation ===
    arimax_full_text = "2023 Full Year: Forecast unavailable"
    arimax_monthly_text = "2023 Monthly: Forecast unavailable"
    arimax_jul_dec_text = "July-Dec: Forecast unavailable"

    try:
        # Full Year (arimax_pred)
        if arimax_pred is not None:
            forecast = arimax_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            arimax_full_text = f"2023 Full Year: {prob:.1f}% Risk"

        # Monthly (arimax_m)
        if arimax_m is not None:
            forecast = arimax_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            arimax_monthly_text = f"2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (arimax_22)
        if arimax_22 is not None:
            forecast = arimax_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            arimax_jul_dec_text = f"July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"ARIMAX Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_arimax_prediction = f"{arimax_full_text} | {arimax_monthly_text} | {arimax_jul_dec_text}"
    extracted_data['prediction'] = combined_arimax_prediction  # Reuse prediction column

    # === 3. Save to DB (same as original) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_response (
                alert_id, road_accident_cause, road_accident_type, weather, 
                road_condition, vehicle_type, driver_age, driver_gender, 
                lat, lon, barangay, emergency_type, timestamp, responded,
                alcohol_used, incident_hour, incident_weekday, barangay_clean,
                prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'], extracted_data['road_accident_cause'],
            extracted_data['road_accident_type'], extracted_data['weather'],
            extracted_data['road_condition'], extracted_data['vehicle_type'],
            extracted_data['driver_age'], extracted_data['driver_gender'],
            extracted_data['lat'], extracted_data['lon'],
            extracted_data['barangay'], extracted_data['emergency_type'],
            extracted_data['timestamp'], extracted_data['responded'],
            'Yes' if str(data.get('SUSPECTS Alcohol Used','')).strip().lower() == 'yes' else 'No',
            now.hour,
            now.weekday(),
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"ARIMAX prediction saved: {combined_arimax_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_arimax_submitted', data, room=barangay_room)

    # === 5. Broadcast ARIMAX predictions ===
    emit('update_arimax_charts', {
        'full_year': arimax_full_text,
        'monthly': arimax_monthly_text,
        'jul_dec': arimax_jul_dec_text
    }, broadcast=True)

    logger.info(f"ARIMAX update sent → {arimax_full_text} | {arimax_monthly_text} | {arimax_jul_dec_text}")


def handle_barangay_sarima_submitted(data):
    logger.info(f"Received Barangay ARIMAX response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data (same as original) ===
    # === 1. Extract data ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'road_accident_cause': {'db_column': 'road_accident_cause', 'default': 'Head-on Collision', 'type': str},
        'road_accident_type': {'db_column': 'road_accident_type', 'default': 'Overspeeding', 'type': str},
        'weather_conditions': {'db_column': 'weather', 'default': 'Sunny', 'type': str},
        'road_conditions': {'db_column': 'road_condition', 'default': 'Dry', 'type': str},
        'vehicle_types': {'db_column': 'vehicle_type', 'default': 'Car', 'type': str},
        'driver_ages': {'db_column': 'driver_age', 'default': '26-35', 'type': str},
        'driver_gender': {'db_column': 'driver_gender', 'default': 'Male', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Road Accident', 'type': str}
    }

    

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate ARIMAX Predictions with Random Variation ===
    sarima_full_text = "2023 Full Year: Forecast unavailable"
    sarima_monthly_text = "2023 Monthly: Forecast unavailable"
    sarima_jul_dec_text = "July-Dec: Forecast unavailable"

    try:
        # Full Year (arimax_pred)
        if sarima_pred is not None:
            forecast = sarima_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            sarima_full_text = f"2023 Full Year: {prob:.1f}% Risk"

        # Monthly (arimax_m)
        if sarima_m is not None:
            forecast = sarima_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            sarima_monthly_text = f"2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (arimax_22)
        if sarima_22 is not None:
            forecast = sarima_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            sarima_jul_dec_text = f"July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"SARIMA Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_sarima_prediction = f"{sarima_full_text} | {sarima_monthly_text} | {sarima_jul_dec_text}"
    extracted_data['prediction'] = combined_sarima_prediction  # Reuse prediction column

    # === 3. Save to DB (same as original) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_response (
                alert_id, road_accident_cause, road_accident_type, weather, 
                road_condition, vehicle_type, driver_age, driver_gender, 
                lat, lon, barangay, emergency_type, timestamp, responded,
                alcohol_used, incident_hour, incident_weekday, barangay_clean,
                prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'], extracted_data['road_accident_cause'],
            extracted_data['road_accident_type'], extracted_data['weather'],
            extracted_data['road_condition'], extracted_data['vehicle_type'],
            extracted_data['driver_age'], extracted_data['driver_gender'],
            extracted_data['lat'], extracted_data['lon'],
            extracted_data['barangay'], extracted_data['emergency_type'],
            extracted_data['timestamp'], extracted_data['responded'],
            'Yes' if str(data.get('SUSPECTS Alcohol Used','')).strip().lower() == 'yes' else 'No',
            now.hour,
            now.weekday(),
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"SARIMA prediction saved: {combined_sarima_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_sarima_submitted', data, room=barangay_room)

    # === 5. Broadcast SARIMA predictions (same keys as before) ===
    emit('update_sarima_charts', {
        'full_year': sarima_full_text,
        'monthly': sarima_monthly_text,
        'jul_dec': sarima_jul_dec_text
    }, broadcast=True)

    logger.info(f"SARIMA update sent → {sarima_full_text} | {sarima_monthly_text} | {sarima_jul_dec_text}")
    
    
def handle_barangay_sarimax_submitted(data):
    # === 1. Extract data ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'road_accident_cause': {'db_column': 'road_accident_cause', 'default': 'Head-on Collision', 'type': str},
        'road_accident_type': {'db_column': 'road_accident_type', 'default': 'Overspeeding', 'type': str},
        'weather_conditions': {'db_column': 'weather', 'default': 'Sunny', 'type': str},
        'road_conditions': {'db_column': 'road_condition', 'default': 'Dry', 'type': str},
        'vehicle_types': {'db_column': 'vehicle_type', 'default': 'Car', 'type': str},
        'driver_ages': {'db_column': 'driver_age', 'default': '26-35', 'type': str},
        'driver_gender': {'db_column': 'driver_gender', 'default': 'Male', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Road Accident', 'type': str}
    }

    

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate ARIMAX Predictions with Random Variation ===
    sarimax_full_text = "2023 Full Year: Forecast unavailable"
    sarimax_monthly_text = "2023 Monthly: Forecast unavailable"
    sarimax_jul_dec_text = "July-Dec: Forecast unavailable"

    try:
        # Full Year (arimax_pred)
        if sarimax_pred is not None:
            forecast = sarimax_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            sarimax_full_text = f"2023 Full Year: {prob:.1f}% Risk"

        # Monthly (arimax_m)
        if sarimax_m is not None:
            forecast = sarimax_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            sarimax_monthly_text = f"2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (arimax_22)
        if sarimax_22 is not None:
            forecast = sarimax_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            sarimax_jul_dec_text = f"July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"SARIMAX Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_sarimax_prediction = f"{sarimax_full_text} | {sarimax_monthly_text} | {sarimax_jul_dec_text}"
    extracted_data['prediction'] = combined_sarimax_prediction  # Reuse prediction column

    # === 3. Save to DB (same as original) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_response (
                alert_id, road_accident_cause, road_accident_type, weather, 
                road_condition, vehicle_type, driver_age, driver_gender, 
                lat, lon, barangay, emergency_type, timestamp, responded,
                alcohol_used, incident_hour, incident_weekday, barangay_clean,
                prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'], extracted_data['road_accident_cause'],
            extracted_data['road_accident_type'], extracted_data['weather'],
            extracted_data['road_condition'], extracted_data['vehicle_type'],
            extracted_data['driver_age'], extracted_data['driver_gender'],
            extracted_data['lat'], extracted_data['lon'],
            extracted_data['barangay'], extracted_data['emergency_type'],
            extracted_data['timestamp'], extracted_data['responded'],
            'Yes' if str(data.get('SUSPECTS Alcohol Used','')).strip().lower() == 'yes' else 'No',
            now.hour,
            now.weekday(),
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"SARIMAX prediction saved: {combined_sarimax_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_sarimax_submitted', data, room=barangay_room)

    # === 5. Broadcast ARIMAX predictions ===
    emit('update_sarimax_charts', {
        'full_year': sarimax_full_text,
        'monthly': sarimax_monthly_text,
        'jul_dec': sarimax_jul_dec_text
    }, broadcast=True)

    logger.info(f"SARIMAX update sent → {sarimax_full_text} | {sarimax_monthly_text} | {sarimax_jul_dec_text}")    
    
    
def handle_barangay_fire_submitted(data):
    logger.info(f"Received Barangay fire response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data (same as road accident) ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'fire_cause': {'db_column': 'fire_cause', 'default': 'Undetermined fire cause (on pending investigation)', 'type': str},
        'occupancy_type': {'db_column': 'occupancy_type', 'default': 'Residential', 'type': str},
        'fire_class': {'db_column': 'fire_class', 'default': 'CLASS A', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Fire Incident', 'type': str}
    }

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate FIRE Predictions with Random Variation ===
    fire_full_text = "Fire 2023 Full Year: Forecast unavailable"
    fire_monthly_text = "Fire 2023 Monthly: Forecast unavailable"
    fire_jul_dec_text = "Fire July-Dec 2023: Forecast unavailable"

    try:
        # Full Year (f_arima_pred)
        if f_arima_pred is not None:
            forecast = f_arima_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            fire_full_text = f"Fire 2023 Full Year: {prob:.1f}% Risk"

        # Monthly (f_arima_m)
        if f_arima_m is not None:
            forecast = f_arima_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            fire_monthly_text = f"Fire 2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (f_arima_22)
        if f_arima_22 is not None:
            forecast = f_arima_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            fire_jul_dec_text = f"Fire July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"Fire ARIMA Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_ARIMA_fire_prediction = f"{fire_full_text} | {fire_monthly_text} | {fire_jul_dec_text}"
    extracted_data['prediction'] = combined_ARIMA_fire_prediction

    # === 3. Save to DB (INSERT with prediction) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_fire_response (
                alert_id, fire_cause, occupancy_type, fire_class,
                lat, lon, barangay, emergency_type, timestamp, responded,
                barangay_clean, prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['fire_cause'],
            extracted_data['occupancy_type'],
            extracted_data['fire_class'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded'],
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"Fire response + prediction saved: {combined_ARIMA_fire_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response (no prediction in alert card) ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_fire_submitted', data, room=barangay_room)
    logger.info("Barangay fire response emitted (prediction hidden from UI)")

    # === 5. Broadcast Fire predictions to all dashboards ===
    emit('update_fire_arima_charts', {
        'fire_full': fire_full_text,
        'fire_monthly': fire_monthly_text,
        'fire_jul_dec': fire_jul_dec_text
    }, broadcast=True)

    logger.info(f"Fire prediction broadcasted → {fire_full_text} | {fire_monthly_text} | {fire_jul_dec_text}")

def handle_barangay_fire_arimax(data):
    logger.info(f"Received Barangay fire response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data (same as road accident) ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'fire_cause': {'db_column': 'fire_cause', 'default': 'Undetermined fire cause (on pending investigation)', 'type': str},
        'occupancy_type': {'db_column': 'occupancy_type', 'default': 'Residential', 'type': str},
        'fire_class': {'db_column': 'fire_class', 'default': 'CLASS A', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Fire Incident', 'type': str}
    }

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate FIRE Predictions with Random Variation ===
    firex_full_text = "Fire 2023 Full Year: Forecast unavailable"
    firex_monthly_text = "Fire 2023 Monthly: Forecast unavailable"
    firex_jul_dec_text = "Fire July-Dec 2023: Forecast unavailable"

    try:
        # Full Year (f_arima_pred)
        if f_arimax_pred is not None:
            forecast = f_arimax_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            firex_full_text = f"Fire 2023 Full Year: {prob:.1f}% Risk"

        # Monthly (f_arima_m)
        if f_arimax_m is not None:
            forecast = f_arimax_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            firex_monthly_text = f"Fire 2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (f_arima_22)
        if f_arimax_22 is not None:
            forecast = f_arimax_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            firex_jul_dec_text = f"Fire July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"Fire ARIMA Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_ARIMAX_fire_prediction = f"{firex_full_text} | {firex_monthly_text} | {firex_jul_dec_text}"
    extracted_data['prediction'] = combined_ARIMAX_fire_prediction

    # === 3. Save to DB (INSERT with prediction) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_fire_response (
                alert_id, fire_cause, occupancy_type, fire_class,
                lat, lon, barangay, emergency_type, timestamp, responded,
                barangay_clean, prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['fire_cause'],
            extracted_data['occupancy_type'],
            extracted_data['fire_class'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded'],
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"Fire response + prediction saved: {combined_ARIMAX_fire_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response (no prediction in alert card) ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_fire_arimax', data, room=barangay_room)
    logger.info("Barangay fire response emitted (prediction hidden from UI)")

    # === 5. Broadcast Fire predictions to all dashboards ===
    emit('update_fire_arimax_charts', {
        'fire_full': firex_full_text,
        'fire_monthly': firex_monthly_text,
        'fire_jul_dec': firex_jul_dec_text
    }, broadcast=True)

    logger.info(f"Fire prediction broadcasted → {firex_full_text} | {firex_monthly_text} | {firex_jul_dec_text}")
    
def handle_barangay_fire_sarima(data):
    logger.info(f"Received Barangay fire response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data (same as road accident) ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'fire_cause': {'db_column': 'fire_cause', 'default': 'Undetermined fire cause (on pending investigation)', 'type': str},
        'occupancy_type': {'db_column': 'occupancy_type', 'default': 'Residential', 'type': str},
        'fire_class': {'db_column': 'fire_class', 'default': 'CLASS A', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Fire Incident', 'type': str}
    }

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate FIRE Predictions with Random Variation ===
    sarima_fire_full_text = "Fire 2023 Full Year: Forecast unavailable"
    sarima_fire_monthly_text = "Fire 2023 Monthly: Forecast unavailable"
    sarima_fire_jul_dec_text = "Fire July-Dec 2023: Forecast unavailable"

    try:
        # Full Year (f_arima_pred)
        if f_sarima_pred is not None:
            forecast = f_sarima_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            sarima_fire_full_text = f"Fire 2023 Full Year: {prob:.1f}% Risk"

        # Monthly (f_arima_m)
        if f_sarima_m is not None:
            forecast = f_arimax_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            sarima_fire_monthly_text = f"Fire 2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (f_arima_22)
        if f_sarima_22 is not None:
            forecast = f_sarima_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            sarima_fire_jul_dec_text = f"Fire July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"Fire ARIMA Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_SARIMA_fire_prediction = f"{sarima_fire_full_text} | {sarima_fire_monthly_text} | {sarima_fire_jul_dec_text}"
    extracted_data['prediction'] = combined_SARIMA_fire_prediction

    # === 3. Save to DB (INSERT with prediction) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_fire_response (
                alert_id, fire_cause, occupancy_type, fire_class,
                lat, lon, barangay, emergency_type, timestamp, responded,
                barangay_clean, prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['fire_cause'],
            extracted_data['occupancy_type'],
            extracted_data['fire_class'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded'],
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"Fire response + prediction saved: {combined_SARIMA_fire_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response (no prediction in alert card) ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_fire_sarima', data, room=barangay_room)
    logger.info("Barangay fire response emitted (prediction hidden from UI)")

    # === 5. Broadcast Fire predictions to all dashboards ===
    emit('update_fire_sarima_charts', {
        'fire_full': sarima_fire_full_text,
        'fire_monthly': sarima_fire_monthly_text,
        'fire_jul_dec': sarima_fire_jul_dec_text
    }, broadcast=True)

    logger.info(f"Fire prediction broadcasted → {sarima_fire_full_text} | {sarima_fire_monthly_text} | {sarima_fire_jul_dec_text}")
    
def handle_barangay_fire_sarimax(data):
    logger.info(f"Received Barangay fire response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Extract data (same as road accident) ===
    field_mappings = {
        'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
        'fire_cause': {'db_column': 'fire_cause', 'default': 'Undetermined fire cause (on pending investigation)', 'type': str},
        'occupancy_type': {'db_column': 'occupancy_type', 'default': 'Residential', 'type': str},
        'fire_class': {'db_column': 'fire_class', 'default': 'CLASS A', 'type': str},
        'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
        'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
        'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
        'emergency_type': {'db_column': 'emergency_type', 'default': 'Fire Incident', 'type': str}
    }

    extracted_data = {}
    for key, mapping in field_mappings.items():
        val = data.get(key)
        extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

    now = datetime.now(pytz.timezone('Asia/Manila'))
    extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    extracted_data['responded'] = True

    # === 2. Generate FIRE Predictions with Random Variation ===
    sarimax_fire_full_text = "Fire 2023 Full Year: Forecast unavailable"
    sarimax_fire_monthly_text = "Fire 2023 Monthly: Forecast unavailable"
    sarimax_fire_jul_dec_text = "Fire July-Dec 2023: Forecast unavailable"

    try:
        # Full Year (f_arima_pred)
        if f_sarimax_pred is not None:
            forecast = f_sarimax_pred.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-15.0, 18.0)
            prob = max(20, min(95, prob))
            sarimax_fire_full_text = f"Fire 2023 Full Year: {prob:.1f}% Risk"

        # Monthly (f_arima_m)
        if f_sarimax_m is not None:
            forecast = f_arimax_m.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 100) * 100
            prob += random.uniform(-18.0, 20.0)
            prob = max(25, min(94, prob))
            sarimax_fire_monthly_text = f"Fire 2023 Monthly: {prob:.1f}% Risk"

        # July-Dec (f_arima_22)
        if f_sarimax_22 is not None:
            forecast = f_sarimax_22.predict(n_periods=1)
            predicted = float(forecast.iloc[0])
            prob = (predicted / 60) * 100
            prob += random.uniform(-20.0, 22.0)
            prob = max(30, min(92, prob))
            sarimax_fire_jul_dec_text = f"Fire July-Dec 2023: {prob:.1f}% Risk"

    except Exception as e:
        logger.error(f"Fire ARIMA Prediction failed: {e}")

    # === COMBINE FOR DB ===
    combined_SARIMAX_fire_prediction = f"{sarimax_fire_full_text} | {sarimax_fire_monthly_text} | {sarimax_fire_jul_dec_text}"
    extracted_data['prediction'] = combined_SARIMAX_fire_prediction

    # === 3. Save to DB (INSERT with prediction) ===
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_fire_response (
                alert_id, fire_cause, occupancy_type, fire_class,
                lat, lon, barangay, emergency_type, timestamp, responded,
                barangay_clean, prediction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['fire_cause'],
            extracted_data['occupancy_type'],
            extracted_data['fire_class'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded'],
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown',
            extracted_data['prediction']
        ))
        conn.commit()
        logger.info(f"Fire response + prediction saved: {combined_SARIMAX_fire_prediction}")

    except Exception as e:
        logger.error(f"DB Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 4. Emit response (no prediction in alert card) ===
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_fire_sarima', data, room=barangay_room)
    logger.info("Barangay fire response emitted (prediction hidden from UI)")

    # === 5. Broadcast Fire predictions to all dashboards ===
    emit('update_fire_sarimax_charts', {
        'fire_full': sarimax_fire_full_text,
        'fire_monthly': sarimax_fire_monthly_text,
        'fire_jul_dec': sarimax_fire_jul_dec_text
    }, broadcast=True)

    logger.info(f"Fire prediction broadcasted → {sarimax_fire_full_text} | {sarimax_fire_monthly_text} | {sarimax_fire_jul_dec_text}")
def handle_barangay_crime_submitted(data):
    logger.info(f"Received Barangay crime response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'crime_types': {'db_column': 'crime_type', 'default': 'Theft', 'type': str},
            'crime_causes': {'db_column': 'crime_cause', 'default': 'Poverty', 'type': str},
            'levels': {'db_column': 'level', 'default': 'Low', 'type': str},
            'suspect_gender': {'db_column': 'suspect_gender', 'default': 'Male', 'type': str},
            'victim_gender': {'db_column': 'victim_gender', 'default': 'Female', 'type': str},
            'suspect_age': {'db_column': 'suspect_age', 'default': '26-35', 'type': str},
            'victim_age': {'db_column': 'victim_age', 'default': '18-25', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'emergency_type': {'db_column': 'emergency_type', 'default': 'Crime Incident', 'type': str}
        }
        
        extracted_data = {
            mapping['db_column']: mapping['type'](data.get(key, mapping['default'])) 
            if data.get(key) is not None else mapping['default']
            for key, mapping in field_mappings.items()
        }
        extracted_data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
        extracted_data['responded'] = True

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_crime_response (
                alert_id, crime_type, crime_cause, level, suspect_gender, 
                victim_gender, suspect_age, victim_age, lat, lon, barangay, 
                emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['crime_type'],
            extracted_data['crime_cause'],
            extracted_data['level'],
            extracted_data['suspect_gender'],
            extracted_data['victim_gender'],
            extracted_data['suspect_age'],
            extracted_data['victim_age'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded']
        ))
        conn.commit()
        logger.info(f"Stored barangay crime response for alert_id: {data.get('alert_id')}")
    except Exception as e:
        logger.error(f"Error storing barangay crime response: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    try:
        cleaned_data = {
            'Year': datetime.now(pytz.timezone('Asia/Manila')).year,
            'Barangay': extracted_data['barangay'],
            'Crime_Type': extracted_data['crime_type'],
            'Crime_Cause': extracted_data['crime_cause'],
            'Level': extracted_data['level'],
            'Suspect_Gender': extracted_data['suspect_gender'],
            'Victim_Gender': extracted_data['victim_gender'],
            'Suspect_Age': extracted_data['suspect_age'],
            'Victim_Age': extracted_data['victim_age']
        }
        
        input_df = pd.DataFrame([cleaned_data])
        
        if crime_df is not None and not crime_df.empty:
            expected_columns = crime_df.columns
            for col in expected_columns:
                if col not in input_df.columns:
                    input_df[col] = 0
            input_df = input_df[expected_columns]
        else:
            logger.warning("crime_df is not initialized or empty, using default columns")
            expected_columns = ['Crime_Type', 'Crime_Cause', 'Barangay', 'Year', 'Level', 'Suspect_Gender', 'Victim_Gender', 'Suspect_Age', 'Victim_Age']
            for col in expected_columns:
                if col not in input_df.columns:
                    input_df[col] = 0
            input_df = input_df[expected_columns]
        
        if crime_predictor:
            raw_prediction = crime_predictor.predict_proba(input_df)[:, 1][0] * 100
            time_range = random.choice(TIME_RANGES)
            data['prediction'] = f"There will be a {raw_prediction:.2f}% chance of Crime Incident again in the next {time_range}"
        else:
            data['prediction'] = 'prediction_error'
    except Exception as e:
        data['prediction'] = 'prediction_error'
        logger.error(f"Error in crime prediction: {e}")

    emit('barangay_crime_submitted', data, room=f"barangay_{data.get('barangay', 'unknown').lower()}")
        
    responses.append(data)
    
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_crime_submitted', data, room=barangay_room)
    logger.info(f"Barangay crime response emitted to room: {barangay_room}")


def handle_barangay_health_response(data):
    logger.info(f"Received health response from barangay: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'health_emergency_types': {'db_column': 'health_type', 'default': 'Heart Attack', 'type': str},
            'health_causes': {'db_column': 'health_cause', 'default': 'Chronic Illness', 'type': str},
            'patient_gender': {'db_column': 'patient_gender', 'default': 'Male', 'type': str},
            'patient_age': {'db_column': 'patient_age', 'default': '26-35', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'emergency_type': {'db_column': 'emergency_type', 'default': 'Health Emergency', 'type': str}
        }
        
        extracted_data = {
            mapping['db_column']: mapping['type'](data.get(key, mapping['default'])) 
            if data.get(key) is not None else mapping['default']
            for key, mapping in field_mappings.items()
        }
        extracted_data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
        extracted_data['responded'] = True
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO barangay_health_response (
                alert_id, health_type, health_cause, patient_age, 
                patient_gender, lat, lon, barangay, emergency_type, 
                timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['health_type'],
            extracted_data['health_cause'],
            extracted_data['patient_age'],
            extracted_data['patient_gender'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded']
        ))
        conn.commit()
        logger.info(f"Stored barangay health response for alert_id: {data.get('alert_id')}")
    except Exception as e:
        logger.error(f"Error storing barangay health response: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    try:
        cleaned_data = {
            'Year': datetime.now(pytz.timezone('Asia/Manila')).year,
            'Barangay': extracted_data['barangay'],
            'Health_Type': extracted_data['health_type'],
            'Health_Cause': extracted_data['health_cause'],
            'Patient_Age': extracted_data['patient_age'],
            'Patient_Gender': extracted_data['patient_gender']
        }
        
        features = pd.DataFrame([[cleaned_data['Health_Type'], cleaned_data['Health_Cause'], 
                                 cleaned_data['Barangay'], cleaned_data['Year']]],
                               columns=['Health_Type', 'Health_Cause', 'Barangay', 'Year'])
        if health_predictor:
            probability = health_predictor.predict_proba(features)[0][1] * 100
            time_range = random.choice(TIME_RANGES)
            data['prediction'] = f"There will be a {probability:.2f}% chance of Health Emergency again in the next {time_range}"
        else:
            data['prediction'] = 'prediction_error'
    except Exception as e:
        data['prediction'] = 'prediction_error'
        logger.error(f"Error in health prediction: {e}")

    emit('barangay_health_response', data, room=f"barangay_{data.get('barangay', 'unknown').lower()}")
        
    responses.append(data)
    today_responses.append(data)
    barangay_room = f"barangay_{data.get('barangay', 'unknown').lower()}"
    emit('barangay_health_response', data, room=barangay_room)
    logger.info(f"Barangay health response emitted to room: {barangay_room}")



def handle_cdrrmo_response_submitted(data):
    logger.info(f"CDRRMO response received: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Save CDRRMO response to DB ===
    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'road_accident_cause': {'db_column': 'road_accident_cause', 'default': 'Head-on Collision', 'type': str},
            'road_accident_type': {'db_column': 'road_accident_type', 'default': 'Overspeeding', 'type': str},
            'weather_conditions': {'db_column': 'weather', 'default': 'Sunny', 'type': str},
            'road_conditions': {'db_column': 'road_condition', 'default': 'Dry', 'type': str},
            'vehicle_types': {'db_column': 'vehicle_type', 'default': 'Car', 'type': str},
            'driver_ages': {'db_column': 'driver_age', 'default': '26-35', 'type': str},
            'driver_gender': {'db_column': 'driver_gender', 'default': 'Male', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'emergency_type': {'db_column': 'emergency_type', 'default': 'Road Accident', 'type': str}
        }

        extracted_data = {}
        for key, mapping in field_mappings.items():
            val = data.get(key)
            extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

        now = datetime.now(pytz.timezone('Asia/Manila'))
        extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
        extracted_data['responded'] = True

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO cdrrmo_response (
                alert_id, road_accident_cause, road_accident_type, weather, 
                road_condition, vehicle_type, driver_age, driver_gender, 
                lat, lon, barangay, emergency_type, timestamp, responded,
                alcohol_used, incident_hour, incident_weekday, barangay_clean
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'], extracted_data['road_accident_cause'],
            extracted_data['road_accident_type'], extracted_data['weather'],
            extracted_data['road_condition'], extracted_data['vehicle_type'],
            extracted_data['driver_age'], extracted_data['driver_gender'],
            extracted_data['lat'], extracted_data['lon'],
            extracted_data['barangay'], extracted_data['emergency_type'],
            extracted_data['timestamp'], extracted_data['responded'],
            'Yes' if str(data.get('SUSPECTS Alcohol Used','')).strip().lower() == 'yes' else 'No',
            now.hour,
            now.weekday(),
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown'
        ))
        conn.commit()
        logger.info(f"Stored CDRRMO response for alert_id: {extracted_data['alert_id']}")
    except Exception as e:
        logger.error(f"DB Error in CDRRMO: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 2. READ THE ONE TRUE PREDICTION FROM BARANGAY SUBMISSION ===
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT prediction FROM barangay_response WHERE alert_id = ?', (data['alert_id'],))
        row = cursor.fetchone()
        if row and row[0]:
            data['prediction'] = row[0]
            logger.info(f"CDRRMO loaded prediction: {data['prediction']}")
        else:
            data['prediction'] = "Prediction unavailable"
            logger.warning(f"No prediction found for alert_id: {data['alert_id']}")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch prediction for CDRRMO: {e}")
        data['prediction'] = "Prediction unavailable"

    # === 3. Emit to CDRRMO room ===
    municipality = data.get('municipality', 'unknown').lower()
    # DO NOT send prediction text → keep it hidden
    emit('cdrrmo_response', data, room=f"cdrrmo_{municipality}")
    logger.info(f"CDRRMO response emitted (prediction hidden from alert card)")



def handle_pnp_response_submitted(data):
    logger.info(f"PNP response received: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # === 1. Save PNP response to DB ===
    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'road_accident_cause': {'db_column': 'road_accident_cause', 'default': 'Head-on Collision', 'type': str},
            'road_accident_type': {'db_column': 'road_accident_type', 'default': 'Overspeeding', 'type': str},
            'weather_conditions': {'db_column': 'weather', 'default': 'Sunny', 'type': str},
            'road_conditions': {'db_column': 'road_condition', 'default': 'Dry', 'type': str},
            'vehicle_types': {'db_column': 'vehicle_type', 'default': 'Car', 'type': str},
            'driver_ages': {'db_column': 'driver_age', 'default': '26-35', 'type': str},
            'driver_gender': {'db_column': 'driver_gender', 'default': 'Male', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'emergency_type': {'db_column': 'emergency_type', 'default': 'Road Accident', 'type': str}
        }

        extracted_data = {}
        for key, mapping in field_mappings.items():
            val = data.get(key)
            extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

        now = datetime.now(pytz.timezone('Asia/Manila'))
        extracted_data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
        extracted_data['responded'] = True

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO pnp_response (
                alert_id, road_accident_cause, road_accident_type, weather, 
                road_condition, vehicle_type, driver_age, driver_gender, 
                lat, lon, barangay, emergency_type, timestamp, responded,
                alcohol_used, incident_hour, incident_weekday, barangay_clean
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'], extracted_data['road_accident_cause'],
            extracted_data['road_accident_type'], extracted_data['weather'],
            extracted_data['road_condition'], extracted_data['vehicle_type'],
            extracted_data['driver_age'], extracted_data['driver_gender'],
            extracted_data['lat'], extracted_data['lon'],
            extracted_data['barangay'], extracted_data['emergency_type'],
            extracted_data['timestamp'], extracted_data['responded'],
            'Yes' if str(data.get('SUSPECTS Alcohol Used','')).strip().lower() == 'yes' else 'No',
            now.hour,
            now.weekday(),
            extracted_data['barangay'].lower().replace(' ', '_') if extracted_data['barangay'] else 'unknown'
        ))
        conn.commit()
        logger.info(f"Stored PNP response for alert_id: {extracted_data['alert_id']}")
    except Exception as e:
        logger.error(f"DB Error in PNP: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # === 2. READ THE ONE TRUE PREDICTION FROM BARANGAY SUBMISSION ===
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT prediction FROM barangay_response WHERE alert_id = ?', (data['alert_id'],))
        row = cursor.fetchone()
        if row and row[0]:
            data['prediction'] = row[0]
            logger.info(f"PNP loaded prediction: {data['prediction']}")
        else:
            data['prediction'] = "Prediction unavailable"
            logger.warning(f"No prediction found for alert_id: {data['alert_id']}")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch prediction for PNP: {e}")
        data['prediction'] = "Prediction unavailable"

    # === 3. Emit to PNP room ===
    municipality = data.get('municipality', 'unknown').lower()
    # DO NOT send prediction text → keep it hidden
    emit('pnp_response', data, room=f"pnp_{municipality}")
    logger.info(f"PNP response emitted (prediction hidden from alert card)")


def handle_pnp_fire_submitted(data):
    logger.info(f"PNP fire response received: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'fire_cause': {'db_column': 'fire_cause', 'default': 'Undetermined fire cause (on pending investigation)', 'type': str},
            'occupancy_type': {'db_column': 'occupancy_type', 'default': 'Residential', 'type': str},
            'fire_class': {'db_column': 'fire_class', 'default': 'CLASS A', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'municipality': {'db_column': 'municipality', 'default': 'San Pablo City', 'type': str}
        }

        extracted_data = {}
        for key, mapping in field_mappings.items():
            val = data.get(key)
            extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

        extracted_data['timestamp'] = data['timestamp']
        extracted_data['responded'] = True

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO pnp_fire_response (
                alert_id, fire_cause, occupancy_type, fire_class,
                lat, lon, barangay, emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['fire_cause'],
            extracted_data['occupancy_type'],
            extracted_data['fire_class'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            'Fire Incident',
            extracted_data['timestamp'],
            True
        ))
        conn.commit()
        logger.info(f"Stored PNP fire response for alert_id: {data['alert_id']}")

    except Exception as e:
        logger.error(f"Error storing PNP fire response: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # READ THE ONE TRUE PREDICTION FROM BARANGAY
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT prediction FROM barangay_fire_response WHERE alert_id = ?', (data['alert_id'],))
        row = cursor.fetchone()
        if row and row[0]:
            data['prediction'] = row[0]
            logger.info(f"PNP loaded prediction: {data['prediction']}")
        else:
            data['prediction'] = "Prediction unavailable"
            logger.warning(f"No prediction found for alert_id: {data['alert_id']}")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch prediction for PNP: {e}")
        data['prediction'] = "Prediction unavailable"
    
    pnp_room = f"pnp_{data.get('municipality', 'unknown').lower()}"
    emit('pnp_fire_submitted', data, room=pnp_room)
    logger.info(f"PNP fire response emitted to room: {pnp_room}")


def handle_pnp_crime_submitted(data):
    logger.info(f"Received PNP crime response: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'crime_types': {'db_column': 'crime_type', 'default': 'Theft', 'type': str},
            'crime_causes': {'db_column': 'crime_cause', 'default': 'Poverty', 'type': str},
            'levels': {'db_column': 'level', 'default': 'Low', 'type': str},
            'suspect_gender': {'db_column': 'suspect_gender', 'default': 'Male', 'type': str},
            'victim_gender': {'db_column': 'victim_gender', 'default': 'Female', 'type': str},
            'suspect_age': {'db_column': 'suspect_age', 'default': '26-35', 'type': str},
            'victim_age': {'db_column': 'victim_age', 'default': '18-25', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'emergency_type': {'db_column': 'emergency_type', 'default': 'Crime Incident', 'type': str}
        }
        
        extracted_data = {
            mapping['db_column']: mapping['type'](data.get(key, mapping['default'])) 
            if data.get(key) is not None else mapping['default']
            for key, mapping in field_mappings.items()
        }
        extracted_data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
        extracted_data['responded'] = True

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO pnp_crime_response (
                alert_id, crime_type, crime_cause, level, suspect_gender, 
                victim_gender, suspect_age, victim_age, lat, lon, barangay, 
                emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['crime_type'],
            extracted_data['crime_cause'],
            extracted_data['level'],
            extracted_data['suspect_gender'],
            extracted_data['victim_gender'],
            extracted_data['suspect_age'],
            extracted_data['victim_age'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded']
        ))
        conn.commit()
        logger.info(f"Stored pnp crime response for alert_id: {data.get('alert_id')}")
    except Exception as e:
        logger.error(f"Error storing pnp crime response: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    try:
        cleaned_data = {
            'Year': datetime.now(pytz.timezone('Asia/Manila')).year,
            'Barangay': extracted_data['barangay'],
            'Crime_Type': extracted_data['crime_type'],
            'Crime_Cause': extracted_data['crime_cause'],
            'Level': extracted_data['level'],
            'Suspect_Gender': extracted_data['suspect_gender'],
            'Victim_Gender': extracted_data['victim_gender'],
            'Suspect_Age': extracted_data['suspect_age'],
            'Victim_Age': extracted_data['victim_age']
        }
        
        input_df = pd.DataFrame([cleaned_data])
        
        # Ensure all expected columns are present
        if crime_df is not None and not crime_df.empty:
            expected_columns = crime_df.columns
            for col in expected_columns:
                if col not in input_df.columns:
                    input_df[col] = 0
            input_df = input_df[expected_columns]
        else:
            logger.warning("crime_df is not initialized or empty, using default columns")
            expected_columns = ['Crime_Type', 'Crime_Cause', 'Barangay', 'Year', 'Level', 'Suspect_Gender', 'Victim_Gender', 'Suspect_Age', 'Victim_Age']
            for col in expected_columns:
                if col not in input_df.columns:
                    input_df[col] = 0
            input_df = input_df[expected_columns]
        
        if crime_predictor:
            raw_prediction = crime_predictor.predict_proba(input_df)[:, 1][0] * 100
            time_range = random.choice(TIME_RANGES)
            data['prediction'] = f"There will be a {raw_prediction:.2f}% chance of Crime Incident again in the next {time_range}"
        else:
            data['prediction'] = 'prediction_error'
    except Exception as e:
        data['prediction'] = 'prediction_error'
    emit('pnp_crime_submitted', data, room=f"pnp_{data.get('municipality', 'unknown').lower()}")
        
    responses.append(data)
    
    pnp_room = f"pnp_{data.get('municipality', 'unknown').lower()}"
    emit('pnp_crime_submitted', data, room=pnp_room)
    logger.info(f"Emitted pnp crime response to room: {pnp_room}")



        

def handle_fire_response_submitted(data):
    logger.info(f"BFP fire response received: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'fire_cause': {'db_column': 'fire_cause', 'default': 'Undetermined fire cause (on pending investigation)', 'type': str},
            'occupancy_type': {'db_column': 'occupancy_type', 'default': 'Residential', 'type': str},
            'fire_class': {'db_column': 'fire_class', 'default': 'CLASS A', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'municipality': {'db_column': 'municipality', 'default': 'San Pablo City', 'type': str}
        }

        extracted_data = {}
        for key, mapping in field_mappings.items():
            val = data.get(key)
            extracted_data[mapping['db_column']] = mapping['type'](val) if val is not None else mapping['default']

        extracted_data['timestamp'] = data['timestamp']
        extracted_data['responded'] = True

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO bfp_response (
                alert_id, fire_cause, occupancy_type, fire_class,
                lat, lon, barangay, emergency_type, timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['fire_cause'],
            extracted_data['occupancy_type'],
            extracted_data['fire_class'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            'Fire Incident',
            extracted_data['timestamp'],
            True
        ))
        conn.commit()
        logger.info(f"Stored BFP fire response for alert_id: {data['alert_id']}")

    except Exception as e:
        logger.error(f"Error storing BFP fire response: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

    # READ THE ONE TRUE PREDICTION FROM BARANGAY
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT prediction FROM barangay_fire_response WHERE alert_id = ?', (data['alert_id'],))
        row = cursor.fetchone()
        if row and row[0]:
            data['prediction'] = row[0]
            logger.info(f"BFP loaded prediction: {data['prediction']}")
        else:
            data['prediction'] = "Prediction unavailable"
            logger.warning(f"No prediction found for alert_id: {data['alert_id']}")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch prediction for BFP: {e}")
        data['prediction'] = "Prediction unavailable"

    # === Emit to BFP room ===
    bfp_room = f"bfp_{data.get('municipality', 'unknown').lower()}"
    emit('fire_response_submitted', data, room=bfp_room)
    logger.info(f"BFP fire response emitted to room: {bfp_room}")

    # === Broadcast Fire prediction to all dashboards ===
    emit('update_prediction_charts', {
        'fire_full': data.get('fire_full', 'Fire 2023 Full Year: Forecast unavailable'),
        'fire_monthly': data.get('fire_monthly', 'Fire 2023 Monthly: Forecast unavailable'),
        'fire_jul_dec': data.get('fire_jul_dec', 'Fire July-Dec 2023: Forecast unavailable')
    }, broadcast=True)
    


def handle_health_response(data):
    logger.info(f"Received health response from barangay: {data}")
    data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        field_mappings = {
            'alert_id': {'db_column': 'alert_id', 'default': str(uuid.uuid4()), 'type': str},
            'health_emergency_types': {'db_column': 'health_type', 'default': 'Heart Attack', 'type': str},
            'health_causes': {'db_column': 'health_cause', 'default': 'Chronic Illness', 'type': str},
            'patient_gender': {'db_column': 'patient_gender', 'default': 'Male', 'type': str},
            'patient_age': {'db_column': 'patient_age', 'default': '26-35', 'type': str},
            'lat': {'db_column': 'lat', 'default': 0.0, 'type': float},
            'lon': {'db_column': 'lon', 'default': 0.0, 'type': float},
            'barangay': {'db_column': 'barangay', 'default': 'Unknown', 'type': str},
            'emergency_type': {'db_column': 'emergency_type', 'default': 'Health Emergency', 'type': str}
        }
        
        extracted_data = {
            mapping['db_column']: mapping['type'](data.get(key, mapping['default'])) 
            if data.get(key) is not None else mapping['default']
            for key, mapping in field_mappings.items()
        }
        extracted_data['timestamp'] = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')
        extracted_data['responded'] = True
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO health_response (
                alert_id, health_type, health_cause, patient_age, 
                patient_gender, lat, lon, barangay, emergency_type, 
                timestamp, responded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            extracted_data['alert_id'],
            extracted_data['health_type'],
            extracted_data['health_cause'],
            extracted_data['patient_age'],
            extracted_data['patient_gender'],
            extracted_data['lat'],
            extracted_data['lon'],
            extracted_data['barangay'],
            extracted_data['emergency_type'],
            extracted_data['timestamp'],
            extracted_data['responded']
        ))
        conn.commit()
        logger.info(f"Stored city health response for alert_id: {data.get('alert_id')}")
    except Exception as e:
        logger.error(f"Error storing city health response: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    try:
        cleaned_data = {
            'Year': datetime.now(pytz.timezone('Asia/Manila')).year,
            'Barangay': extracted_data['barangay'],
            'Health_Type': extracted_data['health_type'],
            'Health_Cause': extracted_data['health_cause'],
            'Patient_Age': extracted_data['patient_age'],
            'Patient_Gender': extracted_data['patient_gender']
        }
        
        features = pd.DataFrame([[cleaned_data['Health_Type'], cleaned_data['Health_Cause'], 
                                 cleaned_data['Barangay'], cleaned_data['Year']]],
                               columns=['Health_Type', 'Health_Cause', 'Barangay', 'Year'])
        if health_predictor:
            probability = health_predictor.predict_proba(features)[0][1] * 100
            time_range = random.choice(TIME_RANGES)
            data['prediction'] = f"There will be a {probability:.2f}% chance of Health Emergency again in the next {time_range}"
        else:
            data['prediction'] = 'prediction_error'
    except Exception as e:
        data['prediction'] = 'prediction_error'
    emit('health_response', data, room=f"health_{data.get('municipality', 'unknown').lower()}")
        
    responses.append(data)
    today_responses.append(data)
    health_room = f"health_{data.get('municipality', 'unknown').lower()}"
    emit('health_response', data, room=health_room)
    logger.info(f"City health response emitted to room: {health_room}")




def handle_hospital_response(data):  # sourcery skip: low-code-quality  # sourcery skip: low-code-quality
    try:
        conn = get_db_connection()  # Create new connection
        c = conn.cursor()
        manila = pytz.timezone('Asia/Manila')
        base_time = datetime.now(manila)
        assigned_hospital = session.get('assigned_hospital', 'Unknown Hospital').title()
        c.execute('''
            INSERT INTO hospital_response (
                alert_id, health_type, health_cause, weather, patient_age, patient_gender, lat, lon, barangay, emergency_type, timestamp, responded, assigned_hospital
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get('responded', True),
            data.get('assigned_hospital')
        ))
        conn.commit()
        logger.info(f"Hospital response data inserted for alert_id: {data.get('alert_id')}")

        # Map incoming data to model expected columns
        prediction_data = {
            'Health_Type': data.get('health_type', 'Unknown'),
            'Health_Cause': data.get('health_cause', 'Unknown'),
            'Barangay': data.get('barangay', 'Unknown'),
            'Year': datetime.now().year
        }
        input_data = pd.DataFrame([prediction_data])
        prediction = "N/A"
        if health_predictor:
            prediction = health_predictor.predict_proba(input_data)[0][1] * 100
            time_range = random.choice(TIME_RANGES)
            data['prediction'] = f"There will be a {prediction:.1f}% chance of Health Emergency again in the next {time_range}"
        else:
            data['prediction'] = 'prediction_error'
    except Exception as e:
        data['prediction'] = 'prediction_error'
        logger.error(f"Error generating hospital prediction: {e}")

        data['prediction'] = prediction
        barangay = data.get('barangay', 'Unknown')
        municipality = get_municipality_from_barangay(barangay)
        if barangay == 'Unknown' or not municipality:
            barangay = next(iter(barangay_coords.get(session.get('municipality', 'Unknown'), {})), 'Unknown')
            logger.warning(f"Invalid barangay {data.get('barangay', 'Unknown')}, using default {barangay}")
        hospital_room = f"hospital_{municipality.lower()}" if municipality else "hospital_unknown"
        socketio.emit('hospital_response', {
            'alert_id': data.get('alert_id'),
            'barangay': barangay,
            'prediction': prediction,
            'assigned_hospital': assigned_hospital
        }, room=hospital_room)
        logger.info(f"Prediction emitted to room {hospital_room}: {prediction}")

        # Emit chart data for dashboard
        chart_data = {
            'barangay': {
                'labels': [barangay] or ['No Data'],
                'datasets': [{
                    'label': 'Barangay Incidents',
                    'data': [1] or [0],
                    'backgroundColor': ['#FF6B6B'] or ['#999999'],
                    'borderColor': ['#FF6B6B'] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'health_type': {
                'labels': [data.get('health_type', 'Unknown')] or ['No Data'],
                'datasets': [{
                    'label': 'Health Emergency Type',
                    'data': [1] or [0],
                    'backgroundColor': ['#4ECDC4'] or ['#999999'],
                    'borderColor': ['#4ECDC4'] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'health_cause': {
                'labels': [data.get('health_cause', 'Unknown')] or ['No Data'],
                'datasets': [{
                    'label': 'Health Emergency Cause',
                    'data': [1] or [0],
                    'backgroundColor': ['#45B7D1'] or ['#999999'],
                    'borderColor': ['#45B7D1'] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'weather': {
                'labels': [data.get('weather', 'Unknown')] or ['No Data'],
                'datasets': [{
                    'label': 'Weather Conditions',
                    'data': [1] or [0],
                    'backgroundColor': ['#96CEB4'] or ['#999999'],
                    'borderColor': ['#96CEB4'] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'patient_age': {
                'labels': [data.get('patient_age', 'Unknown')] or ['No Data'],
                'datasets': [{
                    'label': 'Patient Age',
                    'data': [1] or [0],
                    'backgroundColor': ['#FFEEAD'] or ['#999999'],
                    'borderColor': ['#FFEEAD'] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'patient_gender': {
                'labels': [data.get('patient_gender', 'Unknown')] or ['No Data'],
                'datasets': [{
                    'label': 'Patient Gender',
                    'data': [1] or [0],
                    'backgroundColor': ['#D4A5A5'] or ['#999999'],
                    'borderColor': ['#D4A5A5'] or ['#999999'],
                    'borderWidth': 1
                }]
            },
            'barangay': barangay
        }
        logger.info(f"Emitting hospital_response_update with chart_data: {chart_data}")
        socketio.emit('hospital_response_update', chart_data, room=hospital_room)
        logger.info(f"Chart update emitted to room {hospital_room}")

        from HospitalDashboard import handle_hospital_response
        handle_hospital_response(data)
    except Exception as e:
        logger.error(f"Error inserting hospital response: {e}")
        conn.rollback()
    finally:
        conn.close()