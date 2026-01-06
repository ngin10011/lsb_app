# lsb_app/blueprints/tests/routes.py
from flask import render_template
from lsb_app.blueprints.tests import bp

from lsb_app.services.ynab import get_account_map, create_transaction_leichenschau, get_category_map


@bp.route("/test", methods=["GET"])
def test():
    account_map = get_category_map()

    # payee = "Testbezahler"
    # amount_total = 100.00
    # invoice = ["1000", "1001"]
    # date_transaction = "2025-12-21"

    # ok, msg = create_transaction_leichenschau(
    #     payee=payee,
    #     amount_total=amount_total,
    #     invoice=invoice,
    #     date_transaction=date_transaction,
    # )

    return render_template("test_seite.html", account_map=account_map)
