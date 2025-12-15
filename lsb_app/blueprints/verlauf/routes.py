# lsb_app/blueprints/verlauf/routes.py
from datetime import date
from flask import render_template, redirect, url_for, flash, abort, request

from lsb_app.extensions import db
from lsb_app.models.auftrag import Auftrag
from lsb_app.models.verlauf import Verlauf
from . import bp
from lsb_app.forms import VerlaufForm, DeleteForm


def _auftrag_or_404(auftrag_id: int) -> Auftrag:
    return db.session.get(Auftrag, auftrag_id) or abort(404)

def _verlauf_or_404(auftrag_id: int, verlauf_id: int) -> Verlauf:
    v = db.session.get(Verlauf, verlauf_id)
    if not v or v.auftrag_id != auftrag_id:
        abort(404)
    return v


@bp.get("/")
def index(auftrag_id: int):
    auftrag = _auftrag_or_404(auftrag_id)
    verlauf = (
    Verlauf.query
    .filter(Verlauf.auftrag_id == auftrag_id)
    .order_by(Verlauf.datum.desc(), Verlauf.id.desc())
    .all()
)
    delete_form = DeleteForm()
    return render_template(
        "verlauf/list.html",
        auftrag=auftrag,
        verlauf=verlauf,
        delete_form=delete_form,
    )


@bp.route("/new", methods=["GET", "POST"])
def new(auftrag_id: int):
    auftrag = _auftrag_or_404(auftrag_id)
    form = VerlaufForm()

    if form.validate_on_submit():
        v = Verlauf(
            auftrag_id=auftrag_id,
            datum=form.datum.data,
            ereignis=form.ereignis.data.strip(),
        )
        db.session.add(v)
        db.session.commit()
        flash("Verlaufseintrag wurde angelegt.", "success")
        return redirect(url_for("verlauf.index", auftrag_id=auftrag_id))

    if form.datum.data is None:
        form.datum.data = date.today()

    return render_template("verlauf/form.html", auftrag=auftrag, form=form, verlauf=None)


@bp.route("/<int:verlauf_id>/edit", methods=["GET", "POST"])
def edit(auftrag_id: int, verlauf_id: int):
    auftrag = _auftrag_or_404(auftrag_id)
    v = _verlauf_or_404(auftrag_id, verlauf_id)

    form = VerlaufForm(obj=v)

    if form.validate_on_submit():
        form.populate_obj(v)
        v.ereignis = v.ereignis.strip()
        db.session.commit()
        flash("Verlaufseintrag wurde aktualisiert.", "success")
        return redirect(url_for("verlauf.index", auftrag_id=auftrag_id))

    return render_template("verlauf/form.html", auftrag=auftrag, form=form, verlauf=v)


@bp.post("/<int:verlauf_id>/delete")
def delete(auftrag_id: int, verlauf_id: int):
    _auftrag_or_404(auftrag_id)
    v = _verlauf_or_404(auftrag_id, verlauf_id)

    db.session.delete(v)
    db.session.commit()
    flash("Verlaufseintrag wurde gelöscht.", "success")
    return redirect(url_for("verlauf.index", auftrag_id=auftrag_id))