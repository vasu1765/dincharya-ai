"""Bounded response diagnostics for a disposable staging approval."""
import json
from uuid import UUID

FALLBACK = 'Operation could not be confirmed. Check the same preview or status.'


def verify_confirmation(result, ledger):
    """A commit and its expected SDK reply are independent requirements."""
    counts, control = ledger()
    has_control = False
    try:
        has_control = str(UUID(str(control))) == control
    except ValueError:
        pass
    result = result if isinstance(result, dict) else {}
    messages = result.get('messages')
    valid_list = isinstance(messages, list)
    replies = messages if valid_list else []
    expected = f'Rule approved. ID {control}.'
    approved = sum(isinstance(reply, str) and reply.startswith('Rule approved. ID ') for reply in replies)
    relay = result.get('relay')
    diagnostic = dict(events=counts[0], controls=counts[1], audits=counts[2], slots=counts[3],
                      deliveries=counts[4], replies=len(replies) if valid_list else -1,
                      approved_replies=approved, fallback_replies=replies.count(FALLBACK),
                      keyboard='missing' if 'keyboard' not in result else ('present' if result['keyboard'] is not None else 'absent'),
                      matches_control=has_control and replies == [expected],
                      relay=relay if relay in ('no_confirmation_call','relay_error','unexpected_result',
                                               'approved_other_reply','approved_reply') else 'unknown')
    print(json.dumps(diagnostic, sort_keys=True), flush=True)
    if not (tuple(counts)==(1,1,1,0,0) and diagnostic['matches_control']
            and diagnostic['keyboard']=='absent' and relay=='approved_reply'):
        raise RuntimeError('Approval response or ledger mismatch; stop without replay')

def snapshot(query):
    row=json.loads(query("""SELECT json_build_array(
      (SELECT count(*) FROM public.schedule_events),
      (SELECT count(*) FROM lunar_private.recurring_control),
      (SELECT count(*) FROM lunar_private.recurring_audit),
      (SELECT count(*) FROM lunar_private.notification_slot),
      (SELECT count(*) FROM public.reminder_deliveries),
      (SELECT min(id::text) FROM lunar_private.recurring_control))"""))
    return row[:5],row[5]


