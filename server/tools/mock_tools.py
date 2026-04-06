def lookup_account(account_id):
    """
    Returns hidden account info
    """
    return {
        "fraud_flag": account_id.endswith("F"),
        "vip": account_id.startswith("VIP")
    }


def check_incident(incident_id):
    return {
        "severity": "high",
        "status": "active"
    }


def check_refund_eligibility(ticket):
    if "payment" in ticket["text"].lower():
        return True
    return False