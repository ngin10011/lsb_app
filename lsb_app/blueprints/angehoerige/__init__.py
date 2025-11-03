from flask import Blueprint

bp = Blueprint(
    "angehoerige",
    __name__,
    url_prefix="/angehoerige",
    template_folder="../../templates/angehoerige",
)

from . import routes  # noqa: E402,F401
