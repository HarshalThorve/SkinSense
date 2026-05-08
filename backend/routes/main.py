"""
Main Routes — Home, Dashboard, History, Test API
"""
import os
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from backend.models import SkinReport, TrendHistory, IngredientScanHistory

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/test-api')
def test_api():
    key = os.environ.get("GEMINI_API_KEY")
    return {
        "key_loaded": bool(key),
        "key_preview": key[:8] + "..." if key else "NOT FOUND"
    }


@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@main_bp.route('/history')
@login_required
def history():
    skin_reports = SkinReport.query.filter_by(user_id=current_user.id).order_by(SkinReport.id.desc()).all()
    trend_history = TrendHistory.query.filter_by(user_id=current_user.id).order_by(TrendHistory.id.desc()).all()
    scan_history = IngredientScanHistory.query.filter_by(user_id=current_user.id).order_by(IngredientScanHistory.id.desc()).all()

    return render_template('history.html',
                           skin_reports=skin_reports,
                           trend_history=trend_history,
                           scan_history=scan_history)
