-- 0001_initial.sql
-- Create users and topics tables

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS topics (
    user_id BIGINT PRIMARY KEY,
    topic_id BIGINT NOT NULL UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_topics_topic_id ON topics(topic_id);
