#lsb_app/viewmodels/rechnung_vm.py
from dataclasses import dataclass
from datetime import date
from markupsafe import Markup
from decimal import Decimal
from typing import Mapping, Sequence
from lsb_app.models.auftrag import Auftrag

@dataclass(frozen=True)
class HomeVM:
    recent_auftraege: Sequence[Auftrag]
    debug: bool

    ready_email_count: int
    print_count: int
    todo_count: int
    inquiry_count: int
    wait_overdue_count: int
    overdue_count: int
    sent_count: int
    ready_post_count: int

    @property
    def ready_email_is_zero(self) -> bool:
        return not self.ready_email_count

    @property
    def print_is_zero(self) -> bool:
        return not self.print_count

    @property
    def todo_is_zero(self) -> bool:
        return not self.todo_count 
    
    @property
    def inquiry_is_zero(self) -> bool:
        return not self.inquiry_count
    
    @property
    def wait_overdue_is_zero(self) -> bool:
        return not self.wait_overdue_count
    
    @property
    def overdue_is_zero(self) -> bool:
        return not self.overdue_count
    
    @property
    def sent_is_zero(self) -> bool:
        return not self.sent_count
    
    @property
    def ready_post_is_zero(self) -> bool:
        return not self.ready_post_count