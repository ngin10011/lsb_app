# lsb_app/blueprints/debug/routes.py
from __future__ import annotations
from flask import request, render_template, current_app, abort
from lsb_app.blueprints.debug import bp
from lsb_app.extensions import db

# Modelle einmal importieren (nur die, die es tatsächlich gibt)
# Passen Sie die Liste bei Bedarf an.
try:
    from lsb_app.models import (
        Patient, Adresse, Auftrag, Bestattungsinstitut, Behoerde, Angehoeriger,
        Rechnung, Verlauf
    )
    MODEL_REGISTRY = [Patient, Adresse, Auftrag, Bestattungsinstitut, Behoerde, 
                      Angehoeriger, Rechnung, Verlauf]
except Exception:
    # Fallback, wenn noch nicht alles existiert
    from lsb_app import models as _models
    MODEL_REGISTRY = [
        getattr(_models, name) for name in dir(_models)
        if isinstance(getattr(_models, name), type)
        and hasattr(getattr(_models, name), "__table__")
    ]

def _fmt(val):
    """Kleine Hilfsformatierung: Datum, Enum, Relationen."""
    import datetime
    from enum import Enum

    if val is None:
        return "—"
    if isinstance(val, Enum):
        # Enum.value anzeigen, sonst Name
        return getattr(val, "value", val.name)
    if isinstance(val, (datetime.date, datetime.datetime)):
        try:
            return val.strftime("%d.%m.%Y")
        except Exception:
            return str(val)
    # SQLAlchemy-Relationen: möglichst kompakt
    # Hat das Objekt ein 'id'-Attribut, zeige Klasse#id
    if hasattr(val, "__class__") and hasattr(val, "id"):
        return f"{val.__class__.__name__}#{getattr(val, 'id', '?')}"
    # Sequenzen wie Listen von Behörden/Angehörigen
    if isinstance(val, (list, tuple, set)):
        items = []
        for x in val:
            if hasattr(x, "id"):
                items.append(f"{x.__class__.__name__}#{getattr(x, 'id', '?')}")
            else:
                items.append(str(x))
        return ", ".join(items) if items else "—"
    # Längere Strings kürzen
    s = str(val)
    return s if len(s) <= 120 else s[:117] + "..."

def _visible_models(only_param: str | None):
    if not only_param:
        return MODEL_REGISTRY
    wanted = {n.strip() for n in only_param.split(",") if n.strip()}
    return [m for m in MODEL_REGISTRY if m.__name__ in wanted]

@bp.route("/db", methods=["GET"])
def db_overview():
    # Optional: nur im Debug-Modus anzeigen.
    # Entfernen Sie die nächste Zeile, wenn auch ohne DEBUG erlaubt sein soll.
    if not current_app.debug and not current_app.testing:
        abort(404)

    # Parameter
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 500))  # Kappung
    only = request.args.get("only")  # z. B. "Patient,Adresse"

    models_out = []
    for model in _visible_models(only):
        # Spaltennamen aus der Tabelle
        try:
            columns = [c.name for c in model.__table__.columns]
        except Exception:
            columns = []

        # Datensätze holen
        try:
            q = model.query
            # Bestmöglich nach PK sortieren, falls vorhanden
            if hasattr(model, "id"):
                q = q.order_by(getattr(model, "id").desc())
            rows = q.limit(limit).all()
        except Exception:
            rows = []

        models_out.append({
            "name": model.__name__,
            "columns": columns,
            "rows": rows,
        })

    # Funktion `fmt` für das Template bereitstellen
    return render_template("debug_db.html", models=models_out, fmt=_fmt)
