SEEDED_INCIDENT = {
    "hit": True,
    "incident_id": "seed-requests-conflict",
    "error_signature": "pip_conflict:requests:2.28.0_vs_2.31.0",
    "fix_applied": "upgrade requests to 2.31.0",
    "confidence": 0.91,
    "success_rate": 0.85,
    "reuse": True,
}


def search_seeded_incidents(error_signature: str) -> dict:
    if "requests" in error_signature or error_signature == SEEDED_INCIDENT["error_signature"]:
        return SEEDED_INCIDENT.copy()
    return {"hit": False, "confidence": 0.0, "reuse": False, "error_signature": error_signature}
