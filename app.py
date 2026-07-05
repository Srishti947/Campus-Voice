from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.utils import secure_filename
import os
import sqlite3
import random
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
# ---------------- EMAIL CONFIGURATION ----------------
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)


# ---------------- HOME ----------------

@app.route('/')
def home():
    return redirect('/login')


# ---------------- LOGIN PAGE ----------------

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
    "SELECT username, password, is_admin FROM users WHERE email=?",
    (email,)
)

    user = cursor.fetchone()

    conn.close()

    if user is None:
        return "❌ Email not found!"

    username = user[0]
    db_password = user[1]
    is_admin = user[2]

    if not check_password_hash(db_password, password):
        return "❌ Incorrect Password!"

    session['username'] = username
    session['email'] = email
    session['is_admin'] = is_admin

    flash("✅ Login successful!", "success")

    if is_admin == 1:
       return redirect('/admin')
    else:
        return redirect('/dashboard')

# ---------------- REGISTER PAGE ----------------

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')


# ---------------- REGISTER ----------------

@app.route('/register', methods=['POST'])
def register():

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return "❌ Email already registered!"

    conn.close()

    otp = str(random.randint(100000, 999999))
    print("OTP for testing:", otp)

    # Save data temporarily in session
    session['otp'] = otp
    session['otp_time'] = time.time()
    session['username'] = username
    session['email'] = email
    session['password'] = generate_password_hash(password)

    msg = Message(
        "Email Verification OTP",
        recipients=[email]
    )

    msg.body = f"Hello {username},\n\nYour OTP is: {otp}\n\nThank you!"

    mail.send(msg)

    return redirect('/verify-otp')
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():

    if request.method == 'GET':
        return render_template('verify_otp.html')

    entered_otp = request.form['otp']

    # ---------------- OTP EXPIRY CHECK (5 minutes) ----------------
    if time.time() - session.get('otp_time', 0) > 300:
        return render_template("verify_otp.html", error="❌ OTP expired. Please register again.")

    # ---------------- OTP EXISTS + MATCH CHECK ----------------
    if session.get('otp') and entered_otp == session.get('otp'):

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users(username,email,password) VALUES(?,?,?)",
            (
                session['username'],
                session['email'],
                session['password']
            )
        )

        conn.commit()
        conn.close()

        # ---------------- CLEAN SESSION ----------------
        session.clear()

        return redirect('/login')

    return render_template("verify_otp.html", error="❌ Invalid OTP!")
# ---------------- FORGOT PASSWORD ----------------

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == "GET":
        return render_template("forgot_password.html")

    email = request.form['email']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    )

    user = cursor.fetchone()

    conn.close()

    if user is None:
        return "❌ Email not registered."

    otp = str(random.randint(100000, 999999))

    session['reset_otp'] = otp
    session['reset_email'] = email
    session['reset_time'] = time.time()

    msg = Message(
        "Campus Voice Password Reset OTP",
        recipients=[email]
    )

    msg.body = f"Your OTP for password reset is: {otp}"

    mail.send(msg)

    return redirect('/reset_password')
# ---------------- RESET PASSWORD ----------------

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():

    if request.method == "GET":
        return render_template("reset_password.html")

    entered_otp = request.form['otp']
    new_password = request.form['password']

    # OTP Expiry (5 minutes)
    if time.time() - session.get('reset_time', 0) > 300:
        return "❌ OTP has expired."

    # OTP Verification
    if entered_otp != session.get('reset_otp'):
        return "❌ Invalid OTP."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password=? WHERE email=?",
        (
            generate_password_hash(new_password),
            session['reset_email']
        )
    )

    conn.commit()
    conn.close()

    # Clear reset session
    session.pop('reset_otp', None)
    session.pop('reset_email', None)
    session.pop('reset_time', None)

    flash("✅ Password reset successfully! Please log in.", "success")

    return redirect('/login')


# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'dashboard.html',
        username=session['username'],
        email=session['email'],
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )
# ---------------- REPORT AN ISSUE ----------------

@app.route('/report', methods=['GET', 'POST'])
def report():

    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':

        title = request.form['title']
        category = request.form['category']
        location = request.form['location']
        description = request.form['description']
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id FROM complaints
        WHERE LOWER(title)=LOWER(?)
        """, (title,))

        existing = cursor.fetchone()

        if existing:
            conn.close()
            flash("⚠️ A complaint with this title already exists.", "warning")
            return redirect("/report")

        image = request.files['image']

        filename = ""

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor.execute("""
            INSERT INTO complaints
            (title, description, category, location, image, user_email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            description,
            category,
            location,
            filename,
            session['email']
      ))

        conn.commit()
        conn.close()
        flash("✅ Complaint submitted successfully!", "success")

        return redirect('/dashboard')

    return render_template('report.html')
