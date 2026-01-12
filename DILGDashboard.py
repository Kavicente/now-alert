from flask import Flask, render_template, jsonify, session, request, redirect, url_for
import sqlite3
import json
from collections import Counter
import os
import logging
from datetime  import datetime, timedelta

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

def get_db_connection():
    db_path = os.path.join('database', 'users_web.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_barangays():
    with open('barangay.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

@app.route('/dilg_dashboard')
def dilg_dashboard():
    if 'role' not in session or session.get('role') != 'dilg':
        return redirect('/login')
    return render_template('DILGDashboard.html')

def load_barangays():
    # First try the correct path inside the project (where you actually put the file)
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'assets', 'barangay.txt'),           # ← your current location
        os.path.join(app.static_folder, 'assets', 'barangay.txt'),                    # ← Flask static fallback
        os.path.join(app.static_folder, 'barangay.txt'),                              # ← some people put it directly in static
    ]
    
    barangays = []
    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped:
                            barangays.append(stripped)
                logger.info(f"Successfully loaded {len(barangays)} barangays from {path}")
                return barangays
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
            continue

    # Final safety net – if file is completely missing
    logger.error("barangay.txt not found in any expected location!")
    return []

@app.route('/dilg_data')
def dilg_data():
    conn = get_db_connection()
    data = {}

    # Load barangays
    barangay_path = os.path.join(app.static_folder, 'barangay.txt')
    try:
        with open(barangay_path, 'r', encoding='utf-8') as f:
            all_barangays = [line.strip() for line in f if line.strip()]
    except:
        all_barangays = []
    data['all_barangays'] = all_barangays

    # Heatmap
    tables_for_heatmap = ['barangay_response', 'barangay_fire_response', 'barangay_health_response', 'barangay_crime_response',
                          'cdrrmo_response', 'bfp_response', 'health_responses', 'pnp_response', 'pnp_fire_response', 'pnp_crime_response']
    heatmap_points = []
    for table in tables_for_heatmap:
        try:
            rows = conn.execute(f"SELECT lat, lon FROM {table} WHERE lat IS NOT NULL AND lon IS NOT NULL").fetchall()
            heatmap_points.extend([[row['lat'], row['lon'], 1] for row in rows])
        except: continue
    data['heatmap'] = heatmap_points

    # Per barangay counts
    def count_per_barangay(tables_list):
        counts = Counter()
        for table in tables_list:
            try:
                rows = conn.execute(f"SELECT barangay FROM {table} WHERE barangay IS NOT NULL").fetchall()
                counts.update(row['barangay'] for row in rows)
            except: continue
        return {b: counts.get(b, 0) for b in all_barangays}

    data['alerts_per_barangay'] = count_per_barangay(['barangay_response', 'barangay_fire_response', 'barangay_health_response', 'barangay_crime_response'])
    data['cdrrmo_alerts'] = count_per_barangay(['cdrrmo_response'])
    data['bfp_alerts'] = count_per_barangay(['bfp_response'])
    data['health_alerts'] = count_per_barangay(['health_responses'])
    data['pnp_alerts'] = count_per_barangay(['pnp_response', 'pnp_fire_response', 'pnp_crime_response'])

    # Detailed per-barangay charts
    def get_field_stats_for_barangay(tables, field):
        stats_per_barangay = {}
        for table in tables:
            try:
                q = f"SELECT barangay, {field} FROM {table} WHERE {field} IS NOT NULL AND barangay IS NOT NULL"
                rows = conn.execute(q).fetchall()
                for row in rows:
                    b = row['barangay']
                    val = row[field] or "Unknown"
                    if b not in stats_per_barangay:
                        stats_per_barangay[b] = Counter()
                    stats_per_barangay[b][val] += 1
            except: continue
        return {b: dict(counter) for b, counter in stats_per_barangay.items()}

    # Road Accident
    data['road_cause'] = get_field_stats_for_barangay(['barangay_response', 'cdrrmo_response', 'pnp_response'], 'road_accident_cause')
    data['road_type'] = get_field_stats_for_barangay(['barangay_response', 'cdrrmo_response', 'pnp_response'], 'road_accident_type')
    data['vehicle_type'] = get_field_stats_for_barangay(['barangay_response', 'cdrrmo_response', 'pnp_response'], 'vehicle_type')
    data['driver_age'] = get_field_stats_for_barangay(['barangay_response', 'cdrrmo_response', 'pnp_response'], 'driver_age')
    data['driver_gender'] = get_field_stats_for_barangay(['barangay_response', 'cdrrmo_response', 'pnp_response'], 'driver_gender')

    # Fire
    data['fire_cause'] = get_field_stats_for_barangay(['barangay_fire_response', 'bfp_response'], 'fire_cause')
    data['fire_type'] = get_field_stats_for_barangay(['barangay_fire_response', 'bfp_response'], 'fire_type')
    data['fire_weather'] = get_field_stats_for_barangay(['barangay_fire_response', 'bfp_response'], 'weather')
    data['fire_severity'] = get_field_stats_for_barangay(['barangay_fire_response', 'bfp_response'], 'fire_severity')

    # Health
    data['health_type'] = get_field_stats_for_barangay(['barangay_health_response', 'health_responses'], 'health_type')
    data['health_cause'] = get_field_stats_for_barangay(['barangay_health_response', 'health_responses'], 'health_cause')
    data['health_weather'] = get_field_stats_for_barangay(['barangay_health_response', 'health_responses'], 'weather')
    data['patient_age'] = get_field_stats_for_barangay(['barangay_health_response', 'health_responses'], 'patient_age')
    data['patient_gender'] = get_field_stats_for_barangay(['barangay_health_response', 'health_responses'], 'patient_gender')

    # Crime
    data['crime_type'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'crime_type')
    data['crime_cause'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'crime_cause')
    data['crime_level'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'level')
    data['suspect_gender'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'suspect_gender')
    data['victim_gender'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'victim_gender')
    data['suspect_age'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'suspect_age')
    data['victim_age'] = get_field_stats_for_barangay(['barangay_crime_response', 'pnp_crime_response'], 'victim_age')

    conn.close()
    return jsonify(data)

