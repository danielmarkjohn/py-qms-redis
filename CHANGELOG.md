# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
*Any work you are currently doing but haven't deployed yet goes here.*

## [1.0.0] - 2026-05-27
### Added
- Core Quick-Commerce Management System (QMS) backend.
- FastAPI REST endpoints for System Health, Catalog, and Orders.
- MongoDB integration for persistent storage of users, products, and orders.
- Redis integration for blazing-fast order caching and Rate Limiting.
- Kafka Event Publisher and Consumer for asynchronous order processing.
- Stateless JWT-based Authentication middleware (`JWTMiddleware`).
- Automatic customer ID extraction from JWT payload for secure order creation.

### Changed
- Refactored Kafka and Redis logic into reusable `CacheService` and `EventPublisher`.

### Security
- Implemented Fixed-Window Rate Limiting to prevent auth brute-force attacks.
- Secured order endpoints to ensure users can only access their own data.

### Advice
- PATCH (1.0.1): You fixed a bug.
- MINOR (1.1.0): You added a new feature in a backwards-compatible way.
- MAJOR (2.0.0): You made breaking changes that require the frontend to update.


## [1.1.0] - 2026-05-28

### Added
- **AI Assistant API:** Integrated an Agentic RAG chat endpoint (`POST /chat/`) powered by Groq and Llama 3.1.
- **Dynamic Tool Calling:** The AI can securely query a user's specific order history and tracking numbers from MongoDB using their JWT payload.
- **Advanced Catalog Endpoints:** - `GET /catalog/search`: Full-text search across product names, categories, and IDs.
  - `GET /catalog/{product_id}`: Fetch single product details.
- **Admin Catalog Endpoints:**
  - `POST /catalog/`: Add new products to the database.
  - `PATCH /catalog/{product_id}/stock`: Atomically update inventory using MongoDB `$inc`.
- **Centralized Config:** Added `app/config/config.py` to manage AI model settings and external API keys cleanly.
- Dedicated Postman collection for AI Chat testing.

### Changed
- **Massive Latency Optimization:** Implemented industry-standard connection pooling for MongoDB (`minPoolSize=10`), Redis, and Kafka. This eliminated the 300ms "cold start" database latency, dropping it to ~25ms.
- **Upgraded AI Model:** Migrated from the deprecated `llama3-8b-8192` model to `llama-3.1-8b-instant` for faster and more accurate tool calling.
- **Smarter AI Queries:** Updated the `query_orders` AI tool to accept dynamic parameters (`tracking_number`, `limit`), preventing 500 errors when users ask about specific tracking IDs.

### Fixed
- Fixed a startup crash in `database.py` by correcting the `aiokafka` producer argument from `batch_size` to `max_batch_size`.