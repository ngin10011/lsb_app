# lsb_app/forms/__init__.py
from .patient import PatientForm
from .tb import TBPatientForm
from .address import AddressForm
from .auftrag import AuftragForm
from .institut import InstitutForm, InstitutSelectForm
from .angehoeriger import AngehoerigerForm
from .behoerde import BehoerdeForm
from .rechnung import RechnungForm, RechnungCreateForm
from .dummy_csrf import DummyCSRFForm
from .verlauf import VerlaufForm, DeleteForm

__all__ = ["PatientForm", "TBPatientForm", "AddressForm", "AuftragForm",
           "InstitutForm", "AngehoerigerForm", "BehoerdeForm",
           "RechnungForm", "RechnungCreateForm", "DummyCSRFForm",
           "VerlaufForm", "DeleteForm", "InstitutSelectForm"]
