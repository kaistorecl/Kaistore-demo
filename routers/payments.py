from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/webhook")
async def stripe_webhook(request: Request):
    # En esta demo solo confirmamos recepción
    _ = await request.body()
    return {"received": True}
