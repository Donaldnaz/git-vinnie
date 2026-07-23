"""
CloudBoard - A Flask + Redis educational application
=====================================================
This application is designed for students learning Docker and Docker Compose.
It demonstrates how a multi-container application is wired together using
Docker Compose, with Flask as the web layer and Redis as the data store.

Key concepts demonstrated:
  - Connecting to Redis using environment variables for configuration
  - Using Redis commands: INCR, SET, GET, LPUSH, LRANGE, FLUSHALL
  - Reading container hostname (useful for understanding Docker networking)
  - Graceful handling of Redis connection errors
"""

import os
import socket
import datetime
import redis
from flask import Flask, render_template, request, url_for

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
# Flask reads these values from environment variables.  Sensible defaults are
# provided so the app also works when run locally without Docker.

app = Flask(__name__)

# The display name and greeting shown on the home page.
APP_NAME = os.environ.get("APP_NAME", "CloudBoard")
APP_GREETING = os.environ.get("APP_GREETING", "Welcome to the Docker Compose Workshop!")

# Redis connection details.  When running inside Docker Compose, REDIS_HOST
# should be set to "redis" — the service name defined in compose.yaml.
# Docker's internal DNS resolves that name to the Redis container's IP address.
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# ---------------------------------------------------------------------------
# Redis Connection
# ---------------------------------------------------------------------------
# We create a single Redis client.  decode_responses=True makes Redis return
# Python strings instead of bytes, which is easier for beginners to work with.

def get_redis_client():
    """
    Create and return a Redis client.
    Returns the client if successful, or None if the connection fails.
    Having this as a function lets us retry the connection on each request,
    which is useful during classroom demos when Redis might restart.
    """
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,  # Return strings, not bytes
            socket_connect_timeout=2,  # Fail fast if Redis is unreachable
        )
        client.ping()  # Verify the connection is alive
        return client
    except redis.exceptions.ConnectionError:
        return None  # Redis is not available — routes handle this gracefully


# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

def get_hostname():
    """Return the hostname of the container running this Flask app."""
    return socket.gethostname()


def get_current_time():
    """Return the current UTC time as a readable string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """
    Home page — the first thing students see.

    Redis operations used:
      INCR  : Atomically increment the visitor counter by 1.
               INCR is safe even with multiple containers running simultaneously.
      GET   : Read the last visitor timestamp.
      SET   : Store the current timestamp as the last visit.
    """
    r = get_redis_client()
    redis_status = "Connected ✅" if r else "Disconnected ❌"
    visitor_count = 0
    last_visit = "N/A"

    if r:
        # INCR creates the key with value 1 if it doesn't exist yet,
        # then increments it by 1 on every subsequent call.
        visitor_count = r.incr("stats:visitor_count")

        # Record the timestamp of this visit
        current_time = get_current_time()
        r.set("stats:last_visit", current_time)
        last_visit = current_time

    return render_template(
        "home.html",
        app_name=APP_NAME,
        app_greeting=APP_GREETING,
        visitor_count=visitor_count,
        hostname=get_hostname(),
        redis_status=redis_status,
        current_time=get_current_time(),
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Student registration page.

    Redis operations used:
      LPUSH : Push a new student name to the LEFT of a list.
               The list keeps a history of all registered students.
      SET   : Store the name of the most recently registered student.
      INCR  : Increment the student counter.
    """
    r = get_redis_client()
    message = None
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            error = "Please enter a name."
        elif not r:
            error = "Cannot register: Redis is not available."
        else:
            # LPUSH adds the name to the front of the list "students:names"
            r.lpush("students:names", name)

            # Track the most recently registered student
            r.set("stats:last_student", name)

            # Keep a running total of registrations
            r.incr("stats:student_count")

            message = f"✅ '{name}' has been registered successfully!"

    return render_template(
        "register.html",
        app_name=APP_NAME,
        message=message,
        error=error,
        redis_connected=(r is not None),
    )


@app.route("/students")
def students():
    """
    Student list page — shows everyone who has registered.

    Redis operations used:
      LRANGE : Retrieve all elements from the students list.
               LRANGE 0 -1 means "from index 0 to the last element".
    """
    r = get_redis_client()
    student_list = []

    if r:
        # LRANGE key start stop
        # start=0, stop=-1 means return ALL elements in the list
        student_list = r.lrange("students:names", 0, -1)

    return render_template(
        "students.html",
        app_name=APP_NAME,
        students=student_list,
        redis_connected=(r is not None),
    )


@app.route("/stats")
def stats():
    """
    Statistics page — a dashboard showing aggregated data from Redis.

    Redis operations used:
      GET : Read individual string values stored with SET.
    """
    r = get_redis_client()
    data = {
        "visitor_count": "N/A",
        "student_count": "N/A",
        "last_student": "None yet",
        "last_visit": "N/A",
    }

    if r:
        # GET returns None if the key doesn't exist; we use "or" to provide
        # a friendly default value for display.
        data["visitor_count"] = r.get("stats:visitor_count") or "0"
        data["student_count"] = r.get("stats:student_count") or "0"
        data["last_student"] = r.get("stats:last_student") or "None yet"
        data["last_visit"] = r.get("stats:last_visit") or "N/A"

    return render_template(
        "stats.html",
        app_name=APP_NAME,
        data=data,
        redis_connected=(r is not None),
    )


@app.route("/reset", methods=["GET", "POST"])
def reset():
    """
    Reset page — wipes all data from Redis.
    Useful for classroom demos: instructors can reset the board between sessions.

    Redis operations used:
      FLUSHALL : Delete every key in every Redis database.
                 Use with care — this is irreversible!
    """
    r = get_redis_client()
    message = None
    error = None

    if request.method == "POST":
        if not r:
            error = "Cannot reset: Redis is not available."
        else:
            # FLUSHALL removes ALL keys from ALL Redis databases.
            # In a classroom setting this is fine; in production you'd
            # use DEL with specific key patterns instead.
            r.flushall()
            message = "🗑️ All data has been cleared from Redis."

    return render_template(
        "reset.html",
        app_name=APP_NAME,
        message=message,
        error=error,
        redis_connected=(r is not None),
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # FLASK_PORT lets us change the port via an environment variable.
    # Inside Docker this is mapped in compose.yaml; locally it defaults to 5000.
    port = int(os.environ.get("FLASK_PORT", 5000))
    # debug=False in production; set DEBUG=1 env var to enable during development
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
