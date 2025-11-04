from dataclasses import dataclass
from datetime import date
from markupsafe import Markup
from decimal import Decimal
from typing import Mapping, Sequence

@dataclass(frozen=True)
class LeistungVM:
    kurz: str
    beschreibung: str
    betrag: str

@dataclass(frozen=True)
class RechnungVM:
    auftrag_id: int
    auftragsnummer: int

    rechnungsdatum: date
    auftragsdatum: date

    patient_name: str
    patient_vorname: str
    patient_geburtsdatum: date
    patient_geschlecht: str

    anschrift_html: Markup

    leistungen: Sequence[LeistungVM]

    summe_str: str

    config: Mapping[str, str]

    @property
    def rechnungsnummer_str(self) -> str:
        return f"LS-{self.auftragsnummer:04d}"
    
    @property
    def patient_name_komplett(self) -> str:
        return f"{self.patient_name}, {self.patient_vorname}"
    
    @property
    def verwendungszweck(self) -> str:
        return f"Rechnung {self.rechnungsnummer_str}"
    
    @property
    def verstorbener_gegendert(self) -> str:
        val = getattr(self.patient_geschlecht, "value", self.patient_geschlecht)
        geschlecht = (val or "").lower()

        if geschlecht == "männlich":
            return "Verstorbener"
        elif geschlecht == "weiblich":
            return "Verstorbene"
        else:
            return "Verstorbene(r)"
