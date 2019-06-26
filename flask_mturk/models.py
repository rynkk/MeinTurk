from flask_mturk import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.id}', '{self.username}', '{self.email}', '{self.password}')"


"""class HIT(db.Model):
    hitgroup = db.Column(db.Integer)
    title = db.Column(db.String)
    description = db.Column(db.String)
    question = db.Column(db.Integer)
    hitLayoutId = db.Column(db.Integer)
    hitLayoutParameters = db.Column(db.Integer)
    reward = db.Column(db.String)
    AssignmentDurationInSeconds = db.Column(db.Integer)
    LifetimeInSeconds = db.Column(db.Integer)
    keywords = db.Column(db.String)
    maxAssignments = db.Column(db.Integer)
    autoApprovalDelayInSeconds = db.Column(db.Integer)
    QualificationRequirements = db.Column(db.Integer)
    AssignmentReviewPolicy = db.Column(db.Integer)
    HITReviewPolicy = db.Column(db.Integer)
    RequesterAnnotation = db.Column(db.String)
    UniqueRequestToken = db.Column(db.String)

"""

# class MicroHIT(db.Model):
#    id = "test"
