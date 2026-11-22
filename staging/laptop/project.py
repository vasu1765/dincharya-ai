"""Explicit, mutually exclusive disposable staging namespaces."""
SELECTORS = {
    'DINCHARYA_STAGE1_RECHECK': 'dincharya-stage1-recheck',
    'DINCHARYA_STAGE1_COMPLETE': 'dincharya-stage1-complete',
    'DINCHARYA_STAGE2': 'dincharya-stage2-physical',
    'DINCHARYA_STAGE2_RECOVERY_ONLY': 'dincharya-stage2-recovery-only',
}


def select_project(environment):
    active = [name for name in SELECTORS if environment.get(name) == '1']
    if len(active) > 1:
        raise ValueError('Conflicting project selectors')
    # Preserve rejection of nonempty conflicting legacy selector values.
    if active and any(environment.get(name) for name in SELECTORS if name != active[0]):
        raise ValueError('Conflicting project selectors')
    return SELECTORS[active[0]] if active else 'dincharya-laptop-staging'
