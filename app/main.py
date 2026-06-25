from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import os, csv, io, json, re
from datetime import timedelta
from dotenv import load_dotenv

from app.database import engine, Base, get_db
from app.models import *
from app.schemas import *
from app.auth import *
from app.i18n import I18nMiddleware, get_translations, get_lang

# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

app = FastAPI(title="FarmGate-UG Pro", description="Connecting Farmers & Buyers Globally")

# Add i18n middleware
app.add_middleware(I18nMiddleware)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---- Jinja2 globals for i18n (using pass_context) ----
from jinja2 import pass_context

@pass_context
def _jinja_global_translate(context, text):
    request = context.get('request')
    if request:
        translations = get_translations(request)
        return translations.get(text, text)
    return text

def _jinja_global_lang(request: Request):
    return get_lang(request)

templates.env.globals['_'] = _jinja_global_translate
templates.env.globals['lang'] = _jinja_global_lang

# ---- Helper ----
def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    return setting.value if setting else default

# ---- Districts list (136 districts from image) - SORTED A-Z ----
DISTRICTS = sorted([
    "Koboko", "Maracha", "Arua", "Zombo", "Nebbi", "Pakwach", "Madi Okollo", "Terego",
    "Yumbe", "Moyo", "Obongi", "Adjumani", "Amuru", "Nwoya", "Omoro", "Gulu", "Lamwo",
    "Kitgum", "Karenga", "Kaabong", "Kotido", "Moroto", "Amudat", "Nakapiripirit",
    "Nabilatuk", "Napak", "Pader", "Otuke", "Akurana", "Okuloe", "Alebit", "Lira",
    "Kole", "Oyam", "Apac", "Kwania", "Dokolo", "Amolatar", "Kaberamaido", "Kalaki",
    "Soroti", "Amuria", "Kapelebyong", "Katakwi", "Kumi", "Bukedea", "Bulambuli",
    "Kapchorwa", "Kween", "Bukwo", "Sironko", "Bududa", "Namisindwa", "Manafwa",
    "Tororo", "Busia", "Nanyingo", "Bugiri", "Mayuge", "Bugweri", "Namutumba",
    "Budaleja", "Mbale", "Budaka", "Butebo", "Kibuku", "Pallisa", "Ngora", "Serere",
    "Buyende", "Kaliro", "Iganga", "Luka", "Jini", "Kamuli", "Kayunga", "Bukwe",
    "Buvuma", "Mukono", "Kamapia", "Wakiso", "Mpigi", "Kalangala", "Masaka",
    "Kyotera", "Rakai", "Lwengo", "Lyantonde", "Sembabule", "Bukomansimbi",
    "Kalungu", "Butambala", "Gomba", "Mbende", "Kasanda", "Mityana", "Kiboga",
    "Kyankwanzi", "Nakaseke", "Luwero", "Nakasongola", "Kirangondo", "Masindi",
    "Bullisa", "Hoima", "Kikuube", "Kakumiro", "Kibaale", "Kagadi", "Ntoroko",
    "Bundibugyo", "Bunyangabu", "Kabarole", "Kyenjogo", "Kwegyega", "Kamwenge",
    "Kazo", "Ibanda", "Kitagwenda", "Kasebe", "Rubirizi", "Bushenyi", "Mbamra",
    "Nkomo", "Mbarara", "Kiruhura", "Isingiro", "Rwampara", "Ntungamo", "Mitooma",
    "Rukungiri", "Kanungu", "Kisoro", "Rubanda", "Rukiga", "Kabale"
])

# ---- Startup event (deferred table creation) ----
@app.on_event("startup")
def startup():
    from app.database import engine
    from app.models import Base
    Base.metadata.create_all(bind=engine)

