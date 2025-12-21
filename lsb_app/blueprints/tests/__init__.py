# lsb_app/blueprints/tests/__init__.py
from flask import Blueprint

bp = Blueprint(
    "tests",
    __name__,
    template_folder="../../templates/tests",
)

from . import routes  # noqa: E402,F401
