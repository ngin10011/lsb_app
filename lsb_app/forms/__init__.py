# lsb_app/forms/__init__.py
from .patient import PatientForm
from .tb import TBPatientForm
from .address import AddressForm
from .auftrag import AuftragForm
from .institut import InstitutForm
from .angehoeriger import AngehoerigerForm

__all__ = ["PatientForm", "TBPatientForm", "AddressForm", "AuftragForm",
           "InstitutForm", "AngehoerigerForm"]
