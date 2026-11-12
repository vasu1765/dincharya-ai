-- Synthetic schema only. This is not the production baseline.
CREATE TABLE public.synthetic_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL,
    starts_at timestamptz NOT NULL
);
CREATE FUNCTION public.synthetic_title(value text) RETURNS text
    LANGUAGE sql IMMUTABLE AS $$ SELECT value; $$;
CREATE FUNCTION public.synthetic_check() RETURNS trigger
    LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;
CREATE TRIGGER synthetic_check_before_insert
    BEFORE INSERT ON public.synthetic_events
    FOR EACH ROW EXECUTE FUNCTION public.synthetic_check();
