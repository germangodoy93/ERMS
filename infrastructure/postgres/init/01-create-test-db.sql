-- Runs once, when the PostgreSQL volume is first created (docker compose).
-- Creates a separate, disposable database for integration tests.
CREATE DATABASE erms_test;
