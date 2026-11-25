import os
import time
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from fastapi import FastAPI, HTTPException, Request, Query
from pydantic import BaseModel, Field

API_TYPE = os.getenv("API_TYPE", "customers")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
HOSTNAME = os.getenv("HOSTNAME", "localhost")

FRAUD_URL = os.getenv(
    "FRAUD_URL",
    "http://fraud-api.openbank-core.svc.cluster.local:8080"
)

TITLES = {
    "customers": "Customers",
    "accounts": "Accounts",
    "payments": "Payments",
    "fraud": "Fraud Detection",
    "exchange": "Exchange",
    "premium": "Premium Services",
    "legacy": "Legacy Banking",
    "unstable": "Unstable Services",
}

app = FastAPI(
    title=f"OpenBank {TITLES.get(API_TYPE, API_TYPE)} API",
    version=API_VERSION,
    description=(
        "OpenBank training environment. "
        "All banking data is fictional."
    ),
    contact={
        "name": "OpenBank API Team"
    }
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("openbank")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid.uuid4())
    )

    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    duration = round(
        (time.perf_counter() - start) * 1000, 2
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-API-Version"] = API_VERSION
    response.headers["X-Backend"] = HOSTNAME

    logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": API_TYPE,
        "version": API_VERSION,
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration
    }))

    return response


@app.get("/healthz", tags=["Operations"])
def health():
    return {"status": "healthy"}


@app.get("/readyz", tags=["Operations"])
def ready():
    return {"status": "ready"}


@app.get("/info", tags=["Operations"])
def info():
    return {
        "service": API_TYPE,
        "version": API_VERSION,
        "hostname": HOSTNAME
    }


# CUSTOMERS API

CUSTOMERS = [
    {
        "id": "C001",
        "name": "Maria Silva",
        "segment": "premium",
        "status": "active"
    },
    {
        "id": "C002",
        "name": "Joao Santos",
        "segment": "standard",
        "status": "active"
    },
    {
        "id": "C003",
        "name": "Ana Costa",
        "segment": "standard",
        "status": "inactive"
    }
]


if API_TYPE == "customers":

    @app.get("/customers", tags=["Customers"])
    def list_customers():
        return CUSTOMERS

    @app.get("/customers/{customer_id}", tags=["Customers"])
    def get_customer(customer_id: str):
        for customer in CUSTOMERS:
            if customer["id"] == customer_id:
                return customer

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )


# ACCOUNTS API

ACCOUNTS = [
    {
        "id": "A001",
        "customer_id": "C001",
        "currency": "BRL",
        "balance": 25000.00
    },
    {
        "id": "A002",
        "customer_id": "C002",
        "currency": "BRL",
        "balance": 3500.00
    }
]


if API_TYPE == "accounts":

    @app.get("/accounts", tags=["Accounts"])
    def list_accounts():
        return ACCOUNTS

    @app.get("/accounts/{account_id}", tags=["Accounts"])
    def get_account(account_id: str):
        for account in ACCOUNTS:
            if account["id"] == account_id:
                return account

        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )


# SHARED MODELS

class Payment(BaseModel):
    account_id: str
    amount: float = Field(gt=0)
    currency: str = "BRL"


# FRAUD API

if API_TYPE == "fraud":

    @app.post("/fraud", tags=["Fraud"])
    def evaluate_fraud(payment: Payment):

        high_risk = payment.amount > 10000

        return {
            "account_id": payment.account_id,
            "risk_score": 90 if high_risk else 10,
            "risk": "high" if high_risk else "low",
            "approved": not high_risk
        }


# PAYMENTS API

if API_TYPE == "payments":

    @app.post("/payments", tags=["Payments"])
    async def create_payment(
        payment: Payment,
        request: Request
    ):

        try:
            async with httpx.AsyncClient(
                timeout=5.0
            ) as client:

                response = await client.post(
                    f"{FRAUD_URL}/fraud",
                    json=payment.model_dump(),
                    headers={
                        "X-Request-ID":
                            request.state.request_id
                    }
                )

                response.raise_for_status()
                fraud = response.json()

        except httpx.HTTPError:
            raise HTTPException(
                status_code=503,
                detail="Fraud service unavailable"
            )

        if not fraud["approved"]:
            raise HTTPException(
                status_code=422,
                detail="Payment rejected by fraud service"
            )

        return {
            "payment_id": str(uuid.uuid4()),
            "status": "approved",
            "amount": payment.amount,
            "currency": payment.currency,
            "fraud_check": fraud
        }


# EXCHANGE API

RATES = {
    "USD": 5.50,
    "EUR": 6.10,
    "GBP": 7.20
}


if API_TYPE == "exchange":

    @app.get("/exchange", tags=["Exchange"])
    def list_rates():
        return {
            "base": "BRL",
            "rates": RATES,
            "simulated": True
        }

    @app.get("/exchange/{currency}", tags=["Exchange"])
    def get_rate(currency: str):
        currency = currency.upper()

        if currency not in RATES:
            raise HTTPException(
                status_code=404,
                detail="Currency not found"
            )

        return {
            "currency": currency,
            "rate_in_brl": RATES[currency],
            "simulated": True
        }


# PREMIUM API

if API_TYPE == "premium":

    @app.get("/premium", tags=["Premium"])
    def premium_services():
        return {
            "service": "Premium Market Intelligence",
            "classification": "restricted",
            "features": [
                "market-insights",
                "advanced-analytics",
                "priority-support"
            ],
            "version": API_VERSION
        }


# LEGACY API

if API_TYPE == "legacy":

    @app.get("/legacy", tags=["Legacy"])
    def legacy_service(request: Request):
        return {
            "system": "OpenBank Mainframe Simulator",
            "protocol": "HTTP",
            "version": API_VERSION,
            "request_path": request.url.path,
            "channel": request.headers.get(
                "X-Bank-Channel", "unknown"
            )
        }


# UNSTABLE API

if API_TYPE == "unstable":

    @app.get("/unstable", tags=["Troubleshooting"])
    async def unstable_service(
        delay: float = Query(default=0, ge=0, le=30),
        status: int = Query(default=200, ge=200, le=599)
    ):

        await asyncio.sleep(delay)

        if status >= 400:
            raise HTTPException(
                status_code=status,
                detail="Simulated backend error"
            )

        return {
            "status": "success",
            "delay_seconds": delay,
            "hostname": HOSTNAME
        }

