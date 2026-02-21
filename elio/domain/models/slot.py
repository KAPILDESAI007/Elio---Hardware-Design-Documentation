from pydantic import BaseModel


class Slot(BaseModel):
    slot_number: int
    occupied: bool = False