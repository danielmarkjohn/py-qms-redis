# Order API 🍔

A lightweight, asynchronous CRUD API for managing  orders. This service is built with FastAPI and MongoDB (via Motor), utilizing raw JSON request handling for a zero-boilerplate.

## Project Structure

```text
food_order_api/
├── .env                # Environment variables (MongoDB URI, etc.)
├── README.md
├── requirements.txt
└── app/
    ├── __init__.py
    ├── main.py         # Application entry point
    ├── database.py     # MongoDB async connection logic
    └── routers/
        ├── __init__.py
        └── orders.py   # CRUD routing for food orders
```

## Commands

### Setup Dependencies
`python -m venv venv`

### For Mac/Linux:
`source venv/bin/activate`

### For Windows:
`venv\Scripts\activate`

### Install
`task install`

### Run Server
`task dev`
#### The server will be live at: http://127.0.0.1:8000


