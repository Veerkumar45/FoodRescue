from pydantic import BaseModel, Field
from typing import Optional

class ProductIn(BaseModel):
    product_id: str
    store_id: str = "STORE_001"
    name: str
    category: str
    unit: str = "unit"
    expiry_date: str
    quantity: int = Field(ge=0)
    safety_status: str = "pending"

class SaleIn(BaseModel):
    event_id: str
    product_id: str
    quantity: int = Field(gt=0)
    event_timestamp: str

class DonationIn(BaseModel):
    donation_id: str
    product_id: str
    quantity: int = Field(gt=0)
    note: Optional[str] = None
