from .finance import (
    assess_risk_profile,
    calculate_emi,
    calculate_sip_returns,
    escalate_to_human,
)
from .knowledge import lookup_finance_knowledge

FINANCE_TOOLS = [
    lookup_finance_knowledge,
    calculate_emi,
    calculate_sip_returns,
    assess_risk_profile,
    escalate_to_human,
]

__all__ = [
    "FINANCE_TOOLS",
    "lookup_finance_knowledge",
    "calculate_emi",
    "calculate_sip_returns",
    "assess_risk_profile",
    "escalate_to_human",
]
