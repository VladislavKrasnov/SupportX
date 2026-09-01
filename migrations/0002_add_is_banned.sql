-- 0002_add_is_banned.sql
-- Add is_banned column to users table

ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE;
