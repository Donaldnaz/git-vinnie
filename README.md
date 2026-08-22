# Support Ticket System

This is the application for the Phase 2 Capstone Project at CloudSpace Academy. It is a working support ticket system built with two Python Flask microservices and a PostgreSQL database. Your job as a student is not to build the application, it is already built. Your job is to deploy it to AWS EKS the way a real cloud engineering team would.

Read this README carefully before you start. Understanding how the application works will help you make better deployment decisions.

---

## What the application does

Support teams need a reliable way to track issues raised by users and make sure nothing gets missed. This system lets users submit support tickets, track their progress, and receive notifications whenever something changes.

From the browser, a user can:

- Submit a new ticket with a title, description, and priority level
- View all existing tickets and filter them by status
- Click any ticket to see its details and update its status
- See a notification log that updates whenever a ticket is created or its status changes

---

## How the system is structured

The application is made up of three parts: two backend services and a frontend. Each has its own Dockerfile and can be containerized independently.

```
Browser
  |
  | HTTP
  v
Frontend (Nginx)
  |-- /api/tickets/*      --> Ticket API (Flask, port 5001)
  |-- /api/notifications  --> Notification service (Flask, port 5002)

Ticket API  <-->  PostgreSQL (stores all ticket records)
Ticket API   -->  Notification service  (POST /notify on ticket create or status change)
Notification service  -->  Ticket API  (GET /tickets/:id to fetch latest ticket data)
```

### Ticket API

Handles all ticket operations. It connects to the PostgreSQL database and exposes a REST API for creating, listing, viewing, and updating tickets. When a ticket is created or its status changes, it sends an HTTP POST request to the Notification service to trigger a notification.

### Notification service

Listens for events from the Ticket API. When it receives a notification, it calls back to the Ticket API to fetch the latest ticket data, logs a human-readable message, and stores it in memory. These messages are displayed in the frontend. This back-and-forth HTTP communication between the two services is intentional and demonstrates inter-service communication.

### Frontend

A single HTML page served by Nginx. Nginx also acts as a reverse proxy, forwarding `/api/tickets` requests to the Ticket API and `/api/notifications` requests to the Notification service. The browser only ever talks to one host.

---

## Service communication

The two services talk to each other over HTTP using URLs configured through environment variables:

- `NOTIFICATION_SERVICE_URL` is read by the Ticket API to know where to send notifications
- `TICKET_API_URL` is read by the Notification service to know where to fetch ticket data

Neither URL is hardcoded. This means how the services find each other in your deployment is entirely up to you, and the right answer depends on how you set up your Kubernetes networking.

---

## Technology

| Component            | Technology                  |
|----------------------|-----------------------------|
| Frontend             | HTML, CSS, JavaScript       |
| Frontend server      | Nginx 1.27                  |
| Ticket API           | Python 3.12, Flask 3        |
| Notification service | Python 3.12, Flask 3        |
| Database             | PostgreSQL 16               |
| Local dev            | Docker, Docker Compose      |

---

## Project structure

```
support-ticket-system/
  ticket-api/
    app.py              # Ticket API application code
    requirements.txt
    Dockerfile
  notification-service/
    app.py              # Notification service application code
    requirements.txt
    Dockerfile
  frontend/
    index.html          # Single page UI
    nginx.conf          # Nginx config (static files + reverse proxy)
    Dockerfile
  docker-compose.yml    # For running the full system locally
  .env.example          # Environment variable reference
  README.md
```

---

## Environment variables

All configuration is passed through environment variables. Nothing is hardcoded in the application code. When you deploy to Kubernetes, you will need to supply these values using ConfigMaps and Secrets.

| Variable                   | Used by              | Description                                              |
|----------------------------|----------------------|----------------------------------------------------------|
| `DB_HOST`                  | Ticket API           | Hostname of the PostgreSQL server                        |
| `DB_PORT`                  | Ticket API           | PostgreSQL port (default 5432)                           |
| `DB_NAME`                  | Ticket API           | Database name                                            |
| `DB_USER`                  | Ticket API           | Database username                                        |
| `DB_PASSWORD`              | Ticket API           | Database password                                        |
| `NOTIFICATION_SERVICE_URL` | Ticket API, Frontend | Base URL to reach the Notification service               |
| `TICKET_API_URL`           | Notification service, Frontend | Base URL to reach the Ticket API               |
| `FRONTEND_PORT`            | Docker Compose only  | Host port to expose the frontend on locally              |

The database credentials should be handled as Kubernetes Secrets. The service URLs and non-sensitive config can go in a ConfigMap.

---

## API reference

### Ticket API (port 5001)

| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | /health           | Health check                             |
| GET    | /tickets          | List all tickets, newest first           |
| POST   | /tickets          | Create a new ticket                      |
| GET    | /tickets/:id      | Get a single ticket by ID                |
| PATCH  | /tickets/:id      | Update a ticket (status, priority, etc.) |

### Notification service (port 5002)

| Method | Path            | Description                                          |
|--------|-----------------|------------------------------------------------------|
| GET    | /health         | Health check                                         |
| POST   | /notify         | Receive a notification event from the Ticket API     |
| GET    | /notifications  | List all notifications logged in the current session |

Both `/health` endpoints are useful for Kubernetes liveness and readiness probes.

---

## Running locally with Docker Compose

Before deploying to EKS, it is a good idea to run the application locally to understand how it behaves.

**Prerequisites:** Docker and Docker Compose installed.

1. Copy the example env file and fill in values:

   ```bash
   cp .env.example .env
   ```

   The default values in `.env.example` work as-is for local development.

2. Build and start all services:

   ```bash
   docker-compose up --build
   ```

3. Open `http://localhost:8080` in your browser.

4. To stop:

   ```bash
   docker-compose down
   ```

   To also remove stored data:

   ```bash
   docker-compose down -v
   ```

---

## Your task

Your job is to take this application and deploy it to AWS EKS as a production-style system. The Docker Compose setup above is for local testing only. The real deliverable is your Kubernetes deployment.

Refer to the project brief for the full list of requirements and deliverables.
