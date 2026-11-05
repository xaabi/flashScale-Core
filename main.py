from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import redis
import os

app = FastAPI(
    title="FlashScale-Core API",
    description="High-Concurrency Flash Sale & Ticketing Engine with Redis Atomic Operations",
    version="1.0.0"
)

# Koneksi ke Redis (pastikan Redis aktif atau gunakan simulasi in-memory jika testing lokal)
# Untuk enterprise-standard, kita gunakan Redis sebagai distributed lock & stock counter.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
except Exception:
    redis_client = None

class PurchaseRequest(BaseModel):
    user_id: str
    item_id: str
    quantity: int = 1

@app.get("/")
def read_root():
    return {"status": "ONLINE", "service": "FlashScale-Core Engine is running."}

@app.post("/api/v1/flash-sale/buy")
def flash_sale_purchase(payload: PurchaseRequest):
    """
    Endpoint flash sale dengan simulasi atomic decrement stock untuk 
    mencegah race condition dan double-booking.
    """
    stock_key = f"stock:{payload.item_id}"
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis server connection failed.")
    
    # Cek apakah key stok ada, jika belum set default stok flash sale = 100
    if not redis_client.exists(stock_key):
        redis_client.set(stock_key, 100)
    
    # Kurangi stok secara atomic menggunakan Redis DECRBY
    current_stock = redis_client.decrby(stock_key, payload.quantity)
    
    if current_stock < 0:
        # Kembalikan stok jika kehabisan (rollback)
        redis_client.incrby(stock_key, payload.quantity)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sold Out! Stok flash sale telah habis."
        )
        
    return {
        "status": "SUCCESS",
        "message": "Transaksi flash sale berhasil!",
        "user_id": payload.user_id,
        "item_id": payload.item_id,
        "remaining_stock": current_stock
    }