# ---------------- VIEW REPORTED ISSUES ----------------

@app.route('/complaints')
def complaints():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, category, location,
               description, status, support_count, image
        FROM complaints
        ORDER BY id DESC
    """)

    issues = cursor.fetchall()

    supported = []

    for issue in issues:

        cursor.execute("""
            SELECT *
            FROM supports
            WHERE complaint_id = ?
            AND user_email = ?
        """, (issue[0], session['email']))

        supported.append(cursor.fetchone() is not None)

    conn.close()

    return render_template(
        "complaints.html",
        issues=zip(issues, supported)
    )
# ---------------- MY COMPLAINTS ----------------

@app.route('/my_complaints')
def my_complaints():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, category, location,
               description, status, support_count, image, created_at
        FROM complaints
        WHERE user_email = ?
        ORDER BY created_at DESC
    """, (session['email'],))

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "my_complaints.html",
        complaints=complaints
    )
@app.route('/delete_complaint/<int:complaint_id>')
def delete_complaint(complaint_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM complaints
        WHERE id = ?
        AND user_email = ?
        AND status = 'Pending'
    """, (complaint_id, session['email']))

    conn.commit()
    conn.close()

    flash("Complaint deleted successfully.", "success")

    return redirect('/my_complaints')
# ---------------- EDIT COMPLAINT ----------------

@app.route('/edit_complaint/<int:complaint_id>', methods=['GET', 'POST'])
def edit_complaint(complaint_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        title = request.form['title']
        category = request.form['category']
        location = request.form['location']
        description = request.form['description']

        cursor.execute("""
            UPDATE complaints
            SET title=?,
                category=?,
                location=?,
                description=?
            WHERE id=?
            AND user_email=?
            AND status='Pending'
        """, (
            title,
            category,
            location,
            description,
            complaint_id,
            session['email']
        ))

        conn.commit()
        conn.close()

        flash("✅ Complaint updated successfully!", "success")

        return redirect('/my_complaints')

    cursor.execute("""
        SELECT id,title,category,location,description,status
        FROM complaints
        WHERE id=?
        AND user_email=?
    """, (
        complaint_id,
        session['email']
    ))

    complaint = cursor.fetchone()

    conn.close()

    if complaint is None:
        return "Complaint not found."

    return render_template(
        "edit_complaint.html",
        complaint=complaint
    )

# ---------------- PROFILE ----------------

@app.route('/profile')
def profile():

    if 'username' not in session:
        return redirect('/login')

    return render_template(
        'profile.html',
        username=session['username'],
        email=session['email']
    )
# ---------------- ADMIN PANEL ----------------

@app.route('/admin')
def admin():

    if 'username' not in session:
        return redirect('/login')

    if session.get('is_admin') != 1:
        return "❌ Access Denied!"

    search = request.args.get('search', '')
    status = request.args.get('status', 'All')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    query = """
        SELECT id, title, category, location, description, status, created_at, image
        FROM complaints
        WHERE (
            title LIKE ?
            OR category LIKE ?
            OR location LIKE ?
            OR description LIKE ?
        )
    """

    params = [
        f"%{search}%",
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    ]

    if status != "All":
        query += " AND status=?"
        params.append(status)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        complaints=complaints,
        search=search,
        status=status
    )
@app.route('/update_status/<int:complaint_id>', methods=['POST'])
def update_status(complaint_id):

    if 'username' not in session:
        return redirect('/login')

    if session.get('is_admin') != 1:
        return "❌ Access Denied!"

    new_status = request.form['status']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE complaints SET status=? WHERE id=?",
        (new_status, complaint_id)
    )

    conn.commit()
    conn.close()
    flash("✅ Complaint status updated successfully!", "success")

    return redirect('/admin')
@app.route('/support/<int:complaint_id>')
def support(complaint_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Check if this user has already supported this complaint
    cursor.execute("""
        SELECT * FROM supports
        WHERE complaint_id = ? AND user_email = ?
    """, (complaint_id, session['email']))

    already_supported = cursor.fetchone()

    if already_supported:
        conn.close()
        flash("⚠️ You have already supported this complaint.", "warning")
        return redirect('/complaints')

    # Increase support count
    cursor.execute("""
        UPDATE complaints
        SET support_count = support_count + 1
        WHERE id = ?
    """, (complaint_id,))

    # Save the support record
    cursor.execute("""
        INSERT INTO supports (complaint_id, user_email)
        VALUES (?, ?)
    """, (complaint_id, session['email']))

    conn.commit()
    conn.close()

    flash("✅ Thank you for supporting this complaint!", "success")

    return redirect('/complaints')


# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')
if __name__ == "__main__":
    app.run(debug=True)