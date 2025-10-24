from pydantic import BaseModel, Field

class ProductIn(BaseModel):
    title: str = Field(max_length=255)
    description: str = Field(max_length=5000)
    image_url: str = Field(max_length=512)
    price: float
    currency: str = "CLP"
    score: int = 0
    supplier_sku: str | None = None

class ProductOut(ProductIn):
    id: int
    slug: str
    active: bool
    class Config:
        from_attributes = True
