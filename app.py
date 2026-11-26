"""NYAYA VAULT – Secure Legal Evidence & Document Management Platform."""

import os
import uuid
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify,
)
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

from database import get_db, init_db
from security import compute_sha256, encrypt_file, decrypt_file, hash_audit_record

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-fallback-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ENCRYPTED_DIR = os.path.join(os.path.dirname(__file__), "encrypted_files")
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "txt"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ENCRYPTED_DIR, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


def add_audit(username, action, details=""):
    """Insert an audit record chained to the previous hash."""
    db = get_db()
    # Get previous hash
    row = db.execute(
        "SELECT record_hash FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    prev_hash = row["record_hash"] if row else "0" * 64

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    record_hash = hash_audit_record(username, action, details, ts, prev_hash)

    db.execute(
        "INSERT INTO audit_log (username, action, details, record_hash, prev_hash, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (username, action, details, record_hash, prev_hash, ts),
    )
    db.commit()
    db.close()


# ── routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], password):
            session["username"] = user["username"]
            session["role"] = user["role"]
            add_audit(username, "LOGIN", "User logged in")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    user = session.get("username", "unknown")
    add_audit(user, "LOGOUT", "User logged out")
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    total_cases = db.execute("SELECT COUNT(*) as c FROM cases").fetchone()["c"]
    total_docs = db.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]

    if session.get("role") == "admin":
        recent = db.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT 10"
        ).fetchall()
        total_users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    else:
        # Officers see only their own recent activity
        recent = db.execute(
            "SELECT * FROM audit_log WHERE username = ? ORDER BY id DESC LIMIT 10",
            (session["username"],),
        ).fetchall()
        total_users = None
        pending_verifications = None

    # Officer-specific stats
    my_uploads = db.execute(
        "SELECT COUNT(*) as c FROM documents WHERE uploaded_by = ?",
        (session["username"],),
    ).fetchone()["c"]

    db.close()
    return render_template(
        "dashboard.html",
        total_cases=total_cases,
        total_docs=total_docs,
        total_users=total_users,
        my_uploads=my_uploads,
        recent_activities=recent,
    )


# ── cases ────────────────────────────────────────────────────────────────

@app.route("/cases")
@login_required
def cases():
    db = get_db()
    all_cases = db.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template("cases.html", cases=all_cases)


