CREATE TABLE IF NOT EXISTS schedule_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 title TEXT NOT NULL,
 start_time TIME NOT NULL,
 end_time TIME,
 timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
 recurrence TEXT NOT NULL CHECK (recurrence IN ('daily','weekly','once')),
 weekdays SMALLINT[] NOT NULL DEFAULT '{}',
 event_date DATE,
 enabled BOOLEAN NOT NULL DEFAULT TRUE,
 notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT recurrence_fields CHECK (
  (recurrence='daily' AND event_date IS NULL AND cardinality(weekdays)=0) OR
  (recurrence='weekly' AND event_date IS NULL AND cardinality(weekdays)>0 AND weekdays <@ ARRAY[1,2,3,4,5,6,7]::SMALLINT[]) OR
  (recurrence='once' AND event_date IS NOT NULL AND cardinality(weekdays)=0)
 ),
 CONSTRAINT end_after_start CHECK (end_time IS NULL OR end_time > start_time)
);
CREATE INDEX IF NOT EXISTS idx_schedule_events_enabled ON schedule_events(enabled, recurrence, start_time);
