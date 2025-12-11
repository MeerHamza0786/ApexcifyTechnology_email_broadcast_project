from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RecipientList:
    """Immutable list of email recipients"""
    addresses: List[str]

    @classmethod
    def demo(cls) -> "RecipientList":
        """Create a demo recipient list"""
        return cls(
            [
                "meerhamzagujjar6@gmail.com",
                "hamzaiqbalrajpoot35@gmail.com",
            ]
        )


RECEIVER_EMAILS = RecipientList.demo().addresses.copy()
