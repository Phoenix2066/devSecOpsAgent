def incident_edges(incident_id: str) -> list[dict]:
    return [{"from": incident_id, "to": "fix-upgrade-requests", "type": "HAS_FIX"}]
