# lsb_app/blueprints/tests/routes.py
from lsb_app.blueprints.tests import bp
from flask import render_template

@bp.route("/test", methods=["GET"])
def test():

    return render_template("test_seite.html")