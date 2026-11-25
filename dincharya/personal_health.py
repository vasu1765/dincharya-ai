"""Read aggregate health on the isolated personal candidate using the observer role."""
import argparse
import json
from pathlib import Path


def summarize(row):
    enabled, poller, worker, due, uncertain, unsettled, age = row
    return dict(ready=bool(enabled and poller and worker and not uncertain and not unsettled),
                gateway_owned=poller, worker_owned=worker, pending_due=due,
                oldest_due_seconds=age, uncertain=uncertain, unsettled_ui=unsettled)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recorded-root', type=Path, required=True)
    root = parser.parse_args().recorded_root
    if not root.is_absolute():
        raise ValueError('Absolute fixture root required')
    import psycopg
    with psycopg.connect(host='db', dbname='dincharya_personal_candidate', user='personal_operator',
                         password=(root/'personal_operator.key').read_text().strip(),
                         connect_timeout=3, options='-c statement_timeout=3000') as connection:
        result = summarize(connection.execute('SELECT * FROM beta.health()').fetchone())
    print(json.dumps(result))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit('Health unavailable: '+type(exc).__name__) from None
