from flask import Blueprint

bp = Blueprint("zahlungen", __name__, url_prefix="/zahlungen")

from . import routes  # noqa: E402,F401
