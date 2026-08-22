import os
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# Read all configuration from environment variables
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

NOTIFICATION_SERVICE_URL = os.environ.get("NOTIFICATION_SERVICE_URL", "")


def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'medium',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def notify(event_type, ticket):
    """Send a notification to the notification service."""
    if not NOTIFICATION_SERVICE_URL:
        return
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notify",
            json={"event": event_type, "ticket": ticket},
            timeout=5,
        )
    except Exception as e:
        # Notifications are best-effort; a failure here should not break the API
        print(f"Could not reach notification service: {e}")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/tickets", methods=["GET"])
def list_tickets():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    tickets = []
    for row in rows:
        t = dict(row)
        t["created_at"] = t["created_at"].isoformat()
        tickets.append(t)
    return jsonify(tickets)


@app.route("/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json()
    if not data or not data.get("title") or not data.get("description"):
        return jsonify({"error": "title and description are required"}), 400

    title = data["title"].strip()
    description = data["description"].strip()
    priority = data.get("priority", "medium").strip()
    status = "open"

    if priority not in ("low", "medium", "high"):
        return jsonify({"error": "priority must be low, medium, or high"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        INSERT INTO tickets (title, description, status, priority)
        VALUES (%s, %s, %s, %s)
        RETURNING *
        """,
        (title, description, status, priority),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    ticket = dict(row)
    ticket["created_at"] = ticket["created_at"].isoformat()

    notify("ticket_created", ticket)

    return jsonify(ticket), 201


@app.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return jsonify({"error": "ticket not found"}), 404

    ticket = dict(row)
    ticket["created_at"] = ticket["created_at"].isoformat()
    return jsonify(ticket)


@app.route("/tickets/<int:ticket_id>", methods=["PATCH"])
def update_ticket(ticket_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "request body is required"}), 400

    allowed_fields = {"title", "description", "status", "priority"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"error": "no valid fields to update"}), 400

    if "status" in updates and updates["status"] not in ("open", "in_progress", "resolved", "closed"):
        return jsonify({"error": "status must be open, in_progress, resolved, or closed"}), 400

    if "priority" in updates and updates["priority"] not in ("low", "medium", "high"):
        return jsonify({"error": "priority must be low, medium, or high"}), 400

    set_clause = ", ".join(f"{field} = %s" for field in updates)
    values = list(updates.values()) + [ticket_id]

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        f"UPDATE tickets SET {set_clause} WHERE id = %s RETURNING *",
        values,
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if row is None:
        return jsonify({"error": "ticket not found"}), 404

    ticket = dict(row)
    ticket["created_at"] = ticket["created_at"].isoformat()

    if "status" in updates:
        notify("ticket_status_changed", ticket)

    return jsonify(ticket)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
