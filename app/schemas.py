from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    FARMER = "farmer"
    BUYER = "buyer"

class UserCreate(BaseModel):
    full_name: str
    phone: str
    email: Optional[EmailStr] = None
    password: str
    role: UserRole = UserRole.FARMER
    district: Optional[str] = None
    village: Optional[str] = None
    sector_id: Optional[int] = None
    country: Optional[str] = None
    company: Optional[str] = None
    buyer_sector: Optional[str] = None

class UserLogin(BaseModel):
    phone: str
    password: str

class UserOut(BaseModel):
    id: int
    full_name: str
    phone: str
    email: Optional[str]
    role: UserRole
    is_approved: bool
    created_at: datetime
    district: Optional[str]
    village: Optional[str]
    sector_id: Optional[int]
    sector_name: Optional[str] = None
    country: Optional[str]
    company: Optional[str]
    buyer_sector: Optional[str]
    average_rating: float = 0.0
    total_ratings: int = 0

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenData(BaseModel):
    id: int

class ProductCreate(BaseModel):
    name: str
    category: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "UGX"
    quantity: Optional[str] = None
    unit: Optional[str] = "kg"
    photo_url: Optional[str] = None
    is_international: bool = False
    shipping_info: Optional[str] = None

class ProductOut(ProductCreate):
    id: int
    farmer_id: int
    created_at: datetime
    farmer_name: Optional[str] = None
    farmer_rating: Optional[float] = 0.0

    class Config:
        from_attributes = True

class InterestCreate(BaseModel):
    product_id: int
    message: Optional[str] = None

class InterestOut(BaseModel):
    id: int
    product_id: int
    farmer_id: int
    buyer_id: int
    buyer_name: str
    buyer_phone: str
    buyer_email: Optional[str]
    buyer_company: Optional[str]
    buyer_country: Optional[str]
    message: Optional[str]
    created_at: datetime
    product_name: Optional[str] = None
    status: str = "pending"

    class Config:
        from_attributes = True

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ApproveFarmer(BaseModel):
    approve: bool

class FarmerRatingCreate(BaseModel):
    farmer_id: int
    rating: int = Field(ge=1, le=5)
    review: Optional[str] = None

class FarmerRatingOut(BaseModel):
    id: int
    farmer_id: int
    buyer_id: int
    rating: int
    review: Optional[str]
    created_at: datetime
    buyer_name: Optional[str] = None

    class Config:
        from_attributes = True

class BuyerRatingCreate(BaseModel):
    buyer_id: int
    rating: int = Field(ge=1, le=5)
    review: Optional[str] = None

class BuyerRatingOut(BaseModel):
    id: int
    buyer_id: int
    farmer_id: int
    rating: int
    review: Optional[str]
    created_at: datetime
    farmer_name: Optional[str] = None

    class Config:
        from_attributes = True

class SiteSettingBase(BaseModel):
    key: str
    value: Optional[str] = None

class SiteSettingOut(SiteSettingBase):
    id: int
    updated_at: datetime

class FeatureCardCreate(BaseModel):
    icon: str = "fas fa-star"
    title: str
    description: str
    order: Optional[int] = 0

class FeatureCardOut(FeatureCardCreate):
    id: int

class GalleryImageCreate(BaseModel):
    url: str
    alt: Optional[str] = None
    order: Optional[int] = 0

class GalleryImageOut(GalleryImageCreate):
    id: int

class DashboardSettingUpdate(BaseModel):
    visible: bool
    order: Optional[int] = 0

class SectorOut(BaseModel):
    id: int
    name: str
    category: str
