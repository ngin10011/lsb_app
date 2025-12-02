from datetime import date
from lsb_app.extensions import db
from lsb_app.models import Verlauf

def add_verlauf(auftrag, text, datum=None):
    v = Verlauf(
        datum=datum or date.today(),
        ereignis=text,
        auftrag=auftrag,
    )
    db.session.add(v)
    return v