@app.route('/dilg_accounts')
def dilg_accounts():
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                role,
                COALESCE(barangay, '') as barangay,
                COALESCE(assigned_municipality, 'Citywide') as assigned_municipality,
                COALESCE(assigned_hospital, '') as assigned_hospital,
                contact_no,
                password
            FROM users 
            WHERE role IN ('barangay', 'cdrrmo', 'pnp', 'bfp', 'health', 'hospital')
            ORDER BY 
                CASE role WHEN 'barangay' THEN 1 WHEN 'cdrrmo' THEN 2 WHEN 'pnp' THEN 3 
                          WHEN 'bfp' THEN 4 WHEN 'health' THEN 5 WHEN 'hospital' THEN 6 ELSE 99 END,
                barangay, assigned_municipality, contact_no
        """
        users = conn.execute(query).fetchall()
        result = []
        for row in users:
            u = dict(row)
            if u['role'] == 'barangay':
                u['display_name'] = u['barangay'] or 'Unknown Barangay'
                u['location'] = u['assigned_municipality']
            elif u['role'] == 'hospital':
                u['display_name'] = u['assigned_hospital'] or 'Unnamed Hospital'
                u['location'] = u['assigned_municipality']
            else:
                names = {'cdrrmo':'CDRRMO', 'pnp':'PNP', 'bfp':'BFP', 'health':'City Health'}
                u['display_name'] = names.get(u['role'], u['role'].upper())
                u['location'] = u['assigned_municipality']
            result.append(u)
        conn.close()
        return jsonify(result)
    except Exception as e:
        print("Error:", e)
        conn.close()
        return jsonify([])


@app.route('/dilg_update_account', methods=['POST'])
def dilg_update_account():
    data = request.json
    conn = get_db_connection()
    try:
        query = "UPDATE users SET contact_no = ?"
        params = [data['contact']]
        if data['password']:
            query += ", password = ?"
            params.append(data['password'])
        query += " WHERE contact_no = ?"
        params.append(data['old_contact'])
        
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/dilg_delete_account/<contact>', methods=['DELETE'])
def dilg_delete_account(contact):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM users WHERE contact_no = ?', (contact,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

@app.route('/dilg_delete_all/<role_type>', methods=['DELETE'])
def dilg_delete_all(role_type):
    conn = get_db_connection()
    try:
        if role_type == 'barangay':
            conn.execute("DELETE FROM users WHERE role = 'barangay'")
        else:
            conn.execute("DELETE FROM users WHERE role IN ('cdrrmo','pnp','bfp','health','hospital')")
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

@app.route('/dilg_warn_account', methods=['POST'])
def dilg_warn_account():
    data = request.json
    contact = data['contact']
    level = data['level']
    # In real app: store warning level in DB
    return jsonify({'success': True, 'level': level})

@app.route('/dilg_barangays')
def dilg_barangays():
    conn = get_db_connection()
    cursor = conn.execute("SELECT DISTINCT barangay FROM barangay_response WHERE barangay IS NOT NULL")
    barangays = [row['barangay'] for row in cursor.fetchall()]
    conn.close()
    return jsonify({'barangays': barangays})

@app.route('/dilg_barangay_report')
def dilg_barangay_report():
    barangay = request.args.get('barangay', '')
    period = request.args.get('period', 'all')

    conn = get_db_connection()
    where = "WHERE 1=1"
    if barangay:
        where += f" AND barangay = '{barangay}'"

    if period != 'all':
        now = datetime.now()
        if period == 'today':
            date_str = now.strftime('%Y-%m-%d')
            where += f" AND substr(timestamp, 1, 10) = '{date_str}'"
        elif period == 'daily':
            where += f" AND date(timestamp) = date('now')"
        elif period == 'weekly':
            where += f" AND date(timestamp) >= date('now', '-7 days')"
        elif period == 'monthly':
            where += f" AND date(timestamp) >= date('now', '-30 days')"
        elif period == 'yearly':
            where += f" AND date(timestamp) >= date('now', '-365 days')"

    tables = [
        'barangay_response', 'barangay_fire_response',
        'barangay_health_response', 'barangay_crime_response'
    ]

    result = {}
    for table in tables:
        query = f"SELECT * FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        stats = {}
        columns = {
            'barangay_response': ['road_accident_cause', 'road_accident_type', 'vehicle_type', 'driver_age', 'driver_gender'],
            'barangay_fire_response': ['fire_cause', 'fire_type', 'weather', 'fire_severity'],
            'barangay_health_response': ['health_type', 'health_cause', 'weather', 'patient_age', 'patient_gender'],
            'barangay_crime_response': ['crime_type', 'crime_cause', 'level', 'suspect_gender', 'victim_gender', 'suspect_age', 'victim_age']
        }
        for col in columns.get(table, []):
            count = {}
            for row in rows:
                val = row[col]
                if val and val.strip():
                    count[val] = count.get(val, 0) + 1
            if count:
                stats[col.replace('_', ' ')] = count
        if stats:
            result[table] = {k.replace(' ', '_'): v for k, v in stats.items()}

    conn.close()
    return jsonify(result)

@app.route('/dilg_cdrrmo_report')
def dilg_cdrrmo_report():
    barangay = request.args.get('barangay', '')
    period = request.args.get('period', 'all')

    conn = get_db_connection()
    where = "WHERE 1=1"
    if barangay:
        where += f" AND barangay = '{barangay}'"

    if period != 'all':
        now = datetime.now()
        if period == 'today':
            where += f" AND substr(timestamp, 1, 10) = date('now')"
        elif period == 'daily':
            where += f" AND date(timestamp) = date('now')"
        elif period == 'weekly':
            where += f" AND date(timestamp) >= date('now', '-7 days')"
        elif period == 'monthly':
            where += f" AND date(timestamp) >= date('now', '-30 days')"
        elif period == 'yearly':
            where += f" AND date(timestamp) >= date('now', '-365 days')"

    tables = ['barangay_response', 'cdrrmo_response', 'pnp_response']
    result = {}

    for table in tables:
        query = f"SELECT road_accident_cause, road_accident_type, vehicle_type, driver_age, driver_gender FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        for row in rows:
            for key in ['road_accident_cause', 'road_accident_type', 'vehicle_type', 'driver_age', 'driver_gender']:
                val = row[key]
                if val and val.strip():
                    result[key] = result.get(key, {})
                    result[key][val] = result[key].get(val, 0) + 1

    conn.close()
    return jsonify(result)

@app.route('/dilg_bfp_report')
def dilg_bfp_report():
    barangay = request.args.get('barangay', '')
    period = request.args.get('period', 'all')

    conn = get_db_connection()
    where = "WHERE 1=1"
    if barangay:
        where += f" AND barangay = '{barangay}'"

    if period != 'all':
        now = datetime.now()
        if period == 'today':
            where += " AND substr(timestamp, 1, 10) = date('now')"
        elif period == 'daily':
            where += " AND date(timestamp) = date('now')"
        elif period == 'weekly':
            where += " AND date(timestamp) >= date('now', '-7 days')"
        elif period == 'monthly':
            where += " AND date(timestamp) >= date('now', '-30 days')"
        elif period == 'yearly':
            where += " AND date(timestamp) >= date('now', '-365 days')"

    tables = ['barangay_fire_response', 'bfp_response', 'pnp_fire_response']
    result = {}

    for table in tables:
        query = f"SELECT fire_cause, fire_type, weather, fire_severity FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        for row in rows:
            for key in ['fire_cause', 'fire_type', 'weather', 'fire_severity']:
                val = row[key]
                if val and val.strip():
                    result[key] = result.get(key, {})
                    result[key][val] = result[key].get(val, 0) + 1

    conn.close()
    return jsonify(result)

@app.route('/dilg_health_report')
def dilg_health_report():
    barangay = request.args.get('barangay', '')
    period = request.args.get('period', 'all')

    conn = get_db_connection()
    where = "WHERE 1=1"
    if barangay:
        where += f" AND barangay = '{barangay}'"

    if period != 'all':
        now = datetime.now()
        if period == 'today':
            where += " AND substr(timestamp, 1, 10) = date('now')"
        elif period == 'daily':
            where += " AND date(timestamp) = date('now')"
        elif period == 'weekly':
            where += " AND date(timestamp) >= date('now', '-7 days')"
        elif period == 'monthly':
            where += " AND date(timestamp) >= date('now', '-30 days')"
        elif period == 'yearly':
            where += " AND date(timestamp) >= date('now', '-365 days')"

    tables = ['barangay_health_response', 'health_response']
    result = {}

    for table in tables:
        query = f"SELECT health_type, health_cause, weather, patient_age, patient_gender FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        for row in rows:
            for key in ['health_type', 'health_cause', 'weather', 'patient_age', 'patient_gender']:
                val = row[key]
                if val and val.strip():
                    result[key] = result.get(key, {})
                    result[key][val] = result[key].get(val, 0) + 1

    conn.close()
    return jsonify(result)

@app.route('/dilg_pnp_report')
def dilg_pnp_report():
    barangay = request.args.get('barangay', '')
    period = request.args.get('period', 'all')

    conn = get_db_connection()
    where = "WHERE 1=1"
    if barangay:
        where += f" AND barangay = '{barangay}'"

    if period != 'all':
        now = datetime.now()
        if period == 'today':
            where += " AND substr(timestamp, 1, 10) = date('now')"
        elif period == 'daily':
            where += " AND date(timestamp) = date('now')"
        elif period == 'weekly':
            where += " AND date(timestamp) >= date('now', '-7 days')"
        elif period == 'monthly':
            where += " AND date(timestamp) >= date('now', '-30 days')"
        elif period == 'yearly':
            where += " AND date(timestamp) >= date('now', '-365 days')"

    result = {}

    # Road Accidents: barangay_response, pnp_response, cdrrmo_response
    tables_road = ['barangay_response', 'pnp_response', 'cdrrmo_response']
    for table in tables_road:
        query = f"SELECT road_accident_cause, road_accident_type, vehicle_type, driver_age, driver_gender FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        for row in rows:
            for key in ['road_accident_cause', 'road_accident_type', 'vehicle_type', 'driver_age', 'driver_gender']:
                val = row[key]
                if val and val.strip():
                    result[key] = result.get(key, {})
                    result[key][val] = result[key].get(val, 0) + 1

    # Fire Incidents: barangay_fire_response, bfp_response, pnp_fire_response
    tables_fire = ['barangay_fire_response', 'bfp_response', 'pnp_fire_response']
    for table in tables_fire:
        query = f"SELECT fire_cause, fire_type, weather, fire_severity FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        for row in rows:
            for key in ['fire_cause', 'fire_type', 'weather', 'fire_severity']:
                val = row[key]
                if val and val.strip():
                    result[key] = result.get(key, {})
                    result[key][val] = result[key].get(val, 0) + 1

    # Crime Incidents: barangay_crime_response, pnp_crime_response
    tables_crime = ['barangay_crime_response', 'pnp_crime_response']
    for table in tables_crime:
        query = f"SELECT crime_type, crime_cause, level, suspect_gender, victim_gender, suspect_age, victim_age FROM {table} {where}"
        rows = conn.execute(query).fetchall()
        for row in rows:
            for key in ['crime_type', 'crime_cause', 'level', 'suspect_gender', 'victim_gender', 'suspect_age', 'victim_age']:
                val = row[key]
                if val and val.strip():
                    result[key] = result.get(key, {})
                    result[key][val] = result[key].get(val, 0) + 1

    conn.close()
    return jsonify(result)