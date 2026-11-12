-- Initial proposed routine: review before enabling reminders.
INSERT INTO schedule_events (title,start_time,end_time,recurrence,weekdays,notes) VALUES
('Wake up','04:30','04:45','daily','{}','Initial routine'),
('Meditation','05:00','05:30','daily','{}','Initial routine'),
('Bath','05:30','06:00','daily','{}','Initial routine'),
('Havan preparation','06:00','06:30','daily','{}','Initial routine'),
('Havan','06:30','07:00','daily','{}','Initial routine'),
('Yoga or gym','08:00','09:00','weekly','{1,2,3,4,5,6}','Confirm weekday exercise details'),
('Evening prayer','18:00','18:30','daily','{}','Initial routine'),
('Friday study class','16:30','17:30','weekly','{5}','Confirm class end time');
