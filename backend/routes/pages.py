"""
Static Pages Routes — Products, Natural Remedies, Dermatologists
"""
from flask import Blueprint, render_template
from flask_login import login_required
from backend.data.products import PRODUCT_LIST
from backend.data.remedies import REMEDIES_LIST
from backend.data.doctors import CLINICAL_DOCTORS, SOCIAL_DOCTORS

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/natural-remedies')
@login_required
def natural_remedies():
    return render_template('natural_remedies.html', remedies=REMEDIES_LIST)


@pages_bp.route('/products')
@login_required
def products():
    return render_template('products.html', products=PRODUCT_LIST)


@pages_bp.route('/dermatologists')
@login_required
def dermatologists():
    return render_template('dermatologists.html', clinical=CLINICAL_DOCTORS, social=SOCIAL_DOCTORS)
