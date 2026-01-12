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

def get_cdrrmo_stats():
    try:
        types = [a.get('emergency_type', 'unknown') for a in alerts if a.get('role') == 'cdrrmo' or a.get('assigned_municipality')]
        return Counter(types)
    except Exception as e:
        logger.error(f"Error in get_cdrrmo_stats: {e}")
        return Counter()

def get_latest_alert():
    if alerts:
        return list(alerts)[-1]
    return None



def get_the_cdrrmo_stats():
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT COUNT(*) as total 
            FROM cdrrmo_response
        ''')
        total = cursor.fetchone()['total']
        conn.close()
        return type('Stats', (), {'total': lambda self: total})()
    except Exception as e:
        logger.error(f"Error fetching CDRRMO stats: {e}")
        return type('Stats', (), {'total': lambda self: 0})()

def get_cdrrmo_new_alert():
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT alert_id, emergency_type, timestamp 
            FROM cdrrmo_response
            ORDER BY timestamp DESC LIMIT 1
        ''')
        alert = cursor.fetchone()
        conn.close()
        return dict(alert) if alert else None
    except Exception as e:
        logger.error(f"Error fetching latest alert: {e}")
        return None

def get_cdrrmo_alerts_per_month():
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT strftime('%m', datetime(timestamp)) as month, COUNT(*) as count 
            FROM cdrrmo_response 
            WHERE timestamp IS NOT NULL AND datetime(timestamp) IS NOT NULL
            GROUP BY strftime('%m', datetime(timestamp))
        ''')
        month_names = {
            '01': 'January', '02': 'February', '03': 'March', '04': 'April',
            '05': 'May', '06': 'June', '07': 'July', '08': 'August',
            '09': 'September', '10': 'October', '11': 'November', '12': 'December'
        }
        alerts_per_month = {
            'January': 0, 'February': 0, 'March': 0, 'April': 0, 'May': 0, 'June': 0,
            'July': 0, 'August': 0, 'September': 0, 'October': 0, 'November': 0, 'December': 0
        }
        for row in cursor:
            month_num = row['month']
            if month_num in month_names:
                alerts_per_month[month_names[month_num]] = row['count']
        conn.close()
        return alerts_per_month
    except Exception as e:
        logger.error(f"Error fetching alerts per month: {e}")
        return {
            'January': 0, 'February': 0, 'March': 0, 'April': 0, 'May': 0, 'June': 0,
            'July': 0, 'August': 0, 'September': 0, 'October': 0, 'November': 0, 'December': 0
        }

def get_cdrrmo_responded_count():
    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT COUNT(*) as count 
            FROM cdrrmo_response 
            WHERE responded = TRUE
        ''')
        count = cursor.fetchone()['count']
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error fetching responded count: {e}")
        return 0

def emit_cdrrmo_alerts_per_month_update(socketio):
    alerts_per_month = get_cdrrmo_alerts_per_month()
    socketio.emit('update_alerts_per_month', alerts_per_month, room='cdrrmo')

def get_heatmap_data(municipality):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT lat, lon FROM cdrrmo_response WHERE municipality = ?', (municipality,))
    data = cursor.fetchall()
    conn.close()
    return [{'lat': row[0], 'lon': row[1]} for row in data]

