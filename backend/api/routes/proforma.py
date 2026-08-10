from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/proforma", tags=["proforma"], dependencies=[Depends(verify_api_key)])


@router.post("")
async def calculate_proforma(body: dict, session: AsyncSession = Depends(get_session)):
    deal_id = body.get("deal_id")
    purchase_price = body["purchase_price"]
    reno_cost_per_sqft = body.get("reno_cost_per_sqft", 18)
    stabilized_rent_per_sqft = body.get("stabilized_rent_per_sqft", 12.50)
    exit_cap_rate = body.get("exit_cap_rate", 0.065)
    hold_months = body.get("hold_months", 18)
    ltv = body.get("ltv", 0.65)
    interest_rate = body.get("interest_rate", 0.072)

    # Get building sqft if deal_id provided
    sqft = body.get("sqft")
    if deal_id and not sqft:
        result = await session.execute(
            text("""
                SELECT b.sqft FROM deals d
                JOIN buildings b ON d.building_id = b.id
                WHERE d.id = :deal_id
            """),
            {"deal_id": deal_id},
        )
        row = result.first()
        if row:
            sqft = row[0]

    if not sqft:
        sqft = body.get("sqft", 20000)

    reno_cost = reno_cost_per_sqft * sqft
    total_cost = purchase_price + reno_cost

    stabilized_noi = stabilized_rent_per_sqft * sqft
    exit_value = int(stabilized_noi / exit_cap_rate) if exit_cap_rate else 0

    gross_profit = exit_value - total_cost
    equity_invested = total_cost * (1 - ltv)

    # Debt service during hold
    loan_amount = total_cost * ltv
    monthly_interest = loan_amount * (interest_rate / 12)
    total_debt_service = monthly_interest * hold_months

    net_profit = gross_profit - total_debt_service

    cash_on_cash = net_profit / equity_invested if equity_invested else 0
    equity_multiple = (equity_invested + net_profit) / equity_invested if equity_invested else 0

    # Simplified IRR approximation
    irr_approx = (equity_multiple ** (12 / hold_months)) - 1 if hold_months > 0 else 0

    return {
        "sqft": sqft,
        "total_cost": int(total_cost),
        "stabilized_noi": int(stabilized_noi),
        "exit_value": int(exit_value),
        "gross_profit": int(gross_profit),
        "equity_invested": int(equity_invested),
        "cash_on_cash": round(cash_on_cash, 2),
        "equity_multiple": round(equity_multiple, 1),
        "irr_approx": round(irr_approx, 2),
        "hold_months": hold_months,
    }
