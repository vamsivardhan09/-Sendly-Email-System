from flask import Flask, render_template, request, redirect, url_for, session
import random
import sqlite3
from flask_mail import Mail, Message

# Admin credentials (for now hardcoded)
ADMIN_EMAIL = "admin@sendly.com"
ADMIN_PASSWORD = "vamsi09"

app = Flask(__name__)
app.secret_key = "supersecretkey"
# OTP generation function
def generate_otp():
    return str(random.randint(100000, 999999))
# ======================
# EMAIL CONFIGURATION
# ======================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'sendlyteam@gmail.com'
app.config['MAIL_PASSWORD'] = 'nxlhtxckygyobhye'


mail = Mail(app)
def send_otp_email(receiver_email, otp):
    msg = Message(
        subject="Your Sendly OTP Verification Code",
        sender=app.config['MAIL_USERNAME'],
        recipients=[receiver_email]
    )
    msg.body = f"""
Welcome to Sendly!

Your OTP verification code is: {otp}

Do not share this code with anyone.
"""
    mail.send(msg)

# ======================
# DATABASE SETUP
# ======================
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            username TEXT,
            password TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

print("Database initialized")
init_db()

# ======================
# ROUTES
# ======================

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials"

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE is_active=1")
    users = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", users=users)
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        username = request.form["username"]

        cursor.execute(
            "UPDATE users SET name=?, email=?, username=? WHERE id=?",
            (name, email, username, user_id)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template("edit_user.html", user=user)

@app.route("/admin/delete/<int:user_id>")
def delete_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))




@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Step 1: OTP verification stage
        if "otp_verify" in request.form:
            user_otp = request.form["otp"]

            if user_otp == session.get("registration_otp"):

                name = session.get("reg_name")
                email = session.get("reg_email")
                username = session.get("reg_username")
                password = session.get("reg_password")

                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (name, email, username, password) VALUES (?, ?, ?, ?)",
                    (name, email, username, password)
                )
                conn.commit()
                conn.close()

                # Clear session data
                session.pop("registration_otp", None)
                session.pop("reg_name", None)
                session.pop("reg_email", None)
                session.pop("reg_username", None)
                session.pop("reg_password", None)

                return redirect(url_for("login"))
            else:
                return "Invalid OTP"

        # Step 2: First registration form submission
        else:
            name = request.form["name"]
            email = request.form["email"]
            username = request.form["username"]
            password = request.form["password"]

            otp = generate_otp()

            session["registration_otp"] = otp
            session["reg_name"] = name
            session["reg_email"] = email
            session["reg_username"] = username
            session["reg_password"] = password

            send_otp_email(email, otp)

            return render_template("otp_verify.html")

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        # Step 1: OTP verification stage
        if "login_otp_verify" in request.form:
            user_otp = request.form["otp"]

            if user_otp == session.get("login_otp"):
                session["user"] = session.get("login_user")
                
                session.pop("login_otp", None)
                session.pop("login_user", None)

                return redirect(url_for("dashboard"))
            else:
                return "Invalid OTP"

        # Step 2: Email + password verification
        else:
            email = request.form["email"]
            password = request.form["password"]

            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE email=? AND password=? AND is_active=1",
                (email, password)
            )
            user = cursor.fetchone()
            conn.close()

            if user:
                otp = generate_otp()

                session["login_otp"] = otp
                session["login_user"] = user[1]  # storing name

                send_otp_email(email, otp)

                return render_template("login_otp.html")

            else:
                return "Invalid Email or Password"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return render_template("dashboard.html")
    return redirect(url_for("login"))

@app.route("/compose", methods=["GET", "POST"])
def compose():
    if request.method == "POST":
        recipient = request.form["recipient"]
        subject = request.form["subject"]
        message_body = request.form["message"]

        msg = Message(subject,
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[recipient])
        msg.body = message_body
        mail.send(msg)

        return redirect(url_for("success"))

    return render_template("compose.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
