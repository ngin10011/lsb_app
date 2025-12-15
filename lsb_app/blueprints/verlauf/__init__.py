# lsb_app/blueprints/verlauf/__init__.py
from flask import Blueprint

bp = Blueprint(
    "verlauf",
    __name__,
    url_prefix="/auftraege/<int:auftrag_id>/verlauf",
)

from . import routes  # noqa: E402,F401
