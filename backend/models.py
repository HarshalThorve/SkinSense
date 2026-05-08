"""
SkinSense Database Models
"""
import datetime
from flask_login import UserMixin
from backend import db, login_manager


# ================== USER LOADER ==================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================== DATABASE MODELS ==================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))
    phone = db.Column(db.String(20))


class TrendHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    trend = db.Column(db.String(200))
    result = db.Column(db.String(50))  # e.g., "Harmful", "Safe"
    status = db.Column(db.String(20))  # "danger", "success", "warning"
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class IngredientScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    image_path = db.Column(db.String(200))
    result_summary = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class SkinReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    image_file = db.Column(db.String(120))
    skin_type = db.Column(db.String(50))
    concern = db.Column(db.String(50))
    facewash = db.Column(db.String(10))
    moisturizer = db.Column(db.String(10))
    sunscreen = db.Column(db.String(10))
    sleep = db.Column(db.String(20))
    water = db.Column(db.String(20))
    # AI Analysis Results (from Image)
    ai_pimples = db.Column(db.Boolean)
    ai_oily = db.Column(db.Boolean)
    ai_spots = db.Column(db.Boolean)
    result = db.Column(db.String(100))
    skin_health_score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
