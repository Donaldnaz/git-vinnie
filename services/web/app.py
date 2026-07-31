"""
web — Flask UI service
=======================
The only service that renders HTML. Has no direct Redis access.
Calls the three backend JSON API services over HTTP and passes
the response data to Jinja2 templates unchanged.

Routes:
  GET       /           Home page   — calls stats-service
  GET/POST  /register   Register    — calls student-service
  GET       /students   Student list — calls student-service
  GET       /stats      Statistics  — calls stats-service
  GET/POST  /reset      Reset       — calls reset-service
"""

import os
import socket
import datetime
import requests
from requests.exceptions import ConnectionError as ReqConnectionError
from flask import Flask, render_template, request, url_for

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_NAME     = os.environ.get("APP_NAME",     "CloudBoard")
APP_GREETING = os.environ.get("APP_GREETING", "Welcome to the Docker Compose Workshop!")

STUDENT_SERVICE_URL = os.environ.get("STUDENT_SERVICE_URL", "http://student-service:5001")
STATS_SERVICE_URL   = os.environ.get("STATS_SERVICE_URL",   "http://stats-service:5002")
RESET_SERVICE_URL   = os.environ.get("RESET_SERVICE_URL",   "http://reset-service:5003")

# Timeout (seconds) for all inter-service HTTP calls
SERVICE_TIMEOUT = int(os.environ.get("SERVICE_TIMEOUT", 5))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_hostname():
    """Return the hostname of the container running this Flask app."""
    return socket.gethostname()


def get_current_time():
    """Return the current UTC time as a readable string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def call(method, url, **kwargs):
    """
    Make an HTTP request to a backend service.
    Returns the parsed JSON dict on success, or None on any failure
    (connection error, timeout, non-2xx response).
    """
    try:
        resp = method(url, timeout=SERVICE_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except (ReqConnectionError, requests.exceptions.Timeout,
            requests.exceptions.HTTPError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """
    Home page.
    1. POST /stats/visit  — increment visitor counter
    2. GET  /stats        — read current stats for display
    Renders home.html with the same variables as the original monolith.
    """
    # Record visit and get updated visitor count + last_visit
    visit_data = call(requests.post, f"{STATS_SERVICE_URL}/stats/visit") or {}
    # Fall back to a full stats read if visit call failed
    stats_data = call(requests.get, f"{STATS_SERVICE_URL}/stats") or {}

    redis_connected = visit_data.get("redis_connected", stats_data.get("redis_connected", False))
    redis_status    = "Connected ✅" if redis_connected else "Disconnected ❌"
    visitor_count   = visit_data.get("visitor_count", stats_data.get("visitor_count", 0))
    last_visit      = visit_data.get("last_visit", stats_data.get("last_visit", "N/A"))

    return render_template(
        "home.html",
        app_name=APP_NAME,
        app_greeting=APP_GREETING,
        visitor_count=visitor_count,
        hostname=get_hostname(),
        redis_status=redis_status,
        current_time=get_current_time(),
        redis_host=os.environ.get("REDIS_HOST", "redis"),
        redis_port=os.environ.get("REDIS_PORT", "6379"),
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Student registration page.
    On POST: forwards the name to student-service POST /students.
    Renders register.html with the same variables as the original monolith.
    """
    message = None
    error   = None
    redis_connected = True  # optimistic default for GET

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            error = "Please enter a name."
        else:
            result = call(
                requests.post,
                f"{STUDENT_SERVICE_URL}/students",
                json={"name": name},
            )

            if result is None:
                # Service unreachable
                error = "Cannot register: the student service is not available."
                redis_connected = False
            elif result.get("success"):
                message = f"✅ {result['message']}"
            else:
                error = result.get("error", "Registration failed.")
                # student-service returns success:false when Redis is down
                redis_connected = False

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
    Calls student-service GET /students.
    Renders students.html with the same variables as the original monolith.
    """
    result = call(requests.get, f"{STUDENT_SERVICE_URL}/students") or {}

    student_list    = result.get("students", [])
    redis_connected = result.get("redis_connected", False)

    return render_template(
        "students.html",
        app_name=APP_NAME,
        students=student_list,
        redis_connected=redis_connected,
    )


@app.route("/stats")
def stats():
    """
    Statistics dashboard page.
    Calls stats-service GET /stats.
    Renders stats.html with the same variables as the original monolith.
    """
    result = call(requests.get, f"{STATS_SERVICE_URL}/stats") or {}

    data = {
        "visitor_count": result.get("visitor_count", "N/A"),
        "student_count": result.get("student_count", "N/A"),
        "last_student":  result.get("last_student",  "None yet"),
        "last_visit":    result.get("last_visit",    "N/A"),
    }
    redis_connected = result.get("redis_connected", False)

    return render_template(
        "stats.html",
        app_name=APP_NAME,
        data=data,
        redis_connected=redis_connected,
    )


@app.route("/reset", methods=["GET", "POST"])
def reset():
    """
    Reset page.
    On POST: calls reset-service POST /reset.
    Renders reset.html with the same variables as the original monolith.
    """
    message = None
    error   = None
    redis_connected = True  # optimistic default for GET

    if request.method == "POST":
        result = call(requests.post, f"{RESET_SERVICE_URL}/reset")

        if result is None:
            error = "Cannot reset: the reset service is not available."
            redis_connected = False
        elif result.get("success"):
            message = f"🗑️ {result['message']}"
        else:
            error = result.get("error", "Reset failed.")
            redis_connected = False

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
