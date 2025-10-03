from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.governance.audit import AuditLogger


class Agent(ABC):
    def __init__(self, name: str, audit_logger: 'AuditLogger') -> None:
        self.name = name
        self.audit = audit_logger

    @abstractmethod
    def act(self, *args, **kwargs):
        raise NotImplementedError
