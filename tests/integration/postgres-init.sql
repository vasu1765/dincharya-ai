-- Future disposable test stack only. Never target the production Compose project.
CREATE DATABASE dincharya_app_test;
\connect dincharya_app_test
CREATE TABLE synthetic_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL,
    starts_at timestamptz NOT NULL
);
INSERT INTO synthetic_events (title, starts_at)
VALUES ('Synthetic event', '2000-01-01 12:00:00+05:30');
