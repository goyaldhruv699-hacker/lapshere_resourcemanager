from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-key-for-your-local-project"
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT,
            resource_type TEXT,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            resource_id INTEGER,
            assigned_date TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS virtual_machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            os_type TEXT NOT NULL,
            cpu INTEGER NOT NULL,
            memory_mb INTEGER NOT NULL,
            disk_gb INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Stopped',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


def login_required():
    return bool(session.get("logged_in"))


@app.route("/")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    available = conn.execute(
        "SELECT COUNT(*) FROM resources WHERE lower(status)='available'"
    ).fetchone()[0]
    allocated = conn.execute(
        "SELECT COUNT(*) FROM resources WHERE lower(status)='allocated'"
    ).fetchone()[0]
    recent = conn.execute("""
        SELECT a.assigned_date, u.name AS user_name,
               r.resource_name, r.resource_type
        FROM allocations a
        LEFT JOIN users u ON u.id = a.user_id
        LEFT JOIN resources r ON r.id = a.resource_id
        ORDER BY a.id DESC LIMIT 5
    """).fetchall()
    conn.close()
    return render_template(
        "dashboard.html", total=total, available=available,
        allocated=allocated, recent=recent
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        valid = (
            (username == "admin" and password == "admin123")
            or (username == "staff" and password == "staff123")
        )
        if valid:
            session["logged_in"] = True
            session["user_role"] = username
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")


@app.route("/add-resource", methods=["GET", "POST"])
def add_resource():
    if not login_required():
        return redirect(url_for("login"))
    if session.get("user_role") != "admin":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        rtype = request.form.get("type", "").strip()
        if name and rtype:
            conn = get_db()
            conn.execute(
                "INSERT INTO resources (resource_name, resource_type, status) VALUES (?, ?, ?)",
                (name, rtype, "available")
            )
            conn.commit()
            conn.close()
            return redirect(url_for("view_resources"))
        return render_template("add_resource.html", error="Please fill in both fields.")
    return render_template("add_resource.html")


@app.route("/resources")
def view_resources():
    if not login_required():
        return redirect(url_for("login"))
    search = request.args.get("q", "").strip()
    conn = get_db()
    if search:
        resources = conn.execute(
            """SELECT * FROM resources
               WHERE resource_name LIKE ? OR resource_type LIKE ? OR status LIKE ?
               ORDER BY id DESC""",
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        resources = conn.execute("SELECT * FROM resources ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("view_resources.html", resources=resources, search=search)


@app.route("/assign", methods=["GET", "POST"])
def assign_resource():
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        user_id = request.form.get("user", type=int)
        resource_id = request.form.get("resource", type=int)
        if not user_id or not resource_id:
            users = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
            resources = conn.execute(
                "SELECT * FROM resources WHERE lower(status)='available' ORDER BY resource_name"
            ).fetchall()
            conn.close()
            return render_template(
                "assign_resource.html", users=users, resources=resources,
                error="Please select a person and an available resource."
            )
        resource = conn.execute(
            "SELECT id FROM resources WHERE id=? AND lower(status)='available'",
            (resource_id,)
        ).fetchone()
        if not resource:
            conn.close()
            return redirect(url_for("assign_resource"))
        conn.execute(
            "INSERT INTO allocations (user_id, resource_id, assigned_date) VALUES (?, ?, ?)",
            (user_id, resource_id, str(date.today()))
        )
        conn.execute(
            "UPDATE resources SET status='allocated' WHERE id=?", (resource_id,)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("view_resources"))
    users = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
    resources = conn.execute(
        "SELECT * FROM resources WHERE lower(status)='available' ORDER BY resource_name"
    ).fetchall()
    conn.close()
    return render_template("assign_resource.html", users=users, resources=resources)


@app.route("/hypervisor", methods=["GET", "POST"])
def hypervisor():
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        os_type = request.form.get("os_type", "").strip()
        cpu = request.form.get("cpu", type=int)
        memory_mb = request.form.get("memory_mb", type=int)
        disk_gb = request.form.get("disk_gb", type=int)
        if (not name or len(name) > 60 or not os_type or len(os_type) > 40
                or cpu not in (1, 2, 4, 8) or memory_mb not in (512, 1024, 2048, 4096, 8192)
                or disk_gb not in (10, 20, 40, 80, 160)):
            machines = conn.execute("SELECT * FROM virtual_machines ORDER BY id DESC").fetchall()
            conn.close()
            return render_template("hypervisor.html", machines=machines,
                                   error="Enter a valid name and choose supported VM resources.")
        try:
            conn.execute("""INSERT INTO virtual_machines
                (name, os_type, cpu, memory_mb, disk_gb, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'Stopped', ?)""",
                (name, os_type, cpu, memory_mb, disk_gb, str(date.today())))
            conn.commit()
        except sqlite3.IntegrityError:
            machines = conn.execute("SELECT * FROM virtual_machines ORDER BY id DESC").fetchall()
            conn.close()
            return render_template("hypervisor.html", machines=machines,
                                   error="A virtual machine with that name already exists.")
        conn.close()
        return redirect(url_for("hypervisor"))
    machines = conn.execute("SELECT * FROM virtual_machines ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("hypervisor.html", machines=machines)


@app.route("/hypervisor/<int:vm_id>/<action>", methods=["POST"])
def vm_action(vm_id, action):
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    vm = conn.execute("SELECT status FROM virtual_machines WHERE id=?", (vm_id,)).fetchone()
    if vm:
        if action == "start" and vm["status"] == "Stopped":
            conn.execute("UPDATE virtual_machines SET status='Running' WHERE id=?", (vm_id,))
        elif action == "stop" and vm["status"] == "Running":
            conn.execute("UPDATE virtual_machines SET status='Stopped' WHERE id=?", (vm_id,))
        elif action == "restart" and vm["status"] == "Running":
            conn.execute("UPDATE virtual_machines SET status='Running' WHERE id=?", (vm_id,))
        elif action == "delete" and vm["status"] == "Stopped":
            conn.execute("DELETE FROM virtual_machines WHERE id=?", (vm_id,))
        conn.commit()
    conn.close()
    return redirect(url_for("hypervisor"))


@app.route("/delete-resource/<int:resource_id>", methods=["GET", "POST"])
def delete_resource(resource_id):
    if not login_required():
        return redirect(url_for("login"))
    if session.get("user_role") != "admin":
        return redirect(url_for("dashboard"))
    conn = get_db()
    resource = conn.execute(
        "SELECT status FROM resources WHERE id=?", (resource_id,)
    ).fetchone()
    if resource and str(resource["status"]).lower() != "allocated":
        conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
        conn.commit()
    conn.close()
    return redirect(url_for("view_resources"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/release/<int:resource_id>", methods=["GET", "POST"])
def release_resource(resource_id):
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("UPDATE resources SET status='available' WHERE id=?", (resource_id,))
    conn.execute("DELETE FROM allocations WHERE resource_id=?", (resource_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_resources"))


if __name__ == "__main__":
    app.run(debug=True)
