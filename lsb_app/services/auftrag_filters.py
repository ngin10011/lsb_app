# lsb_app/services/auftrag_filters.py
from sqlalchemy import and_, or_
from datetime import date, timedelta
from lsb_app.extensions import db  # falls du es irgendwann brauchst
from lsb_app.models.auftrag import Auftrag
from lsb_app.models.patient import Patient
from lsb_app.models.institut import Bestattungsinstitut
from lsb_app.models.angehoeriger import Angehoeriger
from lsb_app.models.behoerde import Behoerde
from lsb_app.models.enums import KostenstelleEnum, AuftragsStatusEnum


def ready_for_email_filter():
    """
    Aufträge, die:
    - Status READY haben und
    - abhängig von der Kostenstelle eine zustellbare E-Mail-Adresse besitzen.
    """
    cutoff_date = date.today() - timedelta(days=3)

    return and_(
        Auftrag.status == AuftragsStatusEnum.READY,
        Auftrag.auftragsdatum <= cutoff_date,
        or_(
            # 1) Kostenstelle = Bestattungsinstitut + E-Mail im Institut
            and_(
                Auftrag.kostenstelle == KostenstelleEnum.BESTATTUNGSINSTITUT,
                Auftrag.bestattungsinstitut.has(
                    and_(
                        Bestattungsinstitut.email.isnot(None),
                        Bestattungsinstitut.email != "",
                    )
                ),
            ),
            # 2) Kostenstelle = Angehörige + mind. ein Angehöriger mit E-Mail
            and_(
                Auftrag.kostenstelle == KostenstelleEnum.ANGEHOERIGE,
                Auftrag.patient.has(
                    Patient.angehoerige.any(
                        and_(
                            Angehoeriger.email.isnot(None),
                            Angehoeriger.email != "",
                        )
                    )
                ),
            ),
            # 3) Kostenstelle = Behörde + mind. eine Behörde mit E-Mail
            and_(
                Auftrag.kostenstelle == KostenstelleEnum.BEHOERDE,
                Auftrag.behoerden.any(
                    and_(
                        Behoerde.email.isnot(None),
                        Behoerde.email != "",
                    )
                ),
            ),
        ),
    )

def has_deliverable_email_filter():
    """READY + (je nach Kostenstelle) zustellbare E-Mail vorhanden."""
    return and_(
        Auftrag.status == AuftragsStatusEnum.READY,
        or_(
            and_(
                Auftrag.kostenstelle == KostenstelleEnum.BESTATTUNGSINSTITUT,
                Auftrag.bestattungsinstitut.has(
                    and_(Bestattungsinstitut.email.isnot(None), Bestattungsinstitut.email != "")
                ),
            ),
            and_(
                Auftrag.kostenstelle == KostenstelleEnum.ANGEHOERIGE,
                Auftrag.patient.has(
                    Patient.angehoerige.any(
                        and_(Angehoeriger.email.isnot(None), Angehoeriger.email != "")
                    )
                ),
            ),
            and_(
                Auftrag.kostenstelle == KostenstelleEnum.BEHOERDE,
                Auftrag.behoerden.any(
                    and_(Behoerde.email.isnot(None), Behoerde.email != "")
                ),
            ),
        ),
    )

def ready_for_inquiry_filter():
    """
    Aufträge, die:
    - im Status INQUIRY sind
    - mind. 3 Tage alt sind
    - Kostenstelle BESTATTUNGSINSTITUT haben
    - ein Bestattungsinstitut mit hinterlegter E-Mail besitzen
    """
    cutoff_date = date.today() - timedelta(days=3)

    return and_(
        Auftrag.status == AuftragsStatusEnum.INQUIRY,
        Auftrag.auftragsdatum <= cutoff_date,
        Auftrag.kostenstelle == KostenstelleEnum.BESTATTUNGSINSTITUT,
        Auftrag.bestattungsinstitut.has(
            and_(
                Bestattungsinstitut.email.isnot(None),
                Bestattungsinstitut.email != "",
            )
        ),
    )