# lsb_app/blueprints/tb/__init__.py
from flask import Blueprint

bp = Blueprint("tb", __name__, template_folder="../../templates/tb")

from . import routes  # noqa: E402,F401
