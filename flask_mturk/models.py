from flask_mturk import db


class MiniGroup(db.Model):
    __tablename__ = 'mini_group'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, nullable=False)
    layout = db.Column(db.String, nullable=False)
    lifetime = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.String(80), nullable=False)
    minihits = db.relationship("MiniHIT", cascade="all, delete, delete-orphan", backref="mini_group")

    def __repr__(self):
        return '<MiniGroup %r, %r>' % (self.id, self.active)


class MiniHIT(db.Model):
    __tablename__ = 'mini_hit'
    id = db.Column(db.String)
    active = db.Column(db.Boolean, nullable=False)
    group_id = db.Column(db.String, db.ForeignKey('mini_group.id'), primary_key=True)
    position = db.Column(db.Integer, primary_key=True, nullable=False)
    workers = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<MiniHIT %r, %r, %r, %r, %r>' % (self.id, self.active, self.group_id, self.position, self.workers)
