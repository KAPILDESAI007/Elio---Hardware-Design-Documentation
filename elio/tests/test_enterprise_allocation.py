"""Test allocation module."""
def test_basic_allocation():
    assert 1 + 1 == 2

    from domain.models.signal import Signal
from core.orchestrator import Orchestrator


def test_enterprise_flow():

    signals = [
        Signal(tag="T1", signal_type="AI"),
        Signal(tag="T2", signal_type="AI"),
        Signal(tag="T3", signal_type="DI"),
    ]

    orchestrator = Orchestrator()
    nodes = orchestrator.run(signals)

    assert len(nodes) >= 1
    assert nodes[0].modules[0].signals