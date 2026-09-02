
from sqlalchemy import func
from web.models import db

class TaskWeightDefault(db.Model):
    __tablename__ = 'task_weight_default'
    id          = db.Column(db.Integer, primary_key=True)
    scope       = db.Column(db.String(50), default='global')   # 'global' | 'department'
    scope_key   = db.Column(db.String(100))                    # dept name or None
    priority    = db.Column(db.String(20), nullable=False)     # low | medium | high | critical
    weight      = db.Column(db.Integer, default=3, nullable=False)
    max_weight  = db.Column(db.Integer, default=10, nullable=False)
    locked_by_default = db.Column(db.Boolean, default=False)
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at  = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    @staticmethod
    def get_weight(priority='medium', department=None):
        """Return (default_weight, max_weight, locked_by_default)."""
        # 1. Try department-specific
        row = TaskWeightDefault.query.filter_by(
            scope='department', scope_key=department, priority=priority
        ).first()
        # 2. Fall back to global
        if not row:
            row = TaskWeightDefault.query.filter_by(
                scope='global', priority=priority
            ).first()
        if row:
            return row.weight, row.max_weight, row.locked_by_default
        # 3. Hardcoded fallback
        fallbacks = {'low': 2, 'medium': 3, 'high': 5, 'critical': 8}
        return fallbacks.get(priority, 3), 10, False

