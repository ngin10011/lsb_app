# lsb_app/blueprints/debug/__init__.py
from flask import Blueprint

bp = Blueprint("debug", __name__, template_folder="../../templates")

from . import routes  # noqa: E402,F401
