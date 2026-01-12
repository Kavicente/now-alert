from alert_data import alerts
from collections import Counter

import logging
import sqlite3
import os

logger = logging.getLogger(__name__)
def get_health_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'health' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_health_stats: {e}")
        return Counter()

def get_latest_alert():
    try:
        if alerts:
            return alerts[-1]
        return None
    except Exception as e:
        logger.error(f"Error in get_latest_alert: {e}")
        return None
    
def get_heatmap_data(municipality):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT lat, lon FROM health_response WHERE municipality = ?', (municipality,))
    data = cursor.fetchall()
    conn.close()
    return [{'lat': row[0], 'lon': row[1]} for row in data]

def handle_health_response(data):
    try:
        logger.info(f"Handling health response for alert_id: {data.get('alert_id')}")
        # This function can be extended to process health-specific response data if needed
    except Exception as e:
        logger.error(f"Error in handle_health_response: {e}")

