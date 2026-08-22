import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# URL used to fetch ticket details from the Ticket API when needed
TICKET_API_URL = os.environ.get("TICKET_API_URL", "")

# In-memory log of notifications received during this session.
# In a production setup this would be persisted to a database or message queue.
notifications = []


def fetch_ticket(ticket_id):
    """Fetch the latest ticket data from the Ticket API."""
    if not TICKET_API_URL:
        return None
    try:
        resp = requests.get(f"{TICKET_API_URL}/tickets/{ticket_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Could not fetch ticket from Ticket API: {e}")
    return None


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/notify", methods=["POST"])
def receive_notification():
    """
    Called by the Ticket API whenever a ticket is created or its status changes.
    Expects a JSON body: { "event": "...", "ticket": { ... } }
    """
    data = request.get_json()
    if not data or "event" not in data or "ticket" not in data:
        return jsonify({"error": "event and ticket fields are required"}), 400

    event = data["event"]
    ticket = data["ticket"]
    ticket_id = ticket.get("id")

    # Fetch the latest ticket state from the Ticket API to confirm we have
    # up-to-date information (demonstrates inter-service HTTP communication).
    latest = fetch_ticket(ticket_id)
    if latest:
        ticket = latest

    if event == "ticket_created":
        message = (
            f"New ticket #{ticket_id} created: \"{ticket.get('title')}\" "
            f"[priority: {ticket.get('priority')}]"
        )
    elif event == "ticket_status_changed":
        message = (
            f"Ticket #{ticket_id} status changed to \"{ticket.get('status')}\": "
            f"\"{ticket.get('title')}\""
        )
    else:
        message = f"Event '{event}' received for ticket #{ticket_id}"

    entry = {
        "event": event,
        "ticket_id": ticket_id,
        "message": message,
        "ticket": ticket,
    }
    notifications.append(entry)
    print(f"[NOTIFICATION] {message}")

    return jsonify({"status": "received", "message": message}), 200


@app.route("/notifications", methods=["GET"])
def list_notifications():
    """Return all notifications logged in this session, newest first."""
    return jsonify(list(reversed(notifications)))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
