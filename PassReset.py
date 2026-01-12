# PassReset.py
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os


app = Flask(__name__)

def pass_reset():
    if request.method == 'POST':
        role = request.form.get('role')
        contact_no = request.form.get('contact_no')
        password = request.form.get('password')

        if not all([role, contact_no, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('pass_reset_route'))

        db_path = os.path.join(os.path.dirname(__file__), 'database', 'users_web.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET password = ? 
                WHERE role = ? AND contact_no = ?
            ''', (password, role, contact_no))
            
            if cursor.rowcount == 0:
                flash('No account found.', 'error')
            else:
                flash('Password reset successfully!', 'success')
            
            conn.commit()
            conn.close()
        except Exception as e:
            flash('Database error.', 'error')
            print(f"Error: {e}")

        return redirect(url_for('pass_reset_route'))

    return render_template('PassReset.html')

