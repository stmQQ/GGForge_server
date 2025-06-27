from flask import Blueprint, request

from app.models.user_models import User
from app.extensions import db


admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('make-admin', methods=['POST'])
def make_admin():
    data = request.json
    user_email = data['email']
    user = User.query.filter_by(email=user_email).first()
    user.is_admin = True

    db.session.add(user)
    db.session.commit()
