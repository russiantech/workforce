# web/scripts/seed_weights.py

""" 
You need to create the Flask app and push an application context before using db.session, to avoid working
out of request context.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Create app and push context BEFORE importing db-dependent models
from app import create_app
app = create_app()

with app.app_context():
    from web.models.task_weight_config import TaskWeightDefault
    from web.models import db

    defaults = [
        ('global', None, 'low',      2,  4, False),
        ('global', None, 'medium',   3,  5, False),
        ('global', None, 'high',     5,  7, False),
        ('global', None, 'critical', 8, 10, True),
    ]

    for scope, key, pri, w, mx, lk in defaults:
        existing = TaskWeightDefault.query.filter_by(
            scope=scope, scope_key=key, priority=pri
        ).first()
        if existing:
            existing.weight = w
            existing.max_weight = mx
            existing.locked_by_default = lk
        else:
            db.session.add(
                TaskWeightDefault(
                    scope=scope,
                    scope_key=key,
                    priority=pri,
                    weight=w,
                    max_weight=mx,
                    locked_by_default=lk,
                )
            )

    db.session.commit()
    print("Task weight defaults seeded successfully.")