from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
import os
from datetime import date

app = Flask(__name__)

DATABASE_URL = os.environ.get('postgresql://dbuser:14cIEAPaCvkcxDLjEu1M4FnJsBNE4c3L@dpg-d487c06r433s739tb61g-a/wage_db_ppe4')  # Set Render's Postgres connection string

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Note: SERIAL is PostgreSQL's equivalent for AUTOINCREMENT
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Worker (
            WorkerID SERIAL PRIMARY KEY,
            Name TEXT NOT NULL,
            Age INTEGER,
            Contact TEXT,
            WageRate REAL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Attendance (
            AttendanceID SERIAL PRIMARY KEY,
            WorkerID INTEGER,
            WorkDate DATE,
            HoursWorked REAL,
            FOREIGN KEY (WorkerID) REFERENCES Worker(WorkerID)
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Payment (
            PaymentID SERIAL PRIMARY KEY,
            WorkerID INTEGER,
            PaymentDate DATE,
            AmountPaid REAL,
            ModeOfPayment TEXT,
            FOREIGN KEY (WorkerID) REFERENCES Worker(WorkerID)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Worker;")
    workers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', workers=workers)

@app.route('/addworker', methods=['GET', 'POST'])
def addworker():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        contact = request.form['contact']
        wage = request.form['wage']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Worker (Name, Age, Contact, WageRate) VALUES (%s, %s, %s, %s);",
                    (name, age, contact, wage))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')
    return render_template('add_worker.html')

@app.route('/attendance/<int:workerid>', methods=['GET', 'POST'])
def attendance(workerid):
    today = date.today().isoformat()
    if request.method == 'POST':
        workdate = request.form['date']
        hours = request.form['hours']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Attendance (WorkerID, WorkDate, HoursWorked) VALUES (%s, %s, %s);",
                    (workerid, workdate, hours))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')
    return render_template('attendance.html', workerid=workerid, today=today)

@app.route('/payment/<int:workerid>', methods=['GET', 'POST'])
def payment(workerid):
    today = date.today().isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Worker WHERE WorkerID=%s;", (workerid,))
    worker = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(HoursWorked), 0) FROM Attendance WHERE WorkerID=%s;", (workerid,))
    totalhours = cur.fetchone()[0]
    totalearned = worker[4] * totalhours  # WageRate * HoursWorked
    cur.execute("SELECT COALESCE(SUM(AmountPaid), 0) FROM Payment WHERE WorkerID=%s;", (workerid,))
    totalpaid = cur.fetchone()[0]
    pending = totalearned - totalpaid
    if request.method == 'POST':
        amount = float(request.form['amount'])
        mode = request.form['mode']
        paydate = request.form['date']
        if amount > pending:
            amount = pending if pending > 0 else 0
        cur.execute("INSERT INTO Payment (WorkerID, PaymentDate, AmountPaid, ModeOfPayment) VALUES (%s, %s, %s, %s);",
                    (workerid, paydate, amount, mode))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')
    cur.close()
    conn.close()
    return render_template('payments.html', workerid=workerid, today=today, pending=pending)

@app.route('/report/<int:workerid>')
def report(workerid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT Name, WageRate FROM Worker WHERE WorkerID=%s;", (workerid,))
    worker = cur.fetchone()
    cur.execute("SELECT WorkDate, HoursWorked FROM Attendance WHERE WorkerID=%s;", (workerid,))
    attendance = cur.fetchall()
    cur.execute("SELECT COALESCE(SUM(AmountPaid), 0) FROM Payment WHERE WorkerID=%s;", (workerid,))
    totalpaid = cur.fetchone()[0]
    totalearned = sum(row[1] for row in attendance) * worker[1]
    pending = max(totalearned - totalpaid, 0)
    cur.close()
    conn.close()
    return render_template('report.html', worker=worker, attendance=attendance, totalpaid=totalpaid, pending=pending)

@app.route('/getworkerinfo/<int:workerid>')
def getworkerinfo(workerid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT WageRate FROM Worker WHERE WorkerID=%s;", (workerid,))
    worker = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(HoursWorked), 0) FROM Attendance WHERE WorkerID=%s;", (workerid,))
    totalhours = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify(hourlywage=worker[0] if worker else 0, hoursworked=totalhours)

if __name__ == "__main__":
    app.run(debug=True)
