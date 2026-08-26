from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random

app = Flask(__name__)

# Session ke liye secret key
app.secret_key = "rfid-voting-final-demo-2026"

DATABASE = "voting.db"


# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# INITIALIZE DATABASE
# =====================================================

def init_db():

    conn = get_db()
    cursor = conn.cursor()

    # -------------------------------------------------
    # VOTERS TABLE
    # -------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            district TEXT NOT NULL,
            rfid_uid TEXT UNIQUE NOT NULL,
            mobile TEXT,
            voted INTEGER DEFAULT 0
        )
    """)

    # -------------------------------------------------
    # CANDIDATES TABLE
    # -------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            party TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    """)

    # =================================================
    # 5 DEMO VOTERS
    # =================================================

    voters = [
        (
            "VOTER001",
            "Pranav Thorat",
            "Pune",
            "RFID001",
            "9876543210"
        ),
        (
            "VOTER002",
            "Rahul Patil",
            "Mumbai",
            "RFID002",
            "9876543211"
        ),
        (
            "VOTER003",
            "Amit Sharma",
            "Pune",
            "RFID003",
            "9876543212"
        ),
        (
            "VOTER004",
            "Sneha Joshi",
            "Mumbai",
            "RFID004",
            "9876543213"
        ),
        (
            "VOTER005",
            "Rohit Deshmukh",
            "Nashik",
            "RFID005",
            "9876543214"
        )
    ]

    # Insert voters
    for voter in voters:

        cursor.execute("""
            INSERT OR IGNORE INTO voters
            (voter_id, name, district, rfid_uid, mobile)
            VALUES (?, ?, ?, ?, ?)
        """, voter)

    # =================================================
    # 3 DEMO CANDIDATES
    # =================================================

    candidates = [
        ("Candidate A", "Party A"),
        ("Candidate B", "Party B"),
        ("Candidate C", "Party C")
    ]

    # Check whether candidates already exist
    candidate_count = cursor.execute(
        "SELECT COUNT(*) FROM candidates"
    ).fetchone()[0]

    # Insert candidates only once
    if candidate_count == 0:

        for name, party in candidates:

            cursor.execute("""
                INSERT INTO candidates
                (name, party, votes)
                VALUES (?, ?, 0)
            """, (name, party))

    conn.commit()
    conn.close()


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():

    return render_template("index.html")


# =====================================================
# LOGIN / RFID AUTHENTICATION
# =====================================================

@app.route("/login", methods=["POST"])
def login():

    voter_id = request.form.get("voter_id", "").strip()
    rfid_uid = request.form.get("rfid_uid", "").strip()

    # Empty fields check
    if voter_id == "" or rfid_uid == "":

        return render_template(
            "index.html",
            error="Please enter Voter ID and RFID UID!"
        )

    conn = get_db()

    # Check Voter ID + RFID together
    voter = conn.execute("""
        SELECT *
        FROM voters
        WHERE voter_id = ?
        AND rfid_uid = ?
    """, (voter_id, rfid_uid)).fetchone()

    conn.close()

    # Invalid combination
    if voter is None:

        return render_template(
            "index.html",
            error="Invalid Voter ID or RFID UID!"
        )

    # Already voted
    if voter["voted"] == 1:

        return render_template(
            "index.html",
            error="You have already voted!"
        )

    # =================================================
    # GENERATE OTP
    # =================================================

    otp = str(random.randint(100000, 999999))

    # Clear previous session
    session.clear()

    # Store new session
    session["otp"] = otp
    session["voter_id"] = voter["voter_id"]

    # Show OTP in terminal
    print()
    print("======================================")
    print("        RFID VOTING DEMO OTP")
    print("======================================")
    print("Voter ID :", voter["voter_id"])
    print("OTP      :", otp)
    print("======================================")
    print()

    return render_template(
        "index.html",
        otp_generated=True,
        demo_otp=otp
    )


# =====================================================
# OTP VERIFICATION
# =====================================================

