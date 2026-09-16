

https://github.com/user-attachments/assets/fb436424-737e-4714-8ee0-aa793ed09d03

# REST API — POC

This project started as a Proof of Concept . The goal was to build a **REST API** for customer-like data and implement features that make **automated, simple data extraction** possible (e.g., filtering by `id` and other query parameters). For privacy reasons, the POC uses **sample (Formula 1) data** and contains **no real customer data**.

## What this POC includes
- **REST API** with clear resources and predictable routes.
- **Filtering** by `id`, `country`, and `location` to streamline data retrieval.
- **Auth & Accounts**: users can **register** and **log in**.
- **Roles**:
  - **Admin**: access to **drivers** data, **CSV upload**, and **approve/decline** new registrations.
  - **User**: access to **circuits** (with filters by `location`, `id`, `country`).
- **Dockerized** runtime for easy local execution.
- **Azure Functions–ready** design (initial plan was to port this logic to Azure Functions).

---

## Exact API Endpoints

> Base URL: `/` (FastAPI). Auth uses **Bearer JWT** (OAuth2 password flow).

### Auth & Accounts
- `POST /register` — Create a new account (goes to pending until approved).
- `POST /token` — Obtain access token (login).  
  _Form fields_: `username`, `password`.  
  _Returns_: `{ "access_token": "...", "token_type": "bearer" }`
- `GET /users/me` — Get current user profile (requires valid token).

### Admin — User Management
- `GET /admin/pending-users` — List users awaiting approval.
- `POST /admin/approve-user/{username}` — Approve a pending user.
- `DELETE /admin/decline-user/{username}` — Decline a pending user.

### Data Upload (CSV) — Admin only
- `POST /upload-circuits-csv/` — Upload/ingest **circuits** CSV (multipart `file`).
- `POST /upload-pilots-csv/` — Upload/ingest **pilots** CSV (multipart `file`).

### Circuits — User & Admin
- `GET /items` — List all circuits.
- `GET /items/{item_id}` — Get circuit by `item_id`.
- `GET /location/{location_name}` — List circuits filtered by **location**.
- `GET /country/{country_name}` — List circuits filtered by **country**.

### Pilots — Admin only
- `GET /pilots` — List all pilots.
- `GET /pilots/search/{pilot_name}` — Search pilots by (substring) **name**.

---

## Quick start

### Run with Docker
```bash
# build & run (adjust names/ports as needed)
docker build -t api-poc .
