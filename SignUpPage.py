from flask import Blueprint, request, redirect, url_for, render_template
from AlertNow import app  # Ensure you import the app instance
import sqlite3
import os
import csv
import os
import json
import logging

signup_bp = Blueprint('signup', __name__)

logger = logging.getLogger(__name__)

# Load barangay.csv once


def get_db_connection():
    db_path = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), 'database', 'users_web.db'))
    if not os.path.exists(db_path):
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path))
        open(db_path, 'a').close()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_connection_to_db():
    if os.getenv('RENDER') == 'true':  # Render sets this environment variable
        db_path = '/database/users_web.db'
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'users_web.db')
    app.logger.debug(f"Database path: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def load_barangays():
    barangays = {"San Pablo City": [], "Tiaong": []}
    lat_lon_map = {}

    csv_path = os.path.join(app.static_folder, 'Barangay.csv')
    
    if not os.path.exists(csv_path):
        logger.error(f"Barangay.csv not found at {csv_path}")
        return barangays, lat_lon_map

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header row (Municipality,Barangay,Latitude,Longitude)

            for row in reader:
                if len(row) >= 4:
                    municipality = row[0].strip()  # Column A
                    barangay = row[1].strip()      # Column B
                    lat = row[2].strip()           # Column C
                    lon = row[3].strip()           # Column D

                    if municipality in barangays:
                        if barangay not in barangays[municipality]:
                            barangays[municipality].append(barangay)
                        lat_lon_map[barangay] = (lat, lon)

        # Sort alphabetically
        barangays["San Pablo City"].sort()
        barangays["Tiaong"].sort()

        logger.info(f"Loaded {sum(len(v) for v in barangays.values())} barangays from CSV")
    except Exception as e:
        logger.error(f"Error loading Barangay.csv: {e}")

    return barangays, lat_lon_map

# Load once at startup — with defaults if fail
try:
    BARANGAYS_DATA, LAT_LON_DATA = load_barangays()
except:
    BARANGAYS_DATA = {"San Pablo City": [], "Tiaong": []}
    LAT_LON_DATA = {}
@signup_bp.route('/signup_barangay', methods=['GET', 'POST'])
def signup_barangay():
    if request.method == 'POST':
        barangay = request.form['barangay']
        assigned_municipality = request.form['municipality']
        province = request.form['province']
        contact_no = request.form['contact_no']
        password = request.form['password']
        username = f"{barangay}_{contact_no}"
        lat = request.form.get('lat', '')
        lon = request.form.get('lon', '')

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO users (barangay, role, contact_no, assigned_municipality, province, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (barangay, 'barangay', contact_no, assigned_municipality, province, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "User already exists", 400
        except Exception as e:
            app.logger.error(f"Signup failed for {barangay}: {e}", exc_info=True)  # Use current_app
            return f"Signup failed: {e}", 500
        finally:
            conn.close()
    return render_template('SignUpPage.html',
                           barangays=BARANGAYS_DATA,
                           lat_lon_map=json.dumps(LAT_LON_DATA))

@signup_bp.route('/signup_na', methods=['GET'])
def signup_na():
    return render_template('SignUpPage.html')