# ---------- AUTH ----------
@app.post("/api/auth/register", response_model=dict)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.phone == user.phone) | ((User.email == user.email) & (user.email is not None))
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone or email already registered")
    
    if not re.match(r'^\+?[0-9]{7,15}$', user.phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    hashed = get_password_hash(user.password)
    new_user = User(
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        password_hash=hashed,
        role=user.role,
        is_approved=False
    )
    
    if user.role == UserRole.FARMER:
        new_user.district = user.district
        new_user.village = user.village
        new_user.sector_id = user.sector_id
    elif user.role == UserRole.BUYER:
        new_user.country = user.country
        new_user.company = user.company
        new_user.buyer_sector = user.buyer_sector
        new_user.is_approved = True   # Auto-approve buyers
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Registration successful. Awaiting admin approval." if user.role == UserRole.FARMER else "Registration successful. You can now log in."}

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    if user.role != UserRole.ADMIN and not user.is_approved:
        raise HTTPException(status_code=403, detail="Your account is pending approval. Please wait.")

    access_token = create_access_token(data={"sub": str(user.id)})
    user_out = UserOut.model_validate(user)
    if user.sector:
        user_out.sector_name = user.sector.name

    # Secure cookie: set to True only if running on Render (HTTPS)
    secure_cookie = True if os.getenv("RENDER") else False

    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_out.model_dump(mode='json')
    })
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure_cookie,   # True in production, False locally
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    return response

# ---------- SECTORS API ----------
@app.get("/api/sectors", response_model=List[SectorOut])
async def get_sectors(db: Session = Depends(get_db)):
    return db.query(Sector).order_by(Sector.category, Sector.name).all()

# ---------- FARMER ----------
@app.get("/api/farmers/my-products", response_model=List[ProductOut])
async def my_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can access")
    products = db.query(Product).filter(Product.farmer_id == current_user.id).all()
    return products

