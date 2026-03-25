"""AI-powered credit memo narrative generator using Google Gemini API."""

import json
import os
from google import genai
from src.models import ApplicationData, RiskMetrics

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are a senior credit analyst at FinServe, a mid-size financial services company.
You write professional credit memos for the credit committee. Your writing is:
- Concise and factual — no filler
- Structured with clear sections
- Risk-aware: you highlight both strengths and concerns
- Actionable: you end with a clear recommendation and conditions

You receive structured application data and pre-computed risk metrics.
Your job is to generate the NARRATIVE sections of the credit memo.
Do NOT invent financial figures — only use what is provided.
"""


def generate_memo_sections(app: ApplicationData, metrics: RiskMetrics) -> dict:
    """Generate credit memo narrative sections using Gemini."""

    data_context = f"""
APPLICATION DATA:
- Client: {app.client_name} ({app.client_type.value.upper()})
- Registration: {app.registration_number}
- Industry: {app.industry}
- Years in business: {app.years_in_business}
- Employees: {app.employee_count or 'N/A'}
- Existing client: {'Yes' if app.existing_client else 'No'}
- Payment history: {app.payment_history or 'N/A'}

FINANCIALS (EUR):
- Annual revenue: {app.annual_revenue:,.0f}
- Net profit: {app.net_profit:,.0f}
- Total assets: {app.total_assets:,.0f}
- Total liabilities: {app.total_liabilities:,.0f}
- Existing debt: {app.existing_debt:,.0f}

FACILITY REQUEST:
- Product: {app.product_type.value.replace('_', ' ').title()}
- Amount: {app.requested_amount:,.0f} EUR
- Purpose: {app.purpose}
- Tenor: {app.proposed_tenor_months} months
- Collateral: {app.collateral_description or 'None'}
- Collateral value: {f'{app.collateral_value:,.0f} EUR' if app.collateral_value else 'N/A'}

PRE-COMPUTED RISK METRICS:
- Debt-to-Equity: {metrics.debt_to_equity}x
- DSCR: {metrics.debt_service_coverage}x
- Current Ratio: {metrics.current_ratio}x
- Leverage Ratio: {metrics.leverage_ratio}x
- LTV: {f'{metrics.loan_to_value}x' if metrics.loan_to_value else 'N/A'}
- Revenue-to-Debt Ratio: {metrics.revenue_to_debt}x
- Risk Score: {metrics.risk_score}/100
- Risk Rating: {metrics.risk_rating}

ADDITIONAL NOTES: {app.additional_notes or 'None'}
"""

    user_prompt = f"""{data_context}

Generate the following sections as a JSON object with these exact keys:
1. "executive_summary" — 2-3 sentences summarizing the request, client profile, and headline recommendation.
2. "financial_analysis" — 3-5 sentences analyzing the financial position using the provided metrics. Reference specific ratios.
3. "risk_assessment" — 3-5 sentences on key risks and mitigants. Be specific to this client.
4. "collateral_analysis" — 2-3 sentences on collateral adequacy (or note if unsecured).
5. "recommendation" — 1-2 sentences with APPROVE, APPROVE WITH CONDITIONS, or DECLINE and brief justification.
6. "conditions" — a JSON array of 3-6 specific conditions/covenants for approval (or conditions to re-apply if declined).

Return ONLY the JSON object, no markdown formatting."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2000,
            ),
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise RuntimeError("Gemini API rate limit exceeded. Please wait a moment and try again.")
        raise RuntimeError(f"Gemini API error: {error_msg}")

    text = response.text.strip()
    # Handle potential markdown wrapping
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse AI response. Please try again.")
