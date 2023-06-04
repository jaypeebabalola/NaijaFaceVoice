from. import db, login_manager
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask_login import UserMixin, current_user
from flask import Flask, current_app


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(150), unique = True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))

class Video(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    save_directory = db.Column(db.String(500), nullable=False)  

    # Foreign key relationship with User model
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('videos', lazy=True))

    def __init__(self, url, title, save_directory):
        self.url = url
        self.title = title
        self.save_directory = save_directory
        self.user = current_user

def get_token(user, expires_sec=300):
    serial=Serializer(current_app.config['SECRET_KEY'], expires_in=expires_sec)
    return serial.dumps({'user_id': user.id}).decode('utf-8')

from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask import current_app

@staticmethod
def verify_token(token):
    serial = Serializer(current_app.config['SECRET_KEY'])
    try:
        user_id = serial.loads(token)['user_id']
    except:
        return None
    return User.query.get(user_id)