@app.post("/api/farmers/products", response_model=dict)
async def create_product(
    name: str = Form(...),
    category: str = Form(...),
    subcategory: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    currency: Optional[str] = Form("UGX"),
    quantity: Optional[str] = Form(None),
    unit: Optional[str] = Form("kg"),
    is_international: bool = Form(False),
    shipping_info: Optional[str] = Form(None),
    photo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can add products")
    photo_url = None
    if photo and photo.filename:
        photo_url = f"https://via.placeholder.com/200?text={name.replace(' ', '+')}"
    new_product = Product(
        farmer_id=current_user.id,
        name=name,
        category=category,
        subcategory=subcategory,
        description=description,
        price=price,
        currency=currency,
        quantity=quantity,
        unit=unit,
        photo_url=photo_url,
        is_international=is_international,
        shipping_info=shipping_info
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"id": new_product.id, "message": "Product added successfully"}

@app.delete("/api/farmers/products/{product_id}")
async def delete_product(product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can delete products")
    product = db.query(Product).filter(Product.id == product_id, Product.farmer_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}

@app.get("/api/farmers/interests", response_model=List[InterestOut])
async def farmer_interests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can view interests")
    interests = db.query(Interest).filter(Interest.farmer_id == current_user.id).order_by(Interest.created_at.desc()).all()
    for i in interests:
        product = db.query(Product).filter(Product.id == i.product_id).first()
        if product:
            i.product_name = product.name
    return interests

@app.put("/api/farmers/interests/{interest_id}/status")
async def update_interest_status(
    interest_id: int, 
    status: str,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can update interest status")
    interest = db.query(Interest).filter(Interest.id == interest_id, Interest.farmer_id == current_user.id).first()
    if not interest:
        raise HTTPException(status_code=404, detail="Interest not found")
    if status not in ["pending", "contacted", "closed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    interest.status = status
    db.commit()
    return {"message": f"Status updated to {status}"}

# ---------- BUYER ----------
@app.get("/api/buyers/farmers", response_model=List[UserOut])
async def search_farmers(
    district: Optional[str] = None,
    product_category: Optional[str] = None,
    country: Optional[str] = None,
    min_rating: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(User).filter(User.role == UserRole.FARMER, User.is_approved == True)
    if district:
        query = query.filter(User.district == district)
    if product_category:
        query = query.join(Product).filter(Product.category == product_category)
    if country:
        query = query.join(Product).join(InternationalListing).filter(InternationalListing.target_countries.contains(country))
    if min_rating:
        query = query.filter(User.average_rating >= min_rating)
    farmers = query.distinct().all()
    result = []
    for f in farmers:
        out = UserOut.model_validate(f)
        if f.sector:
            out.sector_name = f.sector.name
        result.append(out)
    return result

@app.post("/api/buyers/interest", response_model=dict)
async def express_interest(
    interest: InterestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Only buyers can express interest")
    product = db.query(Product).filter(Product.id == interest.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    farmer = db.query(User).filter(User.id == product.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    existing = db.query(Interest).filter(
        Interest.product_id == product.id,
        Interest.buyer_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already expressed interest in this product")
    new_interest = Interest(
        product_id=product.id,
        farmer_id=farmer.id,
        buyer_id=current_user.id,
        buyer_name=current_user.full_name,
        buyer_phone=current_user.phone,
        buyer_email=current_user.email,
        buyer_company=current_user.company,
        buyer_country=current_user.country,
        message=interest.message
    )
    db.add(new_interest)
    db.commit()
    notif = Notification(
        user_id=farmer.id,
        type="message",
        title="New interest in your product",
        message=f"{current_user.full_name} from {current_user.country or 'Uganda'} showed interest in: {product.name}"
    )
    db.add(notif)
    db.commit()
    return {"message": "Interest expressed successfully"}

@app.get("/api/buyers/my-interests", response_model=List[InterestOut])
async def my_interests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Only buyers can view their interests")
    interests = db.query(Interest).filter(Interest.buyer_id == current_user.id).order_by(Interest.created_at.desc()).all()
    for i in interests:
        product = db.query(Product).filter(Product.id == i.product_id).first()
        if product:
            i.product_name = product.name
    return interests

# ---------- RATINGS (FARMER) ----------
@app.post("/api/ratings", response_model=dict)
async def rate_farmer(
    rating_data: FarmerRatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Only buyers can rate farmers")
    farmer = db.query(User).filter(User.id == rating_data.farmer_id, User.role == UserRole.FARMER).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    interest = db.query(Interest).filter(
        Interest.farmer_id == farmer.id,
        Interest.buyer_id == current_user.id
    ).first()
    if not interest:
        raise HTTPException(status_code=403, detail="You can only rate farmers you have interacted with")
    existing = db.query(FarmerRating).filter(
        FarmerRating.farmer_id == farmer.id,
        FarmerRating.buyer_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already rated this farmer")
    new_rating = FarmerRating(
        farmer_id=farmer.id,
        buyer_id=current_user.id,
        rating=rating_data.rating,
        review=rating_data.review
    )
    db.add(new_rating)
    avg_rating = db.query(func.avg(FarmerRating.rating)).filter(FarmerRating.farmer_id == farmer.id).scalar()
    total_ratings = db.query(func.count(FarmerRating.id)).filter(FarmerRating.farmer_id == farmer.id).scalar()
    farmer.average_rating = round(avg_rating or 0, 1)
    farmer.total_ratings = total_ratings or 0
    db.commit()
    return {"message": "Rating submitted successfully"}

@app.get("/api/ratings/farmer/{farmer_id}", response_model=dict)
async def get_farmer_ratings(farmer_id: int, db: Session = Depends(get_db)):
    farmer = db.query(User).filter(User.id == farmer_id, User.role == UserRole.FARMER).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    ratings = db.query(FarmerRating).filter(FarmerRating.farmer_id == farmer_id).order_by(FarmerRating.created_at.desc()).all()
    result = []
    for r in ratings:
        buyer = db.query(User).filter(User.id == r.buyer_id).first()
        result.append({
            "id": r.id,
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at,
            "buyer_name": buyer.full_name if buyer else "Anonymous"
        })
    return {
        "average_rating": farmer.average_rating,
        "total_ratings": farmer.total_ratings,
        "ratings": result
    }

# ---------- RATINGS (BUYER) ----------
@app.post("/api/ratings/buyer", response_model=dict)
async def rate_buyer(
    rating_data: BuyerRatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can rate buyers")
    
    buyer = db.query(User).filter(User.id == rating_data.buyer_id, User.role == UserRole.BUYER).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    interest = db.query(Interest).filter(
        Interest.farmer_id == current_user.id,
        Interest.buyer_id == buyer.id
    ).first()
    if not interest:
        raise HTTPException(status_code=403, detail="You can only rate buyers you have interacted with")
    
    existing = db.query(BuyerRating).filter(
        BuyerRating.buyer_id == buyer.id,
        BuyerRating.farmer_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already rated this buyer")
    
    new_rating = BuyerRating(
        buyer_id=buyer.id,
        farmer_id=current_user.id,
        rating=rating_data.rating,
        review=rating_data.review
    )
    db.add(new_rating)
    db.commit()
    return {"message": "Buyer rating submitted successfully"}

@app.get("/api/ratings/buyer/{buyer_id}", response_model=dict)
async def get_buyer_ratings(buyer_id: int, db: Session = Depends(get_db)):
    buyer = db.query(User).filter(User.id == buyer_id, User.role == UserRole.BUYER).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    ratings = db.query(BuyerRating).filter(BuyerRating.buyer_id == buyer_id).order_by(BuyerRating.created_at.desc()).all()
    result = []
    for r in ratings:
        farmer = db.query(User).filter(User.id == r.farmer_id).first()
        result.append({
            "id": r.id,
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at,
            "farmer_name": farmer.full_name if farmer else "Anonymous"
        })
    avg = db.query(func.avg(BuyerRating.rating)).filter(BuyerRating.buyer_id == buyer_id).scalar()
    total = db.query(func.count(BuyerRating.id)).filter(BuyerRating.buyer_id == buyer_id).scalar()
    return {
        "average_rating": round(avg or 0, 1),
        "total_ratings": total or 0,
        "ratings": result
    }

# ---------- NOTIFICATIONS ----------
@app.get("/api/notifications", response_model=List[NotificationOut])
async def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return notifs

@app.put("/api/notifications/{notif_id}/read")
async def mark_read(notif_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Not found")
    notif.is_read = True
    db.commit()
    return {"message": "Marked as read"}

# ---------- ADMIN ----------
@app.get("/api/admin/pending-users", response_model=List[UserOut])
async def pending_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).filter(
        User.role == UserRole.FARMER,
        User.is_approved == False
    ).order_by(User.created_at.desc()).all()
    return users

@app.put("/api/admin/approve-user/{user_id}")
async def approve_user(user_id: int, data: ApproveFarmer, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = data.approve
    db.commit()
    title = "Approved" if data.approve else "Rejected"
    message = "Your account has been approved! You can now log in." if data.approve else "Your account was rejected. Please contact support."
    notif = Notification(
        user_id=user_id,
        type="approval",
        title=title,
        message=message
    )
    db.add(notif)
    db.commit()
    return {"message": f"User { 'approved' if data.approve else 'rejected' }"}

@app.get("/api/admin/users", response_model=List[UserOut])
async def all_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users

@app.get("/api/admin/dashboard-stats")
async def admin_stats(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_farmers = db.query(User).filter(User.role == UserRole.FARMER).count()
    total_buyers = db.query(User).filter(User.role == UserRole.BUYER).count()
    pending_users = db.query(User).filter(User.role == UserRole.FARMER, User.is_approved == False).count()
    total_products = db.query(Product).count()
    total_interests = db.query(Interest).count()
    return {
        "total_users": total_users,
        "total_farmers": total_farmers,
        "total_buyers": total_buyers,
        "pending_users": pending_users,
        "total_products": total_products,
        "total_interests": total_interests
    }

@app.get("/api/admin/interests/export-csv")
async def export_interests_csv(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(Interest, Product, User).join(Product, Interest.product_id == Product.id).join(User, Product.farmer_id == User.id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No data")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Buyer Name", "Buyer Phone", "Buyer Email", "Company", "Country", "Message", "Date", "Product", "Farmer", "Farmer Phone", "Status"])
    for interest, product, user in rows:
        writer.writerow([
            interest.buyer_name,
            interest.buyer_phone,
            interest.buyer_email or "",
            interest.buyer_company or "",
            interest.buyer_country or "",
            interest.message or "",
            interest.created_at.strftime("%Y-%m-%d %H:%M"),
            product.name,
            user.full_name,
            user.phone,
            interest.status
        ])
    response = JSONResponse(content=output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=farmgate_interests.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# ---------- SETTINGS API ----------
@app.get("/api/admin/settings", response_model=dict)
async def get_all_settings(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    settings = db.query(SiteSetting).all()
    return {s.key: s.value for s in settings}

@app.put("/api/admin/settings/{key}")
async def update_setting(key: str, value: str, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if not setting:
        setting = SiteSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
    return {"message": "Setting updated"}

@app.get("/api/admin/features", response_model=List[FeatureCardOut])
async def get_features(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(FeatureCard).order_by(FeatureCard.order).all()

@app.post("/api/admin/features", response_model=FeatureCardOut)
async def create_feature(feature: FeatureCardCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    new_feature = FeatureCard(**feature.dict())
    db.add(new_feature)
    db.commit()
    db.refresh(new_feature)
    return new_feature

@app.put("/api/admin/features/{feature_id}")
async def update_feature(feature_id: int, feature: FeatureCardCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    db_feature = db.query(FeatureCard).filter(FeatureCard.id == feature_id).first()
    if not db_feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    for key, val in feature.dict().items():
        setattr(db_feature, key, val)
    db.commit()
    db.refresh(db_feature)
    return db_feature

@app.delete("/api/admin/features/{feature_id}")
async def delete_feature(feature_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    db_feature = db.query(FeatureCard).filter(FeatureCard.id == feature_id).first()
    if not db_feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    db.delete(db_feature)
    db.commit()
    return {"message": "Feature deleted"}

@app.get("/api/admin/gallery", response_model=List[GalleryImageOut])
async def get_gallery(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(GalleryImage).order_by(GalleryImage.order).all()

@app.post("/api/admin/gallery", response_model=GalleryImageOut)
async def add_gallery_image(img: GalleryImageCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    new_img = GalleryImage(**img.dict())
    db.add(new_img)
    db.commit()
    db.refresh(new_img)
    return new_img

@app.put("/api/admin/gallery/{img_id}")
async def update_gallery_image(img_id: int, img: GalleryImageCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    db_img = db.query(GalleryImage).filter(GalleryImage.id == img_id).first()
    if not db_img:
        raise HTTPException(status_code=404, detail="Image not found")
    db_img.url = img.url
    db_img.alt = img.alt
    db_img.order = img.order
    db.commit()
    db.refresh(db_img)
    return db_img

@app.delete("/api/admin/gallery/{img_id}")
async def delete_gallery_image(img_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    db_img = db.query(GalleryImage).filter(GalleryImage.id == img_id).first()
    if not db_img:
        raise HTTPException(status_code=404, detail="Image not found")
    db.delete(db_img)
    db.commit()
    return {"message": "Image deleted"}

@app.get("/api/admin/dashboard-settings/{role}")
async def get_dashboard_settings(role: str, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    settings = db.query(DashboardSetting).filter(DashboardSetting.role == role).order_by(DashboardSetting.order).all()
    return settings

@app.put("/api/admin/dashboard-settings/{setting_id}")
async def update_dashboard_setting(setting_id: int, data: DashboardSettingUpdate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    setting = db.query(DashboardSetting).filter(DashboardSetting.id == setting_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    setting.visible = data.visible
    if data.order is not None:
        setting.order = data.order
    db.commit()
    return {"message": "Dashboard setting updated"}

# ---------- PAGES ----------
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request, db: Session = Depends(get_db)):
    settings = {s.key: s.value for s in db.query(SiteSetting).all()}
    features = db.query(FeatureCard).order_by(FeatureCard.order).all()
    gallery = db.query(GalleryImage).order_by(GalleryImage.order).all()
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "settings": settings,
        "features": features,
        "gallery": gallery,
        "whatsapp": settings.get("whatsapp_number", "+256771511410")
    })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    sectors = db.query(Sector).order_by(Sector.category, Sector.name).all()
    countries = [
        "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
        "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas, The",
        "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin",
        "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria",
        "Burkina Faso", "Burma", "Burundi", "Cabo Verde", "Cambodia", "Cameroon",
        "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia",
        "Comoros", "Costa Rica", "Cote d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czechia",
        "Democratic Republic of the Congo", "Denmark", "Djibouti", "Dominica",
        "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea",
        "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France",
        "Gabon", "Gambia, The", "Georgia", "Germany", "Ghana", "Greece", "Grenada",
        "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras",
        "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel",
        "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
        "Korea", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon",
        "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
        "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands",
        "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco",
        "Mongolia", "Montenegro", "Morocco", "Mozambique", "Namibia", "Nauru",
        "Nepal", "Netherlands, The", "New Zealand", "Nicaragua", "Niger", "Nigeria",
        "Niue", "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Panama",
        "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
        "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia",
        "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe",
        "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore",
        "Slovakia", "Slovenia", "Solomon Islands, The", "Somalia", "South Africa",
        "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland",
        "Syria", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga",
        "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda",
        "Ukraine", "United Arab Emirates, The", "United Kingdom, The", "Uruguay",
        "Uzbekistan", "Vanuatu", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
    ]
    return templates.TemplateResponse("register.html", {
        "request": request,
        "districts": DISTRICTS,
        "sectors": sectors,
        "countries": countries
    })

@app.get("/login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/cyber/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.get("/farmer-dashboard", response_class=HTMLResponse)
async def farmer_dashboard(request: Request, db: Session = Depends(get_db)):
    settings = {s.key: s.value for s in db.query(SiteSetting).all()}
    return templates.TemplateResponse("farmer_dashboard.html", {"request": request, "settings": settings, "districts": DISTRICTS})

@app.get("/buyer-dashboard", response_class=HTMLResponse)
async def buyer_dashboard(request: Request, db: Session = Depends(get_db)):
    settings = {s.key: s.value for s in db.query(SiteSetting).all()}
    return templates.TemplateResponse("buyer_dashboard.html", {"request": request, "settings": settings, "districts": DISTRICTS})

@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    settings = {s.key: s.value for s in db.query(SiteSetting).all()}
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "settings": settings})

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    settings = {s.key: s.value for s in db.query(SiteSetting).all()}
    return templates.TemplateResponse("admin_settings.html", {"request": request, "settings": settings})

# ---------- LANGUAGE SWITCHER ----------
@app.get("/set-language/{lang}")
async def set_language(lang: str, request: Request):
    supported = ['en', 'lg']
    if lang not in supported:
        lang = 'en'
    # Redirect back to the previous page or home
    referer = request.headers.get("referer") or "/"
    response = RedirectResponse(url=referer, status_code=302)
    response.set_cookie(key="lang", value=lang, max_age=60*60*24*30, path="/")
    return response

@app.get("/sitemap.xml", response_class=PlainTextResponse)
async def sitemap():
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://farmgate.ug/</loc><priority>1.0</priority></url>
  <url><loc>https://farmgate.ug/register</loc><priority>0.8</priority></url>
  <url><loc>https://farmgate.ug/login</loc><priority>0.8</priority></url>
  <url><loc>https://farmgate.ug/farmer-dashboard</loc><priority>0.6</priority></url>
  <url><loc>https://farmgate.ug/buyer-dashboard</loc><priority>0.6</priority></url>
</urlset>"""

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return """User-agent: *
Allow: /
Sitemap: https://farmgate.ug/sitemap.xml"""

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please try again later."}
    )
