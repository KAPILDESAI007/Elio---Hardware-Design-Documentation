from pydantic import BaseModel, Field
from typing import List
from .module_instance import ModuleInstance


class Node(BaseModel):
    node_id: int
    modules: List[ModuleInstance] = Field(default_factory=list)