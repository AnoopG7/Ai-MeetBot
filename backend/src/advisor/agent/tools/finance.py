from __future__ import annotations

from livekit.agents.llm import function_tool

from ...core.logging import get_logger

logger = get_logger(__name__)


@function_tool
async def calculate_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int,
) -> str:
    """Calculate the monthly EMI for a loan. Provide principal amount, annual interest rate
    (as percentage, e.g. 9.5 for 9.5%%), and tenure in months."""
    try:
        monthly_rate = annual_rate / 12 / 100
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months
        emi /= (1 + monthly_rate) ** tenure_months - 1

        total_payment = emi * tenure_months
        total_interest = total_payment - principal

        return (
            f"Loan EMI Summary:\n"
            f"• Principal: ₹{principal:,.0f}\n"
            f"• Annual Rate: {annual_rate:.2f}%\n"
            f"• Tenure: {tenure_months} months ({tenure_months // 12}y {tenure_months % 12}m)\n"
            f"• Monthly EMI: ₹{emi:,.0f}\n"
            f"• Total Interest: ₹{total_interest:,.0f}\n"
            f"• Total Payment: ₹{total_payment:,.0f}"
        )
    except Exception:
        logger.exception("EMI calculation failed")
        return "Could not calculate EMI. Please check the values and try again."


@function_tool
async def calculate_sip_returns(
    monthly_investment: float,
    expected_annual_return: float,
    tenure_years: int,
) -> str:
    """Project the returns from a Systematic Investment Plan (SIP).
    Provide monthly investment amount, expected annual return rate (as percentage),
    and investment tenure in years."""
    try:
        months = tenure_years * 12
        monthly_rate = expected_annual_return / 12 / 100

        if monthly_rate == 0:
            total_invested = monthly_investment * months
            return (
                f"SIP Projection (0% return):\n"
                f"• Monthly: ₹{monthly_investment:,.0f}\n"
                f"• Total Invested: ₹{total_invested:,.0f}\n"
                f"• Estimated Returns: ₹0\n"
                f"• Final Value: ₹{total_invested:,.0f}"
            )

        final_value = monthly_investment * ((1 + monthly_rate) ** months - 1) / monthly_rate
        final_value *= 1 + monthly_rate

        total_invested = monthly_investment * months
        estimated_returns = final_value - total_invested

        return (
            f"SIP Projection:\n"
            f"• Monthly Investment: ₹{monthly_investment:,.0f}\n"
            f"• Expected Return: {expected_annual_return:.1f}% p.a.\n"
            f"• Tenure: {tenure_years} years\n"
            f"• Total Invested: ₹{total_invested:,.0f}\n"
            f"• Estimated Returns: ₹{estimated_returns:,.0f}\n"
            f"• Final Value: ₹{final_value:,.0f}\n"
            f"• Note: This is a projection, not a guarantee. "
            f"Actual returns may vary."
        )
    except Exception:
        logger.exception("SIP calculation failed")
        return "Could not calculate SIP returns. Please check the values and try again."


@function_tool
async def assess_risk_profile(
    age: int,
    annual_income: float,
    monthly_expenses: float,
    existing_savings: float,
    investment_horizon_years: int,
    has_dependents: bool,
    existing_loans: bool,
) -> str:
    """Assess the user's investment risk profile based on their financial situation
    and goals. Returns a risk profile (conservative/moderate/aggressive) with
    suggested allocation."""
    try:
        monthly_surplus = annual_income / 12 - monthly_expenses
        savings_ratio = existing_savings / max(annual_income, 1)

        score = 0

        if age < 30:
            score += 3
        elif age < 45:
            score += 2
        else:
            score += 1

        if investment_horizon_years >= 15:
            score += 3
        elif investment_horizon_years >= 7:
            score += 2
        else:
            score += 1

        if savings_ratio >= 0.5:
            score += 3
        elif savings_ratio >= 0.2:
            score += 2
        else:
            score += 1

        if monthly_surplus > 50000:
            score += 2
        elif monthly_surplus > 15000:
            score += 1

        if not has_dependents:
            score += 1
        if not existing_loans:
            score += 1

        if score >= 11:
            profile = "Aggressive"
            equity_debt = "75-85% Equity / 15-25% Debt"
        elif score >= 7:
            profile = "Moderate"
            equity_debt = "50-60% Equity / 40-50% Debt"
        else:
            profile = "Conservative"
            equity_debt = "20-30% Equity / 70-80% Debt"

        return (
            f"Risk Profile Assessment:\n"
            f"• Risk Profile: {profile}\n"
            f"• Suggested Allocation: {equity_debt}\n"
            f"• Monthly Surplus: ₹{monthly_surplus:,.0f}\n"
            f"• Savings/Income Ratio: {savings_ratio:.1%}\n"
            f"• Investment Horizon: {investment_horizon_years} years\n\n"
            f"Disclaimer: This is a basic assessment. "
            f"Consult a SEBI-registered advisor for a detailed financial plan."
        )
    except Exception:
        logger.exception("risk assessment failed")
        return "Could not complete risk assessment. Please try again with valid inputs."


@function_tool
async def escalate_to_human(reason: str) -> str:
    """Request to speak with a human financial advisor. Provide the reason
    for escalation."""
    logger.info("human escalation requested", reason=reason)

    return (
        "I understand you'd like to speak with a human advisor. "
        "I've noted your request regarding: " + reason + ". "
        "Unfortunately, human advisor transfer is not yet available in this demo. "
        "Please contact your financial institution directly for personalized assistance. "
        "In the meantime, I'm happy to answer any general questions I can help with."
    )
