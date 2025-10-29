# lsb_app/blueprints/auftraege/__init__.py
from flask import Blueprint
bp = Blueprint("auftraege", __name__, template_folder="../../templates")
from . import routes  # noqa: E402,F401
