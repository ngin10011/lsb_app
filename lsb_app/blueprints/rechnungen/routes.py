# lsb_app/blueprints/invoices/routes.py
from flask import Blueprint, current_app, render_template
# from lsb_app.models import Invoice
# from lsb_app.services.invoice import render_invoice_pdf
# from sqlalchemy.orm import joinedload
from lsb_app.blueprints.rechnungen import bp
from lsb_app.models import Patient, Auftrag, AuftragsStatusEnum
from lsb_app.services.rechnung_vm_factory import build_rechnung_vm
from datetime import date


@bp.get("/<int:aid>")
def rechnung(aid):
    auftrag = Auftrag.query.get_or_404(aid)

    vm = build_rechnung_vm(
        auftrag=auftrag,
        cfg=current_app.config,
        rechnungsdatum=date.today()
    )
    return render_template("rechnungen/standard.html", vm=vm)
