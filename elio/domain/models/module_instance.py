from pydantic import BaseModel, Field
from typing import List
from .signal import Signal


class ModuleInstance(BaseModel):
    template_name: str
    channel_capacity: int
    slot_number: int | None = None
    node_id: int | None = None
    signals: List[Signal] = Field(default_factory=list)

    def has_capacity(self):
        return len(self.signals) < self.channel_capacity

    def allocate(self, signal: Signal):
        if not self.has_capacity():
            raise Exception("Capacity exceeded")
        self.signals.append(signal)