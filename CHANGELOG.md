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