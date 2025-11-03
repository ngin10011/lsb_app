# lsb_app/blueprints/invoices/routes.py
from flask import Blueprint, make_response, abort, render_template
# from lsb_app.models import Invoice
# from lsb_app.services.invoice import render_invoice_pdf
# from sqlalchemy.orm import joinedload
from lsb_app.blueprints.rechnungen import bp


@bp.get("/<int:inv_id>")
def rechnung(inv_id):
    return render_template("rechnungen/standard.html", rechnungsnummer=inv_id)
