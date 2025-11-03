# lsb_app/blueprints/invoices/__init__.py
from flask import Blueprint

bp = Blueprint("invoices", __name__, template_folder="../../templates/invoices")

from . import routes  # noqa: E402,F401
