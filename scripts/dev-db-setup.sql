-- One-time setup for running ERMS against a locally installed PostgreSQL (without Docker).
-- Run as the `postgres` superuser, replacing CHANGE_ME with a password of your choice:
--
--   & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -v pwd="'CHANGE_ME'" -f scripts/dev-db-setup.sql
--
-- Then put the same password in backend/.env (copy from backend/.env.example).

CREATE ROLE erms WITH LOGIN PASSWORD :pwd;
CREATE DATABASE erms OWNER erms;
CREATE DATABASE erms_test OWNER erms;
