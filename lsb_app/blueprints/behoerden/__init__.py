from flask import Blueprint

bp = Blueprint(
    "behoerden",
    __name__,
    url_prefix="/behoerden",
    template_folder="../../templates/behoerden",
)

from . import routes  # noqa: E402,F401
