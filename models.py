from pydantic import BaseModel
from typing import List, Dict, Optional, Any


# -----------------------------
# ACTION MODEL
# -----------------------------
class SupportOpsAction(BaseModel):
    action_type: str
    ticket_id: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    queue: Optional[str] = None
    duplicate_ticket_id: Optional[str] = None
    account_id: Optional[str] = None
    incident_id: Optional[str] = None


# -----------------------------
# REWARD MODEL
# -----------------------------
class SupportOpsReward(BaseModel):
    reward: float



# -----------------------------
# TICKET MODEL
# -----------------------------
class Ticket(BaseModel):
    ticket_id: str
    text: str
    category: Optional[str] = None
    priority: Optional[str] = None
    queue: Optional[str] = None
    status: str = "open"


# -----------------------------
# OBSERVATION MODEL
# -----------------------------
class SupportOpsObservation(BaseModel):
    tickets: List[Ticket]
    step_count: int
    max_steps: int
    tool_credits_remaining: int
    queue_health: float
    visible_churn_risk: Dict


# -----------------------------
# INTERNAL STATE MODEL
# -----------------------------
class SupportOpsState(BaseModel):
    tickets: Dict[str, Ticket]

    step_count: int = 0
    max_steps: int = 20

    tool_credits_remaining: int = 5
    queue_health: float = 1.0

    # tracking
    categorized: Dict[str, str] = {}
    prioritized: Dict[str, str] = {}
    routed: Dict[str, str] = {}

    resolved_tickets: List[str] = []

    # advanced features
    churn_risk: Dict[str, float] = {}
    duplicates: Dict[str, str] = {}
    active_incidents: List[str] = []
    last_tool_result: Optional[Dict] = None