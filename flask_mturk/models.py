from flask_mturk import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.id}', '{self.username}', '{self.email}', '{self.password}')"


# class HIT(db.Model):
#    id = "test"


# class MicroHIT(db.Model):
#    id = "test"
