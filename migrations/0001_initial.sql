CREATE TABLE customers (
    user_id BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tickets (
    user_id BIGINT PRIMARY KEY REFERENCES customers (user_id) ON DELETE CASCADE,
    topic_id BIGINT NOT NULL UNIQUE,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
