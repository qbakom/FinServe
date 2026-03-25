"""Data models for FinServe Credit Memo Generator."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ClientType(str, Enum):
    SME = "sme"
    RETAIL = "retail"


class ProductType(str, Enum):
    TERM_LOAN = "term_loan"
    REVOLVING_CREDIT = "revolving_credit"
    INVOICE_FINANCING = "invoice_financing"
    EQUIPMENT_LEASE = "equipment_lease"


class ApplicationData(BaseModel):
    # Client information
    client_name: str = Field(..., description="Legal name of the client")
    client_type: ClientType
    registration_number: str = Field(..., description="Company registration / national ID")
    industry: str
    years_in_business: int
    employee_count: Optional[int] = None

    # Financial data
    annual_revenue: float = Field(..., description="Annual revenue in EUR")
    net_profit: float = Field(..., description="Net profit in EUR")
    total_assets: float = Field(..., description="Total assets in EUR")
    total_liabilities: float = Field(..., description="Total liabilities in EUR")
    existing_debt: float = Field(0, description="Existing outstanding debt in EUR")

    # Loan request
    product_type: ProductType
    requested_amount: float = Field(..., description="Requested facility amount in EUR")
    purpose: str = Field(..., description="Purpose of the facility")
    proposed_tenor_months: int = Field(..., description="Proposed tenor in months")
    collateral_description: Optional[str] = None
    collateral_value: Optional[float] = None

    # Additional context
    existing_client: bool = False
    payment_history: Optional[str] = None
    additional_notes: Optional[str] = None


class RiskMetrics(BaseModel):
    debt_to_equity: float
    debt_service_coverage: float
    current_ratio: float
    leverage_ratio: float
    loan_to_value: Optional[float] = None
    revenue_to_debt: float
    risk_score: int = Field(..., ge=1, le=100, description="1=lowest risk, 100=highest risk")
    risk_rating: str  # AAA, AA, A, BBB, BB, B, CCC


class CreditMemo(BaseModel):
    application: ApplicationData
    risk_metrics: RiskMetrics
    executive_summary: str
    financial_analysis: str
    risk_assessment: str
    collateral_analysis: str
    recommendation: str
    conditions: list[str]
    generated_at: str
