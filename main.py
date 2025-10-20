from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi.responses import Response, StreamingResponse
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests

load_dotenv()

app = FastAPI(title="Uy Ijara API", description="Uy-joy ijarasi uchun API")

# CORS sozlamalari (frontend uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://asadbek669.github.io",  # To‘g‘ri
        "https://asadbek669.github.io/uy-ijara-xaritasi",  # Bu ham kerak
        "http://localhost:3000",  # Local test uchun
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Ma'lumotlar bazasi ulanishi
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Response modellari - database.py dagi haqiqiy ustun nomlariga mos
class ListingResponse(BaseModel):
    id: int
    title: str
    description: str
    total_floors: int
    floor_number: int
    price: float
    address: str
    latitude: float
    longitude: float
    photos: List[str]
    is_active: bool
    created_at: datetime
    owner_name: str

@app.get("/")
async def root():
    return {"message": "Uy Ijara API ishlamoqda"}

@app.get("/api/listings", response_model=List[ListingResponse])
async def get_active_listings():
    """Barcha faol e'lonlarni olish (frontend xarita uchun)"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # database.py dagi haqiqiy ustun nomlari bilan so'rov
        cur.execute("""
            SELECT 
                l.id, l.title, l.description, l.total_floors, l.floor_number,
                l.price, l.address, l.latitude, l.longitude, l.photos,
                l.is_active, l.created_at, u.full_name as owner_name
            FROM listings l 
            JOIN users u ON l.user_id = u.id 
            WHERE l.is_active = true
            ORDER BY l.created_at DESC
        """)
        
        listings = cur.fetchall()
        
        result = []
        for listing in listings:
            # photos ni to'g'ri ishlash
            photos = listing[9] if listing[9] else []
            if isinstance(photos, str):
                photos = [photos]
            
            result.append(ListingResponse(
                id=listing[0],
                title=listing[1],
                description=listing[2],
                total_floors=listing[3],
                floor_number=listing[4],
                price=float(listing[5]),
                address=listing[6],
                latitude=float(listing[7]),
                longitude=float(listing[8]),
                photos=photos,
                is_active=listing[10],
                created_at=listing[11],
                owner_name=listing[12]
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server xatosi: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()




# main.py ga qo'shing
@app.get("/api/listings/{listing_id}/telegram")
async def get_listing_telegram_info(listing_id: int):
    """E'lon ma'lumotlarini Telegram uchun olish"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                l.id, l.title, l.description, l.total_floors, l.floor_number,
                l.price, l.address, l.latitude, l.longitude, l.photos,
                l.is_active, l.created_at, u.full_name as owner_name
            FROM listings l 
            JOIN users u ON l.user_id = u.id 
            WHERE l.id = %s
        """, (listing_id,))
        
        listing = cur.fetchone()
        
        if not listing:
            raise HTTPException(status_code=404, detail="E'lon topilmadi")
        
        photos = listing[9] if listing[9] else []
        if isinstance(photos, str):
            photos = [photos]
        
        return {
            "id": listing[0],
            "title": listing[1],
            "description": listing[2],
            "total_floors": listing[3],
            "floor_number": listing[4],
            "price": float(listing[5]),
            "address": listing[6],
            "latitude": float(listing[7]),
            "longitude": float(listing[8]),
            "photos": photos,
            "is_active": listing[10],
            "created_at": listing[11],
            "owner_name": listing[12],
            "telegram_url": f"https://t.me/testuchun878_bot?start=listing_{listing_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server xatosi: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.get("/api/listings/{listing_id}", response_model=ListingResponse)
async def get_listing_by_id(listing_id: int):
    """ID bo'yicha e'lon ma'lumotlarini olish"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                l.id, l.title, l.description, l.total_floors, l.floor_number,
                l.price, l.address, l.latitude, l.longitude, l.photos,
                l.is_active, l.created_at, u.full_name as owner_name
            FROM listings l 
            JOIN users u ON l.user_id = u.id 
            WHERE l.id = %s
        """, (listing_id,))
        
        listing = cur.fetchone()
        
        if not listing:
            raise HTTPException(status_code=404, detail="E'lon topilmadi")
        
        # photos ni to'g'ri ishlash
        photos = listing[9] if listing[9] else []
        if isinstance(photos, str):
            photos = [photos]
        
        return ListingResponse(
            id=listing[0],
            title=listing[1],
            description=listing[2],
            total_floors=listing[3],
            floor_number=listing[4],
            price=float(listing[5]),
            address=listing[6],
            latitude=float(listing[7]),
            longitude=float(listing[8]),
            photos=photos,
            is_active=listing[10],
            created_at=listing[11],
            owner_name=listing[12]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server xatosi: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.get("/api/photos/{photo_id}")
async def get_photo(photo_id: str):
    """Telegram'dan haqiqiy rasmni olish"""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        return generate_placeholder_image("BOT_TOKEN yo'q")
    
    try:
        # Telegram fayl ma'lumotini olish
        file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={photo_id}"
        file_info = requests.get(file_info_url).json()
        
        if not file_info.get("ok"):
            return generate_placeholder_image("getFile xato")
        
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Suratni yuklab olish
        img_response = requests.get(file_url, stream=True)
        if img_response.status_code == 200:
            return StreamingResponse(img_response.raw, media_type="image/jpeg")
        else:
            return generate_placeholder_image("yuklash xato")
    
    except Exception as e:
        print(f"Telegram rasm yuklash xatosi: {e}")
        return generate_placeholder_image("server xato")


def generate_placeholder_image(photo_id: str):
    """Placeholder rasm yaratish"""
    try:
        # Rasm o'lchamlari
        width, height = 400, 300
        
        # Rasm yaratish
        img = Image.new('RGB', (width, height), color=(52, 152, 219))
        draw = ImageDraw.Draw(img)
        
        # Matn qo'shish
        text = f"Rasm: {photo_id[:15]}..." if len(photo_id) > 15 else f"Rasm: {photo_id}"
        
        try:
            # Font yuklash
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            # Agar font topilmasa, default font
            font = ImageFont.load_default()
        
        # Matn o'lchamini hisoblash
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Matnni markazga joylashtirish
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        # Rasmni byte ga aylantirish
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        
        return StreamingResponse(img_byte_arr, media_type="image/jpeg")
        
    except Exception as e:
        # Agar rasm yaratishda xatolik bo'lsa, oddiy text qaytarish
        return Response(content=f"Rasm topilmadi: {str(e)}", status_code=500)

# YANGI: Debug endpoint - rasmlarni tekshirish uchun
@app.get("/api/debug/photos/{listing_id}")
async def debug_photos(listing_id: int):
    """Rasmlarni tekshirish uchun debug endpoint"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT photos FROM listings WHERE id = %s", (listing_id,))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if result and result[0]:
        photos = result[0]
        return {
            "listing_id": listing_id,
            "photos_count": len(photos),
            "photos": photos,
            "photo_urls": [f"http://localhost:8000/api/photos/{photo}" for photo in photos]
        }
    
    return {"error": "Listing topilmadi yoki rasmlar yo'q"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
