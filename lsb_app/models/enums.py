# lsb_app/models/enums.py
import enum

class GeschlechtEnum(str, enum.Enum):
    MAENNLICH = "männlich"
    WEIBLICH = "weiblich"
    DIVERS = "divers"
    UNBEKANNT = "unbekannt"

class KostenstelleEnum(str, enum.Enum):
    ANGEHOERIGE = "Angehörige"
    BESTATTUNGSINSTITUT = "Bestattungsinstitut"
    BEHOERDE = "Behörde"
    UNBEKANNT = "unbekannt"

class AuftragsStatusEnum(str, enum.Enum):
    READY = "READY"
    WAIT  = "WAIT"
    TODO  = "TODO"
    SENT  = "SENT"
    DONE  = "DONE"

class RechnungsArtEnum(str, enum.Enum):
    ERSTRECHNUNG = "Erstrechnung"
    MAHNUNG = "Mahnung"
    STORNO = "Storno"

class RechnungsadressModus(str, enum.Enum):
    INSTITUT = "INSTITUT"
    INSTITUT_WEITERLEITUNG = "INSTITUT_WEITERLEITUNG"
    ANGEHOERIGE = "ANGEHOERIGE"