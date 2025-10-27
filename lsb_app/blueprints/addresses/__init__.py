# lsb_app/blueprints/addresses/__init__.py
from flask import Blueprint
bp = Blueprint("addresses", __name__, template_folder="../../templates/addresses")
from . import routes  # noqa: E402,F401
