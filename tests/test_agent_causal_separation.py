from app.agents.investigation_agent import root_agent


def test_agent_requires_selected_incident_and_baseline_separation() -> None:
    instruction = str(root_agent.instruction)

    assert "selected incident" in instruction.lower()
    assert "baseline" in instruction.lower()
    assert "RELATED" in instruction
    assert "UNRELATED" in instruction
    assert "UNCERTAIN" in instruction
    assert "Never assume" in instruction
