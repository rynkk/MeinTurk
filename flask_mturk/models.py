from flask_mturk import db


class HiddenHIT(db.Model):
    __tablename__ = 'hidden_hit'
    id = db.Column(db.String, primary_key=True)


class MiniGroup(db.Model):
    __tablename__ = 'mini_group'
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    hidden = db.Column(db.Boolean, nullable=False)
    assignments_goal = db.Column(db.Integer, nullable=False)
    assignments_submitted = db.Column(db.Integer, nullable=False)
    layout = db.Column(db.String, nullable=False)
    lifetime = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.String(80), nullable=False)
    batch_qualification = db.Column(db.String(80), nullable=False)
    minihits = db.relationship("MiniHIT", cascade="all, delete, delete-orphan", backref="mini_group")

    # TODO: update repr
    def __repr__(self):
        return '<MiniGroup %r, %r>' % (self.id, self.status)


class MiniHIT(db.Model):
    __tablename__ = 'mini_hit'
    id = db.Column(db.String)
    status = db.Column(db.String, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('mini_group.id'), primary_key=True)
    position = db.Column(db.Integer, primary_key=True)
    workers = db.Column(db.Integer, nullable=False)
    # answers are only set if HIT got cached
    answers = db.relationship("CachedAnswer", cascade="all, delete, delete-orphan")

    # TODO: update repr
    def __repr__(self):
        return '<MiniHIT %r, %r, %r, %r, %r>' % (self.id, self.status, self.group_id, self.position, self.workers)


class CachedAnswer(db.Model):
    __tablename__ = 'cached_answer'
    hit_id = db.Column(db.String, db.ForeignKey('mini_hit.id'), primary_key=True)
    assignment_id = db.Column(db.String, primary_key=True)
    worker_id = db.Column(db.String, primary_key=True)
    answer = db.Column(db.String, nullable=False)
    approved = db.Column(db.Boolean, nullable=False)
    bonus = db.Column(db.Integer)
    reason = db.Column(db.String)
    # TODO: REMOVE accept_date?
    accept_date = db.Column(db.DateTime, nullable=False)
    time_taken = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<CachedAnswer %r, %r, %r, %r, %r, %r>' % (self.hit_id, self.assignment_id, self.worker_id, self.answer, self.approved, self.bonus)
