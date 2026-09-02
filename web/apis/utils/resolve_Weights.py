from web.models.task_weight_config import TaskWeightDefault  # adjust import

def _resolve_weight(data, task=None, department=None, is_manager=False):
    """
    Returns (weight, locked) for a task being created or updated.
    """
    priority = data.get('priority', 'medium')
    default_w, max_w, locked_default = TaskWeightDefault.get_weight(priority, department)

    # If admin is explicitly locking/unlocking
    if is_manager and 'weight_locked' in data:
        locked = bool(data['weight_locked'])
    elif task:
        locked = task.weight_locked
    else:
        locked = locked_default

    # Weight value
    if 'weight' in data and data['weight'] is not None:
        try:
            requested = int(data['weight'])
        except (ValueError, TypeError):
            requested = default_w
    else:
        requested = default_w

    # Enforce ceiling
    weight = min(max(requested, 1), max_w)

    # If locked and non-manager tries to change weight → reject silently to default
    if task and task.weight_locked and not is_manager:
        weight = task.weight_locked  # preserve existing

    return weight, locked


