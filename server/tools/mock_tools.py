from server.tools.account_database import generate_account_info, generate_incident_info

def lookup_account(account_id):
    """
    Returns hidden account info
    """
    return generate_account_info(account_id)


def check_incident(incident_id):
    return generate_incident_info(incident_id)


def check_refund_eligibility(ticket):
    text = ticket["text"].lower()
    if "payment" in text or "refund" in text or "billing" in text or "charged" in text:
        return True
    return False