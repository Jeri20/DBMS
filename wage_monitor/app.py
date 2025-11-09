from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import date

app = Flask(__name__)
DATABASE = 'wage.db'

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Worker (
            WorkerID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Age INTEGER,
            Contact TEXT,
            WageRate REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Attendance (
            AttendanceID INTEGER PRIMARY KEY AUTOINCREMENT,
            WorkerID INTEGER,
            WorkDate TEXT,
            HoursWorked REAL,
            FOREIGN KEY(WorkerID) REFERENCES Worker(WorkerID)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Payment (
            PaymentID INTEGER PRIMARY KEY AUTOINCREMENT,
            WorkerID INTEGER,
            PaymentDate TEXT,
            AmountPaid REAL,
            ModeOfPayment TEXT,
            FOREIGN KEY(WorkerID) REFERENCES Worker(WorkerID)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# DB connection helper
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# Home page
@app.route('/')
def index():
    conn = get_db_connection()
    workers = conn.execute("SELECT * FROM Worker").fetchall()
    conn.close()
    return render_template('index.html', workers=workers)

# Add worker
@app.route('/add_worker', methods=['GET', 'POST'])
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        contact = request.form['contact']
        wage = request.form['wage']
        conn = get_db_connection()
        conn.execute("INSERT INTO Worker (Name, Age, Contact, WageRate) VALUES (?, ?, ?, ?)",
                     (name, age, contact, wage))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('add_worker.html')

# Add attendance
@app.route('/attendance/<int:worker_id>', methods=['GET', 'POST'])
def attendance(worker_id):
    today = date.today().isoformat()  # YYYY-MM-DD format
    if request.method == 'POST':
        work_date = request.form['date']
        hours = request.form['hours']
        conn = get_db_connection()
        conn.execute("INSERT INTO Attendance (WorkerID, WorkDate, HoursWorked) VALUES (?, ?, ?)",
                     (worker_id, work_date, hours))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('attendance.html', worker_id=worker_id, today=today)

# Add payment (with pending check)
@app.route('/payment/<int:worker_id>', methods=['GET', 'POST'])
def payment(worker_id):
    today = date.today().isoformat()
    conn = get_db_connection()

    # Fetch worker wage rate and attendance
    worker = conn.execute("SELECT * FROM Worker WHERE WorkerID=?", (worker_id,)).fetchone()
    total_hours = conn.execute("SELECT COALESCE(SUM(HoursWorked), 0) FROM Attendance WHERE WorkerID=?", (worker_id,)).fetchone()[0]
    total_earned = worker['WageRate'] * total_hours

    # Fetch total payments made so far
    total_paid = conn.execute("SELECT COALESCE(SUM(AmountPaid), 0) FROM Payment WHERE WorkerID=?", (worker_id,)).fetchone()[0]
    pending = total_earned - total_paid

    if request.method == 'POST':
        amount = float(request.form['amount'])
        mode = request.form['mode']
        pay_date = request.form['date']

        # Prevent overpayment
        if amount > pending:
            amount = pending if pending > 0 else 0

        conn.execute("INSERT INTO Payment (WorkerID, PaymentDate, AmountPaid, ModeOfPayment) VALUES (?, ?, ?, ?)",
                     (worker_id, pay_date, amount, mode))
        conn.commit()
        conn.close()
        return redirect('/')

    conn.close()
    return render_template('payments.html', worker_id=worker_id, today=today, pending=pending)

# Wage report
@app.route('/report/<int:worker_id>')
def report(worker_id):
    conn = get_db_connection()
    worker = conn.execute("SELECT Name, WageRate FROM Worker WHERE WorkerID=?", (worker_id,)).fetchone()
    attendance = conn.execute("SELECT WorkDate, HoursWorked FROM Attendance WHERE WorkerID=?", (worker_id,)).fetchall()
    total_paid = conn.execute("SELECT SUM(AmountPaid) FROM Payment WHERE WorkerID=?", (worker_id,)).fetchone()[0] or 0
    total_earned = sum([row['HoursWorked'] * worker['WageRate'] for row in attendance])
    pending = max(total_earned - total_paid, 0)  # prevent negative
    conn.close()
    return render_template('report.html', worker=worker, attendance=attendance,
                           total_paid=total_paid, pending=pending)

# Get worker wage + total hours (API)
@app.route('/get_worker_info/<int:worker_id>')
def get_worker_info(worker_id):
    conn = get_db_connection()
    worker = conn.execute("SELECT WageRate FROM Worker WHERE WorkerID=?", (worker_id,)).fetchone()
    total_hours = conn.execute("SELECT SUM(HoursWorked) FROM Attendance WHERE WorkerID=?", (worker_id,)).fetchone()[0] or 0
    conn.close()
    return jsonify({
        "hourly_wage": worker['WageRate'] if worker else 0,
        "hours_worked": total_hours
    })

if __name__ == '__main__':
    app.run(debug=True)
