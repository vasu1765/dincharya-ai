BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate'
 OR current_setting('server_version_num')::int/10000<>17
 OR to_regclass('beta.lunar_reference') IS NULL
 THEN RAISE EXCEPTION 'personal PG17 after migration 0006 required'; END IF;
END $$;
SET LOCAL ROLE personal_executor;
-- Mirrors only the independently published and guarded Delhi rows in
-- prototypes/panchang/personal-annual-references.json.
INSERT INTO beta.lunar_reference(lunar_key,month_kind,civil_year,day,selection) VALUES
 ('margashirsha-purnimanta-krishna-10','ordinary',2026,date '2026-12-03','single'),
 ('margashirsha-purnimanta-krishna-10','ordinary',2027,date '2027-11-23','single'),
 ('margashirsha-purnimanta-krishna-10','ordinary',2028,date '2028-11-12','single');
COMMIT;
