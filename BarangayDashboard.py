from alert_data import alerts
from collections import Counter
import logging
import sqlite3
import os

logger = logging.getLogger(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_barangay_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'barangay' or a.get('barangay')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_barangay_stats: {e}")
        return Counter()

def get_latest_alert():
    try:
        if alerts:
            return alerts[-1]
        return None
    except Exception as e:
        logger.error(f"Error in get_latest_alert: {e}")
        return None
    
def get_the_stats(barangay):
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT COUNT(*) as total 
            FROM (
                SELECT barangay FROM barangay_response WHERE barangay = ?
                UNION ALL
                SELECT barangay FROM barangay_crime_response WHERE barangay = ?
                UNION ALL
                SELECT barangay FROM barangay_fire_response WHERE barangay = ?
                UNION ALL
                SELECT barangay FROM barangay_health_response WHERE barangay = ?
            ) AS combined
        ''', (barangay, barangay, barangay, barangay))
        total = cursor.fetchone()['total']
        conn.close()
        return type('Stats', (), {'total': lambda self: total})()
    except Exception as e:
        logger.error(f"Error fetching barangay stats for {barangay}: {e}")
        return type('Stats', (), {'total': lambda self: 0})()

def get_new_alert(barangay):
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT * FROM (
                SELECT alert_id, barangay, emergency_type, timestamp 
                FROM barangay_response WHERE barangay = ?
                UNION ALL
                SELECT alert_id, barangay, emergency_type, timestamp 
                FROM barangay_crime_response WHERE barangay = ?
                UNION ALL
                SELECT alert_id, barangay, emergency_type, timestamp 
                FROM barangay_fire_response WHERE barangay = ?
                UNION ALL
                SELECT alert_id, barangay, emergency_type, timestamp 
                FROM barangay_health_response WHERE barangay = ?
            ) AS combined
            ORDER BY timestamp DESC LIMIT 1
        ''', (barangay, barangay, barangay, barangay))
        alert = cursor.fetchone()
        conn.close()
        return dict(alert) if alert else None
    except Exception as e:
        logger.error(f"Error fetching latest alert for {barangay}: {e}")
        return None

def get_barangay_emergency_types(barangay=None):
    if not barangay:
        logger.warning("No barangay provided for emergency types")
        return {'Road Accident': 0, 'Crime Incident': 0, 'Fire Incident': 0, 'Health Emergency': 0}
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT emergency_type, COUNT(*) as count 
            FROM (
                SELECT emergency_type FROM barangay_response WHERE barangay = ?
                UNION ALL
                SELECT emergency_type FROM barangay_crime_response WHERE barangay = ?
                UNION ALL
                SELECT emergency_type FROM barangay_fire_response WHERE barangay = ?
                UNION ALL
                SELECT emergency_type FROM barangay_health_response WHERE barangay = ?
            ) AS combined
            GROUP BY emergency_type
        ''', (barangay, barangay, barangay, barangay))
        emergency_types = {'Road Accident': 0, 'Crime Incident': 0, 'Fire Incident': 0, 'Health Emergency': 0}
        for row in cursor:
            if row['emergency_type'] in emergency_types:
                emergency_types[row['emergency_type']] = row['count']
        conn.close()
        return emergency_types
    except Exception as e:
        logger.error(f"Error fetching emergency types for {barangay}: {e}")
        return {'Road Accident': 0, 'Crime Incident': 0, 'Fire Incident': 0, 'Health Emergency': 0}

def get_barangay_responded_count(barangay):
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT COUNT(*) as count FROM barangay_response WHERE barangay = ?', (barangay,))
        count = cursor.fetchone()['count']
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error fetching responded count for {barangay}: {e}")
        return 0

def emit_emergency_types_update(socketio, barangay):
    if not barangay:
        logger.error("No barangay provided for emitting emergency types update")
        return
    emergency_types = get_barangay_emergency_types(barangay)
    socketio.emit('update_emergency_types', emergency_types, room=barangay)
    
def get_heatmap_data(barangay):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT lat, lon FROM barangay_response WHERE barangay = ?', (barangay,))
    data = cursor.fetchall()
    conn.close()
    return [{'lat': row[0], 'lon': row[1]} for row in data]

