import sys
import os
from app.database import SessionLocal, engine, Base
from app.models import *
from app.auth import get_password_hash

def seed_sectors():
    sectors = [
        ("Maize", "Crop Production"), ("Rice", "Crop Production"), ("Sorghum", "Crop Production"),
        ("Millet", "Crop Production"), ("Beans", "Crop Production"), ("Groundnuts", "Crop Production"),
        ("Cowpeas", "Crop Production"), ("Soybeans", "Crop Production"), ("Cassava", "Crop Production"),
        ("Sweet Potatoes", "Crop Production"), ("Irish Potatoes", "Crop Production"), ("Tomatoes", "Crop Production"),
        ("Onions", "Crop Production"), ("Cabbage", "Crop Production"), ("Hot Pepper", "Crop Production"),
        ("Sukuma Wiki (Kale)", "Crop Production"), ("Spinach", "Crop Production"), ("Bananas", "Crop Production"),
        ("Mangoes", "Crop Production"), ("Oranges", "Crop Production"), ("Pineapples", "Crop Production"),
        ("Passion Fruit", "Crop Production"), ("Watermelons", "Crop Production"), ("Avocados", "Crop Production"),
        ("Papaya", "Crop Production"), ("Coffee", "Cash Crops"), ("Tea", "Cash Crops"),
        ("Cotton", "Cash Crops"), ("Sugarcane", "Cash Crops"), ("Tobacco", "Cash Crops"),
        ("Cocoa", "Cash Crops"), ("Sunflower", "Oilseeds"), ("Simsim (Sesame)", "Oilseeds"),
        ("Palm Oil", "Oilseeds"), ("Ginger", "Spices & Herbs"), ("Turmeric", "Spices & Herbs"),
        ("Vanilla", "Spices & Herbs"), ("Pepper", "Spices & Herbs"), ("Roses", "Floriculture"),
        ("Cut Flowers", "Floriculture"), ("Dairy Cattle", "Livestock"), ("Beef Cattle", "Livestock"),
        ("Broilers (Meat)", "Livestock"), ("Layers (Eggs)", "Livestock"), ("Indigenous Poultry", "Livestock"),
        ("Goats", "Livestock"), ("Sheep", "Livestock"), ("Pigs", "Livestock"),
        ("Beekeeping (Honey)", "Livestock"), ("Rabbit Rearing", "Livestock"),
        ("Tilapia Farming", "Aquaculture"), ("Catfish Farming", "Aquaculture"),
        ("Mudfish Farming", "Aquaculture"), ("Fish Feed Production", "Aquaculture"),
        ("Maize Milling", "Agro-processing"), ("Rice Milling", "Agro-processing"),
        ("Oil Extraction", "Agro-processing"), ("Juice Processing", "Agro-processing"),
        ("Dairy Processing", "Agro-processing"), ("Meat Processing", "Agro-processing"),
        ("Coffee Processing", "Agro-processing"), ("Tea Processing", "Agro-processing"),
        ("Cotton Ginning", "Agro-processing"), ("Sugar Refining", "Agro-processing"),
        ("Timber Plantation", "Forestry"), ("Agroforestry", "Forestry"), ("Eco-tourism", "Forestry"),
        ("Organic Crop Production", "Organic Farming"), ("Organic Livestock", "Organic Farming"),
        ("Permaculture", "Organic Farming"), ("Conservation Agriculture", "Organic Farming"),
        ("Hydroponics", "Other"), ("Mushroom Cultivation", "Other"),
        ("Sericulture (Silkworm)", "Other"), ("Medicinal Plant Farming", "Other"),
    ]
    db = SessionLocal()
    db.query(Sector).delete()
    for name, category in sectors:
        db.add(Sector(name=name, category=category))
    db.commit()
    print(f"Seeded {len(sectors)} agricultural sectors.")
    db.close()

