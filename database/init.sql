-- Khởi tạo database PostgreSQL cho Water Purifier Management
-- Chạy file này với quyền superuser (postgres), ví dụ:
--   psql -U postgres -f database/init.sql

SELECT 'CREATE DATABASE waterpurifier'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'waterpurifier')\gexec

-- Tạo user (bỏ qua nếu dùng docker-compose — user đã có sẵn)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'waterpurifier') THEN
    CREATE ROLE waterpurifier WITH LOGIN PASSWORD 'waterpurifier';
  END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE waterpurifier TO waterpurifier;

-- Sau khi tạo database, chạy migration để tạo bảng:
--   alembic upgrade head
