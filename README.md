# Event-Driven Order Management API

A high-throughput, asynchronous microservice built with FastAPI. This system implements an event-driven architecture using Kafka for deferred writes (eventual consistency) and Redis for sub-millisecond read caching.

## 🏗 Architecture & Tech Stack

- **Web Framework:** FastAPI (Python 3.12+)
- **Database:** MongoDB Atlas (via `motor` async driver)
- **Cache:** Redis Cloud (via `redis.asyncio`)
- **Message Broker:** Aiven Kafka (via `aiokafka`)
- **Task Runner:** `taskipy`
- **AI / LLM Engine:** Groq API (Llama-3.1-8b-instant)
- **Security:** Stateless JWT Authentication Middleware

### Data Flow Patterns

- **Reads (`GET`):** Checked against Redis first. On cache miss, fetched from MongoDB and cached for 1 hour.
- **Writes (`POST`):** Payload is instantly accepted, assigned an ID, and fired into a Kafka topic (`orders.create`). A background consumer processes the topic and persists the data to MongoDB.
- **Updates/Deletes (`PUT`/`DELETE`):** Synchronously persisted to MongoDB and immediately invalidates the associated Redis cache to prevent stale data.
- **Agentic RAG (`POST /chat`):** User queries are processed by Llama 3.1. If the LLM detects an order-related question, it securely executes a Python tool (`query_orders`) to fetch the user's specific database records, augmenting its natural language response with real-time data.
- **Zero-Trust JWT:** The `customer_id` is never trusted from the client payload. It is mathematically verified and extracted directly from the user's JWT token via FastAPI's request state middleware.

---

## ⚙️ Local Development Setup

### 1. Prerequisites

- Python 3.12+
- MongoDB Atlas Cluster
- Redis Cloud / Upstash instance
- Aiven Kafka Cluster (with mTLS certificates)
- Groq API Account (for AI features)

### 2. Install Dependencies

Clone the repository and install the required packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
task install
```

### 3. Kafka Certificates

Create a `certs/` directory in the root of the project and place your Aiven mTLS certificates inside. Do not commit these files to version control.

```
certs/
  ├── ca.pem
  ├── service.cert
  └── service.key
```

### 4. Environment Variables

Create a `.env` file in the root directory:

```env
# Database
MONGO_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
DB_NAME="order_management"

# Cache
REDIS_URI="redis://default:<password>@<host>:<port>"

# Kafka
KAFKA_BROKER="<host>:<port>"
KAFKA_CA_PATH="certs/ca.pem"
KAFKA_CERT_PATH="certs/service.cert"
KAFKA_KEY_PATH="certs/service.key"
```

---

## 🚀 Running the Application

Because this is a decoupled architecture, you must run both the API server and the background worker concurrently.

**Terminal 1 — Start the Web Server:**

```bash
task dev
```

**Terminal 2 — Start the Kafka Consumer:**

```bash
task worker
```

---

## 📡 API Endpoints

| Method | Endpoint | Description | Cache Behavior |
|--------|----------|-------------|----------------|
| `POST` | `/orders/` | Create a new order (Async) | N/A (Fires Kafka Event) |
| `GET` | `/orders/` | List all orders | Direct Mongo read |
| `GET` | `/orders/{id}` | Get specific order | Cached (Redis) |
| `PUT` | `/orders/{id}` | Update order status | Invalidates Cache |
| `DELETE` | `/orders/{id}` | Delete order | Invalidates Cache |
| `POST` | `/chat/Query Orders` | FAQ Agentic RAG | Dynamic Tool Calling |

### Sample Payload (Create Order)

```json
{
  "product_id": "macbook-pro-16",
  "customer_id": "59b99db4cfa9a34dcd7885b6",
  "amount": 2499.99
}
```

---

## ☁️ Deployment (Render)

This system requires two separate Render services operating from the same repository:

**Web Service**
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Background Worker**
- Start Command: `python -m app.workers.order_consumer`

**Secret Management:**
Upload `ca.pem`, `service.cert`, and `service.key` as Render Secret Files (mapped to `/etc/secrets/`) and update the respective environment variables in the Render dashboard.