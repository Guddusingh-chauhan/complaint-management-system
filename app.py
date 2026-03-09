from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from datetime import datetime

# -------------------------
# Add Date Column (If Not Exists)
# -------------------------
conn = sqlite3.connect("complaints.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE complaints ADD COLUMN date TEXT")
except:
    pass

conn.commit()
conn.close()

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import TableStyle
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "mysecretkey"

# -------------------------
# Database Initialization
# -------------------------
def init_db():
    conn = sqlite3.connect("complaints.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            department TEXT,
            message TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------
# Home Page
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------------
# Submit Complaint
# -------------------------
@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"]
    email = request.form["email"]
    department = request.form["department"]
    message = request.form["message"]

    date = datetime.now().strftime("%d-%m-%Y %H:%M")

    conn = sqlite3.connect("complaints.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO complaints (name,email,department,message,status,date) VALUES (?,?,?,?,?,?)",
        (name, email, department, message, "Pending", date)
    )

    conn.commit()
    conn.close()

    return redirect("/login")

# -------------------------
# Admin Login
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username.strip() == "admin" and password.strip() == "1234":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Invalid Credentials"

    return render_template("login.html")

# -------------------------
# Admin Panel (Pagination + Search + Filter)
# -------------------------
@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/login")

    search = request.args.get("search")
    status_filter = request.args.get("status")

    page = request.args.get("page", 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page

    conn = sqlite3.connect("complaints.db")
    cursor = conn.cursor()

    query = "SELECT * FROM complaints WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ?)"
        params.append('%' + search + '%')
        params.append('%' + search + '%')

    if status_filter and status_filter != "All":
        query += " AND status=?"
        params.append(status_filter)

    query += " LIMIT ? OFFSET ?"
    params.append(per_page)
    params.append(offset)

    cursor.execute(query, params)
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    total_pages = (total + per_page - 1) // per_page

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        complaints=data,
        total=total,
        pending=pending,
        resolved=resolved,
        total_pages=total_pages
    )

# -------------------------
# Delete Complaint
# -------------------------
@app.route("/delete/<int:id>")
def delete(id):
    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("complaints.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM complaints WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# -------------------------
# Mark Complaint Resolved
# -------------------------
@app.route("/resolve/<int:id>")
def resolve(id):
    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("complaints.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET status='Resolved' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# -------------------------
# Export PDF
# -------------------------
@app.route("/export_pdf")
def export_pdf():
    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("complaints.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints")
    data = cursor.fetchall()
    conn.close()

    file_path = "complaints_report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Complaint Report", styles["Title"]))
    elements.append(Spacer(1, 20))

    table_data = [["ID","Name","Email","Department","Message","Status","Date"]]

    for row in data:
        table_data.append(list(row))

    table = Table(table_data)

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)

# -------------------------
# Logout
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)