def seed_admin():
    db = SessionLocal()
    admin = db.query(User).filter(User.phone == "+96560046249").first()
    if not admin:
        admin = User(
            phone="+96560046249",
            email="admin@farmgate.ug",
            password_hash=get_password_hash("Junior"),
            full_name="Admin",
            role=UserRole.ADMIN,
            is_approved=True
        )
        db.add(admin)

    default_settings = [
        ("hero_title", "FarmGate.ug"),
        ("hero_subtitle", "Connect directly with farmers. No middlemen."),
        ("hero_cta", "Get Started – Free"),
        ("hero_background_image", "https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=1600&h=800&fit=crop"),
        ("hero_background_video", ""),
        ("hero_video_embed", ""),
        ("about_text", "FarmGate.ug is Uganda's premier digital marketplace connecting farmers directly with buyers – from local traders to international factories."),
        ("about_image", "https://images.unsplash.com/photo-1546443310-6a8a9f4c7a8e?w=600&h=400&fit=crop"),
        ("about_video", ""),
        ("cta_title", "Ready to Connect?"),
        ("cta_text", "Join the fastest growing agricultural marketplace in Uganda."),
        ("cta_button_text", "Register Now – Free"),
        ("footer_copyright", "© 2026 FarmGate.ug. All rights reserved."),
        ("footer_facebook", "#"),
        ("footer_twitter", "#"),
        ("footer_instagram", "#"),
        ("whatsapp_number", "+256771511410"),
        ("dashboard_farmer_welcome", "Welcome to your farmer dashboard. Manage your products and track buyer interests."),
        ("dashboard_buyer_welcome", "Welcome to your buyer dashboard. Search for farmers and express interest."),
    ]
    for key, val in default_settings:
        setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if not setting:
            db.add(SiteSetting(key=key, value=val))
        else:
            setting.value = val

    features = [
        ("fas fa-user-plus", "Free Registration", "Farmers and buyers sign up for free."),
        ("fas fa-handshake", "Direct Connections", "Buyers contact farmers directly via WhatsApp."),
        ("fas fa-globe", "International Reach", "List products for global buyers."),
        ("fas fa-star", "Trust & Transparency", "Rate farmers based on your experience."),
        ("fas fa-tractor", "All Agricultural Products", "Crops, livestock, poultry, fish, and more."),
        ("fas fa-chart-line", "Market Insights", "Stay informed about market prices.")
    ]
    for i, (icon, title, desc) in enumerate(features):
        if not db.query(FeatureCard).filter(FeatureCard.title == title).first():
            db.add(FeatureCard(icon=icon, title=title, description=desc, order=i))

    gallery = [
        ("https://images.unsplash.com/photo-1546443310-6a8a9f4c7a8e?w=400&h=300&fit=crop&crop=center", "Cattle"),
        ("https://images.unsplash.com/photo-1628037668369-ccb82f04c1f1?w=400&h=300&fit=crop&crop=center", "Vegetables"),
        ("https://images.unsplash.com/photo-1595428462458-5b45b8cb3a45?w=400&h=300&fit=crop&crop=center", "Matooke"),
        ("https://images.unsplash.com/photo-1592921870789-04563d5507f3?w=400&h=300&fit=crop&crop=center", "Goat"),
        ("https://images.unsplash.com/photo-1585659722983-3a675dabf23d?w=400&h=300&fit=crop&crop=center", "Chicken"),
        ("https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=400&h=300&fit=crop&crop=center", "Coffee"),
        ("https://images.unsplash.com/photo-1559757175-0c4f68b4c184?w=400&h=300&fit=crop&crop=center", "Market"),
        ("https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=400&h=300&fit=crop&crop=center", "Farm")
    ]
    for i, (url, alt) in enumerate(gallery):
        if not db.query(GalleryImage).filter(GalleryImage.url == url).first():
            db.add(GalleryImage(url=url, alt=alt, order=i))

    for role in ["farmer", "buyer"]:
        sections = ["products", "interests", "notifications", "search"] if role == "buyer" else ["products", "interests", "notifications", "ratings"]
        for i, sec in enumerate(sections):
            if not db.query(DashboardSetting).filter(DashboardSetting.role == role, DashboardSetting.section == sec).first():
                db.add(DashboardSetting(role=role, section=sec, visible=True, order=i))

    db.commit()
    print("Admin and default settings seeded.")
    db.close()

def seed_all():
    print("Seeding database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_sectors()
    seed_admin()
    print("\n" + "="*50)
    print("Database seeded successfully!")
    print("\nAdmin Credentials:")
    print("   Phone: +96560046249")
    print("   Password: Junior")
    print("="*50)

if __name__ == "__main__":
    seed_all()
