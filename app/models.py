from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, DECIMAL, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FARMER = "farmer"
    BUYER = "buyer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.FARMER)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Farmer fields – simplified
    district = Column(String(100))
    village = Column(String(100))
    sector_id = Column(Integer, ForeignKey("sectors.id", ondelete="SET NULL"), nullable=True)
    
    # Buyer fields
    country = Column(String(100))
    company = Column(String(255))
    buyer_sector = Column(String(50))
    
    # Rating stats
    average_rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    
    # Relationships
    sector = relationship("Sector")
    products = relationship("Product", back_populates="farmer")
    notifications = relationship("Notification", back_populates="user")
    interests_made = relationship("Interest", foreign_keys="Interest.buyer_id", back_populates="buyer")
    interests_received = relationship("Interest", foreign_keys="Interest.farmer_id", back_populates="farmer")
    ratings_received = relationship("FarmerRating", foreign_keys="FarmerRating.farmer_id", back_populates="farmer")
    ratings_given = relationship("FarmerRating", foreign_keys="FarmerRating.buyer_id", back_populates="buyer")
    buyer_ratings_received = relationship("BuyerRating", foreign_keys="BuyerRating.buyer_id", back_populates="buyer")
    buyer_ratings_given = relationship("BuyerRating", foreign_keys="BuyerRating.farmer_id", back_populates="farmer")

class Sector(Base):
    __tablename__ = "sectors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)

class FarmerRating(Base):
    __tablename__ = "farmer_ratings"
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    farmer = relationship("User", foreign_keys=[farmer_id], back_populates="ratings_received")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="ratings_given")

class BuyerRating(Base):
    __tablename__ = "buyer_ratings"
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="buyer_ratings_received")
    farmer = relationship("User", foreign_keys=[farmer_id], back_populates="buyer_ratings_given")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(50))
    description = Column(Text)
    price = Column(DECIMAL(10,2))
    currency = Column(String(10), default="UGX")
    quantity = Column(String(100))
    unit = Column(String(20), default="kg")
    photo_url = Column(Text)
    is_international = Column(Boolean, default=False)
    shipping_info = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("User", back_populates="products")
    international_listings = relationship("InternationalListing", back_populates="product")
    interests = relationship("Interest", back_populates="product")

class InternationalListing(Base):
    __tablename__ = "international_listings"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    target_countries = Column(Text)
    shipping_cost = Column(DECIMAL(10,2))
    estimated_delivery_days = Column(Integer)
    currency = Column(String(10), default="USD")
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="international_listings")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    type = Column(String(50))
    title = Column(String(255))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")

class Interest(Base):
    __tablename__ = "interests"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    buyer_name = Column(String(255), nullable=False)
    buyer_phone = Column(String(20), nullable=False)
    buyer_email = Column(String(255))
    buyer_company = Column(String(255))
    buyer_country = Column(String(100))
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="pending")

    product = relationship("Product", back_populates="interests")
    farmer = relationship("User", foreign_keys=[farmer_id], back_populates="interests_received")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="interests_made")

class SiteSetting(Base):
    __tablename__ = "site_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class FeatureCard(Base):
    __tablename__ = "feature_cards"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String(50), default="fas fa-star")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    order = Column(Integer, default=0)

class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    alt = Column(String(255))
    order = Column(Integer, default=0)

class DashboardSetting(Base):
    __tablename__ = "dashboard_settings"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)
    section = Column(String(50), nullable=False)
    visible = Column(Boolean, default=True)
    order = Column(Integer, default=0)
