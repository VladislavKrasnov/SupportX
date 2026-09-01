-- 0003_add_topic_created_at.sql
-- Add created_at column to topics table for auto-closing

ALTER TABLE topics ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
