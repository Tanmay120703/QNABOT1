from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)

    uploads = db.relationship(
        'Upload',
        backref='user',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Upload(db.Model):
    __tablename__ = 'uploads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Upload {self.filename} (User {self.user_id})>"
