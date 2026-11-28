-- Disposable completion acceptance. Check the release registry without creating any events.
DO $$ BEGIN
 IF (SELECT array_agg(day ORDER BY civil_year) FROM beta.lunar_reference
     WHERE lunar_key='margashirsha-purnimanta-krishna-10' AND month_kind='ordinary' AND selection='single')
 IS DISTINCT FROM ARRAY[date '2026-12-03',date '2027-11-23',date '2028-11-12']
 THEN RAISE EXCEPTION 'reviewed Delhi reference register does not match'; END IF;
 IF (SELECT count(*) FROM beta.lunar_reference)<>4 OR EXISTS(SELECT FROM beta.proposal)
 OR EXISTS(SELECT FROM beta.authority) OR EXISTS(SELECT FROM beta.slot)
 THEN RAISE EXCEPTION 'migration seeded unauthorized actions'; END IF;
 IF has_table_privilege('personal_gateway','beta.lunar_reference','INSERT')
 OR has_table_privilege('personal_worker','beta.lunar_reference','UPDATE')
 THEN RAISE EXCEPTION 'runtime could alter reference register'; END IF;
END $$;
