# lsb_app/blueprints/home/routes.py
from flask import Blueprint, render_template, current_app
from lsb_app.extensions import db
from lsb_app.models import Auftrag
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import selectinload
from lsb_app.viewmodels.home_vm import HomeVM
from lsb_app.models import (AuftragsStatusEnum, KostenstelleEnum,
        Bestattungsinstitut, Angehoeriger, Behoerde, Patient)
from lsb_app.services.auftrag_filters import ready_for_email_filter

bp = Blueprint("home", __name__)

@bp.route("/")
def index():
    
    recent_auftraege = (
        db.session.query(Auftrag)
        .order_by(Auftrag.id.desc())
        .limit(10)
        .all()
    )

    ready_email_count = (
    db.session.query(func.count(Auftrag.id))
    .filter(ready_for_email_filter())
    .scalar()
)

    print_count = (
        db.session.query(func.count(Auftrag.id))
        .filter(Auftrag.status == AuftragsStatusEnum.PRINT)
        .scalar()
    )

    todo_count = (
        db.session.query(func.count(Auftrag.id))
        .filter(Auftrag.status == AuftragsStatusEnum.TODO)
        .scalar()
    )

    vm = HomeVM(
        recent_auftraege=recent_auftraege,
        ready_email_count=ready_email_count,
        print_count=print_count,
        todo_count=todo_count,
        debug=current_app.debug, 
        )
    return render_template("home.html", vm=vm)