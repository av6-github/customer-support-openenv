from typing import Dict, List
from ticket_generator import generate_tickets

def get_triage_sprint():
    """
    Easy task: 8 clean tickets
    """
    tickets = generate_tickets("triage_sprint", n=8)

    return {
        "tickets": tickets,
        "max_steps": 40
    }

def get_queue_pressure():
    tickets = generate_tickets("queue_pressure", n=3)
    
    # Add task-specific hidden properties
    tickets[0]["churn_risk"] = 0.8
    
    tickets[1]["duplicate_of"] = tickets[0]["ticket_id"]
    
    tickets[2]["category"] = "incident"
    tickets[2]["priority"] = "urgent"
    tickets[2]["queue"] = "engineering"
    tickets[2]["incident_id"] = "INC1"
    tickets[2]["text"] = "Server down"

    return {
        "tickets": tickets,
        "max_steps": 20,
        "tool_budget": 5
    }

def get_incident_cascade():
    tickets = generate_tickets("incident_cascade", n=2)
    
    tickets[0]["category"] = "incident"
    tickets[0]["priority"] = "urgent"
    tickets[0]["queue"] = "engineering"
    tickets[0]["incident_id"] = "INC1"
    tickets[0]["text"] = "App not loading"
    
    tickets[1]["vip"] = True
    tickets[1]["fraud_flag"] = True

    return {
        "tickets": tickets,
        "max_steps": 25,
        "tool_budget": 5
    }