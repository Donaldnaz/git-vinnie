"""
frontend-service  (Backend-for-Frontend)
=========================================
Renders all Jinja2 templates. Replaces direct Redis calls with HTTP
requests to the appropriate backend microservice over Docker internal DNS.

Service URLs are injected via environment variables set in compose.yaml:
  VISITOR_SERVICE_URL  — e.g. http://visitor-service:5000
  STUDENT_SERVICE_URL  — e.g. http://student-service:5000
  STATS_SERVICE_URL    — e.g. http://stats-service:5000
  ADMIN_SERVICE_URL    — e.g. http://admin-service:5000

Graceful degradation: any requests.ConnectionError is caught and the
templates receive redis_connected=False, preserving the existing
warning-alert behaviour without raising a 500.
"""

import os
import socket
import datetime
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_NAME     = os.environ.get("APP_NAME",     "CloudBoard")
APP_GREETING = os.environ.get("APP_GREETING", "Welcome to the Docker Compose Workshop!")

VISITOR_SERVICE_URL = os.environ.get("VISITOR_SERVICE_URL", "http://visitor-service:5000")
STUDENT_SERVICE_URL = os.environ.get("STUDENT_SERVICE_URL", "http://student-service:5000")
STATS_SERVICE_URL   = os.environ.get("STATS_SERVICE_URL",   "http://stats-service:5000")
ADMIN_SERVICE_URL   = os.environ.get("ADMIN_SERVICE_URL",   "http://admin-service:5000")

# Timeout for all outbound service calls (seconds)
SERVICE_TIMEOUT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_hostname():
    """Return the hostname of the container running this frontend."""
    return socket.gethostname()


def get_current_time():
    """Return current UTC time as a readable string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def call_service(method, url, **kwargs):
    """
    Wrapper around requests that catches connection errors.
    Returns (response_json_dict, ok:bool).
    ok=False means the downstream service was unreachable.
    """
    try:
        resp = requests.request(method, url, timeout=SERVICE_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp.json(), True
    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError):
        return {}, False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """
    Home page.
    Calls POST /visit on visitor-service to increment counter + record timestamp.
    """
    data, ok = call_service("POST", f"{VISITOR_SERVICE_URL}/visit")

    visitor_count = data.get("visitor_count", 0) if ok else 0
    redis_status  = "Connected ✅" if ok else "Disconnected ❌"

    return render_template(
        "home.html",
        app_name=APP_NAME,
        app_greeting=APP_GREETING,
        visitor_count=visitor_count,
        hostname=get_hostname(),
        redis_status=redis_status,
        current_time=get_current_time(),
        # Shown in the Redis hint card on the home page
        redis_host=os.environ.get("VISITOR_SERVICE_URL", "visitor-service:5000"),
        redis_port="",
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Student registration page.
    On POST, calls POST /students on student-service.
    """
    message = None
    error   = None
    redis_connected = True  # optimistic; will flip on failure

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            error = "Please enter a name."
        else:
            data, ok = call_service(
                "POST",
                f"{STUDENT_SERVICE_URL}/students",
                json={"name": name},
            )
            if ok:
                message = f"✅ '{name}' has been registered successfully!"
            else:
                redis_connected = False
                error = "Cannot register: student service is currently unavailable."

    return render_template(
        "register.html",
        app_name=APP_NAME,
        message=message,
        error=error,
        redis_connected=redis_connected,
    )


@app.route("/students")
def students():
    """
    Student list page.
    Calls GET /students on student-service.
    """
    data, ok = call_service("GET", f"{STUDENT_SERVICE_URL}/students")
    student_list = data.get("students", []) if ok else []

    return render_template(
        "students.html",
        app_name=APP_NAME,
        students=student_list,
        redis_connected=ok,
    )


@app.route("/stats")
def stats():
    """
    Statistics dashboard.
    Calls GET /stats on stats-service.
    """
    payload, ok = call_service("GET", f"{STATS_SERVICE_URL}/stats")

    stats_data = {
        "visitor_count": payload.get("visitor_count", "N/A"),
        "student_count": payload.get("student_count", "N/A"),
        "last_student":  payload.get("last_student",  "None yet"),
        "last_visit":    payload.get("last_visit",    "N/A"),
    }

    return render_template(
        "stats.html",
        app_name=APP_NAME,
        data=stats_data,
        redis_connected=ok,
    )


@app.route("/reset", methods=["GET", "POST"])
def reset():
    """
    Reset page.
    On POST, calls POST /reset on admin-service.
    """
    message = None
    error   = None
    redis_connected = True

    if request.method == "POST":
        data, ok = call_service("POST", f"{ADMIN_SERVICE_URL}/reset")
        if ok:
            message = "🗑️ All data has been cleared from Redis."
        else:
            redis_connected = False
            error = "Cannot reset: admin service is currently unavailable."

    return render_template(
        "reset.html",
        app_name=APP_NAME,
        message=message,
        error=error,
        redis_connected=redis_connected,
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port  = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
