"""Unit tests for the deterministic risk scoring engine."""

import pytest
from src.models import ApplicationData
from src.risk_engine import compute_risk_metrics


def _make_app(**overrides) -> ApplicationData:
    """Create an ApplicationData with sensible defaults, overridable per-test."""
    defaults = dict(
        client_name="Test Corp",
        client_type="sme",
        registration_number="HRB 99999",
        industry="Technology",
        years_in_business=5,
        annual_revenue=1_000_000,
        net_profit=150_000,
        total_assets=800_000,
        total_liabilities=300_000,
        existing_debt=0,
        product_type="term_loan",
        requested_amount=200_000,
        purpose="Working capital",
        proposed_tenor_months=36,
        existing_client=False,
    )
    defaults.update(overrides)
    return ApplicationData(**defaults)


class TestFinancialRatios:
    """Verify that individual financial ratios are computed correctly."""

    def test_debt_to_equity(self):
        app = _make_app(total_assets=1_000_000, total_liabilities=400_000, requested_amount=200_000)
        m = compute_risk_metrics(app)
        # equity = 1M - 400k = 600k, total_debt = 400k + 200k = 600k → D/E = 1.0
        assert m.debt_to_equity == 1.0

    def test_dscr(self):
        app = _make_app(
            net_profit=300_000,
            requested_amount=300_000,
            proposed_tenor_months=36,
            existing_debt=0,
        )
        m = compute_risk_metrics(app)
        # annual_debt_service = 300k / 3 = 100k, DSCR = 300k / 100k = 3.0
        assert m.debt_service_coverage == 3.0

    def test_dscr_with_existing_debt(self):
        app = _make_app(
            net_profit=300_000,
            requested_amount=300_000,
            proposed_tenor_months=36,
            existing_debt=500_000,
        )
        m = compute_risk_metrics(app)
        # annual_service = 100k + 500k*0.08 = 140k, DSCR = 300k / 140k ≈ 2.14
        assert m.debt_service_coverage == 2.14

    def test_current_ratio(self):
        app = _make_app(total_assets=900_000, total_liabilities=300_000)
        m = compute_risk_metrics(app)
        assert m.current_ratio == 3.0

    def test_leverage_ratio(self):
        app = _make_app(total_assets=1_000_000, total_liabilities=400_000, requested_amount=100_000)
        m = compute_risk_metrics(app)
        # total_debt = 400k + 100k = 500k, leverage = 500k / 1M = 0.5
        assert m.leverage_ratio == 0.5

    def test_ltv_with_collateral(self):
        app = _make_app(requested_amount=500_000, collateral_value=750_000)
        m = compute_risk_metrics(app)
        assert m.loan_to_value == 0.67

    def test_ltv_without_collateral(self):
        app = _make_app(collateral_value=None)
        m = compute_risk_metrics(app)
        assert m.loan_to_value is None

    def test_zero_liabilities(self):
        app = _make_app(total_liabilities=0)
        m = compute_risk_metrics(app)
        assert m.current_ratio == 99


class TestRiskRating:
    """Verify the composite risk score maps to the correct rating."""

    def test_strong_client_gets_high_rating(self):
        app = _make_app(
            annual_revenue=5_000_000,
            net_profit=800_000,
            total_assets=3_000_000,
            total_liabilities=500_000,
            existing_debt=100_000,
            requested_amount=300_000,
            proposed_tenor_months=48,
            collateral_value=600_000,
            years_in_business=12,
            existing_client=True,
        )
        m = compute_risk_metrics(app)
        assert m.risk_rating in ("AAA", "AA", "A")
        assert m.risk_score <= 35

    def test_weak_client_gets_low_rating(self):
        app = _make_app(
            annual_revenue=200_000,
            net_profit=-50_000,
            total_assets=150_000,
            total_liabilities=300_000,
            existing_debt=200_000,
            requested_amount=500_000,
            proposed_tenor_months=12,
            collateral_value=100_000,
            years_in_business=1,
            existing_client=False,
        )
        m = compute_risk_metrics(app)
        assert m.risk_rating in ("B", "CCC")
        assert m.risk_score >= 65

    def test_existing_client_bonus(self):
        base = _make_app(existing_client=False)
        existing = _make_app(existing_client=True)
        m_base = compute_risk_metrics(base)
        m_existing = compute_risk_metrics(existing)
        assert m_existing.risk_score == m_base.risk_score - 5

    def test_score_clamped_to_bounds(self):
        # Even with extreme values, score stays in 1-100
        app = _make_app(
            annual_revenue=100_000_000,
            net_profit=50_000_000,
            total_assets=200_000_000,
            total_liabilities=1_000,
            requested_amount=1_000,
            proposed_tenor_months=120,
            collateral_value=500_000_000,
            years_in_business=50,
            existing_client=True,
        )
        m = compute_risk_metrics(app)
        assert 1 <= m.risk_score <= 100


class TestSampleData:
    """Verify ratings for the three bundled sample applications."""

    def test_techflow_aa(self):
        """TechFlow Solutions — strong SME, expected AA."""
        app = _make_app(
            client_name="TechFlow Solutions GmbH",
            industry="Software & IT Services",
            years_in_business=7,
            annual_revenue=3_200_000,
            net_profit=480_000,
            total_assets=2_100_000,
            total_liabilities=850_000,
            existing_debt=200_000,
            requested_amount=500_000,
            proposed_tenor_months=48,
            collateral_value=750_000,
            existing_client=True,
        )
        m = compute_risk_metrics(app)
        assert m.risk_rating == "AA"

    def test_green_harvest_bb(self):
        """Green Harvest Farms — moderate risk, expected BB."""
        app = _make_app(
            client_name="Green Harvest Farms Sp. z o.o.",
            industry="Agriculture & Food Processing",
            years_in_business=12,
            annual_revenue=8_500_000,
            net_profit=510_000,
            total_assets=6_200_000,
            total_liabilities=3_800_000,
            existing_debt=1_200_000,
            requested_amount=1_200_000,
            proposed_tenor_months=60,
            collateral_value=1_800_000,
            existing_client=False,
        )
        m = compute_risk_metrics(app)
        assert m.risk_rating == "BB"

    def test_urban_style_high_risk(self):
        """Urban Style Retail — high risk, expected CCC."""
        app = _make_app(
            client_name="Urban Style Retail Ltd",
            industry="Retail — Fashion & Apparel",
            years_in_business=3,
            annual_revenue=1_800_000,
            net_profit=-45_000,
            total_assets=950_000,
            total_liabilities=720_000,
            existing_debt=350_000,
            requested_amount=400_000,
            proposed_tenor_months=12,
            collateral_value=300_000,
            existing_client=False,
        )
        m = compute_risk_metrics(app)
        assert m.risk_rating == "CCC"
