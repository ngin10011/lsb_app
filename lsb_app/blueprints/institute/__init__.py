from flask import Blueprint

bp = Blueprint(
    "institute",
    __name__,
    url_prefix="/institute",
    template_folder="../../templates/institute",
)

from . import routes  # noqa: E402,F401
