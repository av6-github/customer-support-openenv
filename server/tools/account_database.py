import hashlib

def _hash_to_prob(val: str) -> float:
    """Returns deterministic float between 0 and 1 based on hash."""
    return int(hashlib.md5(val.encode()).hexdigest(), 16) / (16**32)

ACCOUNT_DB = {
    "VIP-101": {"fraud_score": 0.05, "vip_tier": "enterprise", "lifetime_value": 150000},
    "USER-999-F": {"fraud_score": 0.95, "vip_tier": "free", "lifetime_value": 0},
}

def generate_account_info(account_id: str) -> dict:
    if account_id in ACCOUNT_DB:
        base = ACCOUNT_DB[account_id]
        fraud_risk_score = base["fraud_score"]
        vip_tier = base["vip_tier"]
        ltv = base["lifetime_value"]
    else:
        h = _hash_to_prob(account_id)
        fraud_risk_score = min(1.0, h * 0.8)
        vip_tier = "premium" if (h * 100) % 10 > 8 else "free"
        ltv = int(h * 5000)

    return {
        "fraud_flag": fraud_risk_score > 0.7 or account_id.endswith("F"),
        "vip": vip_tier in ["premium", "enterprise"] or account_id.startswith("VIP"),
        "fraud_risk_score": fraud_risk_score,
        "vip_tier": vip_tier,
        "lifetime_value": ltv,
        "account_health": "poor" if fraud_risk_score > 0.6 else "good"
    }

def generate_incident_info(incident_id: str) -> dict:
    h = _hash_to_prob(incident_id)
    if h > 0.8:
        sev = "critical"
    elif h > 0.4:
        sev = "high"
    else:
        sev = "medium"
        
    status = "active" if h > 0.2 else "resolved"
    
    return {
        "severity": sev,
        "status": status,
        "customer_impact_estimate": int(h * 1000)
    }