@app.route("/cases/create", methods=["POST"])
@login_required
@admin_required
def create_case():
    case_id = request.form.get("case_id", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not case_id or not title:
        flash("Case ID and title are required.", "error")
        return redirect(url_for("cases"))

    db = get_db()
    existing = db.execute("SELECT id FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if existing:
        flash("Case ID already exists.", "error")
        db.close()
        return redirect(url_for("cases"))

    db.execute(
        "INSERT INTO cases (case_id, title, description, created_by) VALUES (?, ?, ?, ?)",
        (case_id, title, description, session["username"]),
    )
    db.commit()
    db.close()
    add_audit(session["username"], "CREATE_CASE", f"Created case {case_id}")
    flash("Case created successfully.", "success")
    return redirect(url_for("cases"))


@app.route("/cases/<case_id>")
@login_required
def case_details(case_id):
    db = get_db()
    case = db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        flash("Case not found.", "error")
        db.close()
        return redirect(url_for("cases"))
    docs = db.execute(
        "SELECT * FROM documents WHERE case_id = ? ORDER BY uploaded_at DESC",
        (case_id,),
    ).fetchall()
    db.close()
    return render_template("case_details.html", case=case, documents=docs)


# ── documents ────────────────────────────────────────────────────────────

@app.route("/upload", methods=["POST"])
@login_required
def upload_document():
    case_id = request.form.get("case_id", "").strip()
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("case_details", case_id=case_id))

    if not allowed_file(file.filename):
        flash("File type not allowed. Use PDF, JPG, PNG or TXT.", "error")
        return redirect(url_for("case_details", case_id=case_id))

    # Read file into memory
    file_data = file.read()
    if len(file_data) > 16 * 1024 * 1024:
        flash("File too large (max 16 MB).", "error")
        return redirect(url_for("case_details", case_id=case_id))

    # Compute SHA-256 of original file
    sha256 = compute_sha256(file_data)

    # Encrypt
    encrypted_data = encrypt_file(file_data)

    # Store encrypted file with unique name
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}.enc"
    enc_path = os.path.join(ENCRYPTED_DIR, unique_name)
    with open(enc_path, "wb") as f:
        f.write(encrypted_data)

    # DB record
    db = get_db()
    db.execute(
        """INSERT INTO documents
           (filename, original_name, case_id, file_type, file_size, sha256_hash, encrypted_path, uploaded_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (unique_name, file.filename, case_id, ext, len(file_data), sha256, enc_path, session["username"]),
    )
    db.commit()
    db.close()

    add_audit(session["username"], "UPLOAD", f"Uploaded {file.filename} to {case_id}")
    flash("Document uploaded and encrypted.", "success")
    return redirect(url_for("case_details", case_id=case_id))


@app.route("/documents/<int:doc_id>/download")
@login_required
def download_document(doc_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    db.close()
    if not doc:
        flash("Document not found.", "error")
        return redirect(url_for("dashboard"))

    # Decrypt
    with open(doc["encrypted_path"], "rb") as f:
        encrypted_data = f.read()
    decrypted_data = decrypt_file(encrypted_data)

    add_audit(session["username"], "DOWNLOAD", f"Downloaded {doc['original_name']}")

    # Send as temp file
    import io
    return send_file(
        io.BytesIO(decrypted_data),
        download_name=doc["original_name"],
        as_attachment=True,
    )


@app.route("/documents/<int:doc_id>/verify")
@login_required
def verify_document(doc_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    db.close()
    if not doc:
        return jsonify({"status": "error", "message": "Document not found"}), 404

    # Decrypt and re-hash
    with open(doc["encrypted_path"], "rb") as f:
        encrypted_data = f.read()
    decrypted_data = decrypt_file(encrypted_data)
    current_hash = compute_sha256(decrypted_data)

    if current_hash == doc["sha256_hash"]:
        result = "VERIFIED"
        message = "Document integrity confirmed. SHA-256 hashes match."
    else:
        result = "INTEGRITY MISMATCH"
        message = "WARNING: Document has been tampered with!"

    add_audit(
        session["username"],
        "VERIFY",
        f"Verified {doc['original_name']} – {result}",
    )

    return jsonify({
        "status": result,
        "message": message,
        "original_hash": doc["sha256_hash"],
        "current_hash": current_hash,
    })


# ── audit ────────────────────────────────────────────────────────────────

@app.route("/audit")
@login_required
@admin_required
def audit():
    db = get_db()
    logs = db.execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()
    db.close()
    return render_template("audit.html", logs=logs)


@app.route("/audit/verify-chain")
@login_required
@admin_required
def verify_audit_chain():
    """Verify the integrity of the entire audit chain."""
    db = get_db()
    logs = db.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
    db.close()

    if not logs:
        return jsonify({"status": "VERIFIED", "message": "Audit log is empty.", "checked": 0})

    prev_hash = "0" * 64
    for i, log in enumerate(logs):
        expected = hash_audit_record(
            log["username"], log["action"], log["details"] or "",
            log["timestamp"], prev_hash,
        )
        if log["record_hash"] != expected:
            return jsonify({
                "status": "CHAIN BROKEN",
                "message": f"Integrity failure at record #{log['id']}",
                "checked": i,
            })
        if log["prev_hash"] != prev_hash:
            return jsonify({
                "status": "CHAIN BROKEN",
                "message": f"Previous-hash mismatch at record #{log['id']}",
                "checked": i,
            })
        prev_hash = log["record_hash"]

    return jsonify({
        "status": "VERIFIED",
        "message": "All audit records are intact.",
        "checked": len(logs),
    })


# ── run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
