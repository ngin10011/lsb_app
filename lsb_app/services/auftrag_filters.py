# lsb_app/services/auftrag_filters.py
from sqlalchemy import and_, or_

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
    return and_(
        Auftrag.status == AuftragsStatusEnum.READY,
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
