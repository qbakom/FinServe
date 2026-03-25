"""Deterministic risk scoring engine for FinServe Credit Memo Generator.

Computes financial ratios and a composite risk score without AI —
the LLM is only used for narrative generation, not for risk decisions.
"""

from models import ApplicationData, RiskMetrics


def compute_risk_metrics(app: ApplicationData) -> RiskMetrics:
    equity = app.total_assets - app.total_liabilities
    if equity <= 0:
        equity = 1  # avoid division by zero

    total_debt = app.total_liabilities + app.requested_amount

    debt_to_equity = total_debt / equity
    leverage_ratio = total_debt / app.total_assets if app.total_assets > 0 else 99
    revenue_to_debt = app.annual_revenue / total_debt if total_debt > 0 else 99

    # Simplified DSCR: net profit / estimated annual debt service
    annual_debt_service = app.requested_amount / max(app.proposed_tenor_months / 12, 1)
    if app.existing_debt > 0:
        annual_debt_service += app.existing_debt * 0.08  # assume 8% avg rate on existing
    dscr = app.net_profit / annual_debt_service if annual_debt_service > 0 else 0

    current_ratio = app.total_assets / app.total_liabilities if app.total_liabilities > 0 else 99

    ltv = None
    if app.collateral_value and app.collateral_value > 0:
        ltv = app.requested_amount / app.collateral_value

    # --- Composite risk score (1 = safest, 100 = riskiest) ---
    score = 50  # start at neutral

    # Debt-to-equity impact (-20 to +25)
    if debt_to_equity < 0.5:
        score -= 20
    elif debt_to_equity < 1.0:
        score -= 10
    elif debt_to_equity < 2.0:
        score += 5
    elif debt_to_equity < 4.0:
        score += 15
    else:
        score += 25

    # DSCR impact (-20 to +20)
    if dscr > 3.0:
        score -= 20
    elif dscr > 2.0:
        score -= 12
    elif dscr > 1.5:
        score -= 5
    elif dscr > 1.0:
        score += 5
    else:
        score += 20

    # Leverage impact
    if leverage_ratio > 0.8:
        score += 10
    elif leverage_ratio < 0.3:
        score -= 10

    # LTV impact
    if ltv is not None:
        if ltv < 0.5:
            score -= 10
        elif ltv < 0.7:
            score -= 5
        elif ltv > 1.0:
            score += 15
        elif ltv > 0.85:
            score += 5

    # Business maturity
    if app.years_in_business < 2:
        score += 10
    elif app.years_in_business > 10:
        score -= 5

    # Profitability
    if app.net_profit <= 0:
        score += 15
    elif app.net_profit / app.annual_revenue > 0.15:
        score -= 5

    # Existing relationship
    if app.existing_client:
        score -= 5

    score = max(1, min(100, score))

    # Map to rating
    if score <= 15:
        rating = "AAA"
    elif score <= 25:
        rating = "AA"
    elif score <= 35:
        rating = "A"
    elif score <= 50:
        rating = "BBB"
    elif score <= 65:
        rating = "BB"
    elif score <= 80:
        rating = "B"
    else:
        rating = "CCC"

    return RiskMetrics(
        debt_to_equity=round(debt_to_equity, 2),
        debt_service_coverage=round(dscr, 2),
        current_ratio=round(current_ratio, 2),
        leverage_ratio=round(leverage_ratio, 2),
        loan_to_value=round(ltv, 2) if ltv else None,
        revenue_to_debt=round(revenue_to_debt, 2),
        risk_score=score,
        risk_rating=rating,
    )
