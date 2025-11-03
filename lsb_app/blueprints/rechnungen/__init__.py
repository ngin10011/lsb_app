# lsb_app/blueprints/invoices/__init__.py
from flask import Blueprint

bp = Blueprint("rechnungen", __name__, template_folder="../../templates/rechnungen")

from . import routes  # noqa: E402,F401
