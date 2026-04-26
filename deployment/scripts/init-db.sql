-- PostgreSQL init script (runs once on container start)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for fast text search

-- Ensure news user has full access
GRANT ALL PRIVILEGES ON DATABASE newsdb TO news;
