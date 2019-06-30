from flask_mturk import db


class MiniGroup(db.Model):
    __tablename__ = 'mini_group'
    group_id = db.Column(db.String, primary_key=True)
    active = db.Column(db.Boolean, nullable=False)
    layout = db.Column(db.String, nullable=False)
    lifetime = db.Column(db.Integer, nullable=False)

    def __init__(self, group_id, active, layout, lifetime):
        self.group_id = group_id
        self.active = active
        self.layout = layout
        self.lifetime = lifetime

    def __repr__(self):
        return f"MiniGroup('{self.group_id}', '{self.active}', 'someBigQuestion')"  # '{self.layout}')"


class MiniLink(db.Model):
    __tablename__ = 'mini_link'
    group_id = db.Column(db.String, db.ForeignKey('mini_group.group_id', ondelete="CASCADE"), primary_key=True, nullable=False)
    active_hit = db.Column(db.String, db.ForeignKey('mini_hit.uid'), nullable=False)

    def __init__(self, group_id, active_hit):
        self.group_id = group_id
        self.active_hit = active_hit

    def __repr__(self):
        return f"MiniLink('{self.group_id}', '{self.active_hit})"


class MiniHIT(db.Model):
    __tablename__ = 'mini_hit'

    parent_id = db.Column(db.String, db.ForeignKey('mini_group.group_id', ondelete="CASCADE"), primary_key=True)
    position = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String)
    workers = db.Column(db.Integer, nullable=False)

    def __init__(self, id, position, workers, hit_id=None):
        self.parent_id = id
        self.position = position
        self.uid = hit_id
        self.workers = workers

    def __repr__(self):
        return f"MiniHIT('{self.uid}', '{self.parent_id}', '{self.position}', '{self.workers}')"
