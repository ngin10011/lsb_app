# lsb_app/blueprints/home/routes.py
from flask import Blueprint, render_template, current_app
from lsb_app.extensions import db
from lsb_app.models import Auftrag
from sqlalchemy.orm import selectinload
from lsb_app.viewmodels.home_vm import HomeVM

bp = Blueprint("home", __name__)

# @bp.route("/")
# def index():
#     recent_auftraege = (
#         db.session.query(Auftrag)
#         .options(selectinload(Auftrag.patient))
#         .order_by(Auftrag.id.desc())
#         .limit(5)
#         .all()
#     )
#     return render_template("home.html", recent_auftraege=recent_auftraege)

@bp.route("/")
def index():
    
    recent_auftraege = (
        db.session.query(Auftrag)
        .order_by(Auftrag.id.desc())
        .limit(10)
        .all()
    )

    vm = HomeVM(
        recent_auftraege=recent_auftraege,
        ready_email_count=0,
        ready_print_count=2,
        todo_count=3,
        debug=current_app.debug, 
        )
    return render_template("home.html", vm=vm)