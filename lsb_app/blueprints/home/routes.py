# lsb_app/blueprints/home/routes.py
from flask import Blueprint, render_template
from lsb_app.extensions import db
from lsb_app.models import Auftrag
from sqlalchemy.orm import selectinload

bp = Blueprint("home", __name__)

@bp.route("/")
def index():
    recent_auftraege = (
        db.session.query(Auftrag)
        .options(selectinload(Auftrag.patient))
        .order_by(Auftrag.id.desc())
        .limit(5)
        .all()
    )
    return render_template("home.html", recent_auftraege=recent_auftraege)
