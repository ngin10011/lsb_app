# lsb_app/forms/__init__.py
from .patient import PatientForm
from .tb import TBPatientForm
from .address import AddressForm
from .auftrag import AuftragForm

__all__ = ["PatientForm", "TBPatientForm", "AddressForm", "AuftragForm"]
