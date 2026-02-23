# 🚖 LaaRide Backend

LaaRide is a digital taxi stand platform built for Ladakh, designed to modernize the traditional stand-based taxi booking system.
This backend powers shared seat bookings, driver trip listings, and scalable transport management using FastAPI and MongoDB.

---

## 🧠 Project Vision

Instead of real-time ride-hailing (like Uber), LaaRide digitizes the existing taxi stand model in Ladakh:

* Drivers list upcoming trips (e.g., Kargil → Leh)
* Passengers book available seats
* Fixed-route shared travel is prioritized
* Custom/private bookings are also supported

---

## ⚙️ Tech Stack

* **Framework:** FastAPI (Async)
* **Database:** MongoDB
* **Driver:** Motor (Async MongoDB driver)
* **Server:** Uvicorn
* **Dependency Manager:** uv
* **Architecture:** Modular + Versioned API

---

## 📁 Project Structure

```
laaride-server/
│
├── run.py
│
└── app/
    ├── main.py
    │
    ├── core/
    │   ├── config.py
    │   └── database.py
    │
    ├── models/
    ├── schemas/
    ├── services/
    │
    └── routes/
        └── v1/
            ├── __init__.py
            └── default.py
```

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/laaride-server.git
cd laaride-server
```

### 2️⃣ Create virtual environment

```bash
uv venv
```

Activate:

**Windows**

```bash
.venv\Scripts\activate
```

**Mac/Linux**

```bash
source .venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
uv add fastapi uvicorn motor pydantic-settings python-dotenv
```

### 4️⃣ Run the server

```bash
uv run python run.py
```

Server runs at:

```
http://127.0.0.1:8000
```

Swagger Docs:

```
http://127.0.0.1:8000/docs
```

---

## 🔌 API Versioning

All routes are prefixed with:

```
/api/v1
```

Example:

```
GET /api/v1/
```

---

## 📌 Upcoming Modules

* Authentication (JWT)
* Driver onboarding
* Trip creation (shared & private)
* Seat-based booking logic
* Payment integration
* Admin dashboard

---

## 🎯 Goal

Build scalable transport infrastructure for Ladakh while respecting its local taxi union and stand-based ecosystem.