@app.route("/verify", methods=["POST"])
def verify():

    entered_otp = request.form.get("otp", "").strip()

    saved_otp = session.get("otp")

    # OTP not found
    if saved_otp is None:

        return render_template(
            "index.html",
            error="OTP expired. Please login again."
        )

    # Wrong OTP
    if entered_otp != saved_otp:

        return render_template(
            "index.html",
            error="Invalid OTP!"
        )

    # OTP correct
    session["authenticated"] = True

    # OTP no longer required
    session.pop("otp", None)

    return redirect(url_for("vote"))


# =====================================================
# VOTING PAGE
# =====================================================

@app.route("/vote")
def vote():

    # Check authentication
    if not session.get("authenticated"):

        return redirect(url_for("home"))

    voter_id = session.get("voter_id")

    if voter_id is None:

        session.clear()

        return redirect(url_for("home"))

    conn = get_db()

    # Get voter
    voter = conn.execute("""
        SELECT *
        FROM voters
        WHERE voter_id = ?
    """, (voter_id,)).fetchone()

    # Get candidates
    candidates = conn.execute("""
        SELECT *
        FROM candidates
        ORDER BY id
    """).fetchall()

    conn.close()

    # Voter doesn't exist
    if voter is None:

        session.clear()

        return redirect(url_for("home"))

    # Check again if already voted
    if voter["voted"] == 1:

        session.clear()

        return render_template(
            "index.html",
            error="You have already voted!"
        )

    return render_template(
        "vote.html",
        candidates=candidates,
        voter=voter
    )


# =====================================================
# SUBMIT VOTE
# =====================================================

@app.route("/submit_vote", methods=["POST"])
def submit_vote():

    # Authentication check
    if not session.get("authenticated"):

        return redirect(url_for("home"))

    voter_id = session.get("voter_id")

    candidate_id = request.form.get("candidate")

    # Missing information
    if voter_id is None or candidate_id is None:

        session.clear()

        return redirect(url_for("home"))

    conn = get_db()

    # -------------------------------------------------
    # GET VOTER
    # -------------------------------------------------

    voter = conn.execute("""
        SELECT *
        FROM voters
        WHERE voter_id = ?
    """, (voter_id,)).fetchone()

    # Voter doesn't exist
    if voter is None:

        conn.close()
        session.clear()

        return render_template(
            "index.html",
            error="Voter not found!"
        )

    # -------------------------------------------------
    # CHECK IF ALREADY VOTED
    # -------------------------------------------------

    if voter["voted"] == 1:

        conn.close()
        session.clear()

        return render_template(
            "index.html",
            error="You have already voted!"
        )

    # -------------------------------------------------
    # CHECK CANDIDATE
    # -------------------------------------------------

    candidate = conn.execute("""
        SELECT *
        FROM candidates
        WHERE id = ?
    """, (candidate_id,)).fetchone()

    if candidate is None:

        conn.close()

        return "Invalid candidate selected!"

    # -------------------------------------------------
    # ADD ONE VOTE
    # -------------------------------------------------

    conn.execute("""
        UPDATE candidates
        SET votes = votes + 1
        WHERE id = ?
    """, (candidate_id,))

    # -------------------------------------------------
    # MARK VOTER AS VOTED
    # -------------------------------------------------

    conn.execute("""
        UPDATE voters
        SET voted = 1
        WHERE voter_id = ?
    """, (voter_id,))

    conn.commit()
    conn.close()

    # Clear session
    session.clear()

    return render_template(
        "success.html"
    )


# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin")
def admin():

    conn = get_db()

    # Get all voters
    voters = conn.execute("""
        SELECT *
        FROM voters
        ORDER BY id
    """).fetchall()

    # Get all candidates
    candidates = conn.execute("""
        SELECT *
        FROM candidates
        ORDER BY id
    """).fetchall()

    # Total votes
    result = conn.execute("""
        SELECT SUM(votes) AS total
        FROM candidates
    """).fetchone()

    total_votes = result["total"]

    if total_votes is None:
        total_votes = 0

    conn.close()

    return render_template(
        "admin.html",
        voters=voters,
        candidates=candidates,
        total_votes=total_votes
    )


# =====================================================
# START SERVER
# =====================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)