CREATE INDEX tickets_open_last_activity_idx ON tickets (last_activity_at) WHERE is_open;
