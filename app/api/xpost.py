from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.xpost import get_xpost_service

router = APIRouter(prefix="/api/xpost", tags=["xpost"])


class TweetRequest(BaseModel):
    text: str


class TweetResponse(BaseModel):
    success: bool
    tweet_id: str | None = None
    tweet_url: str | None = None
    error: str | None = None


@router.get("/status")
async def xpost_status():
    """Check X connection status."""
    try:
        service = await get_xpost_service()
        return await service.get_status()
    except RuntimeError as e:
        return {
            "authenticated": False,
            "screen_name": None,
            "user_id": None,
            "error": str(e),
        }


@router.post("/tweet", response_model=TweetResponse)
async def post_tweet(req: TweetRequest):
    """Post a tweet to X."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Tweet text cannot be empty.")

    if len(req.text) > 280:
        raise HTTPException(status_code=400, detail="Tweet text exceeds 280 characters.")

    try:
        service = await get_xpost_service()
        result = await service.post_tweet(req.text.strip())
        return TweetResponse(**result)
    except RuntimeError as e:
        return TweetResponse(success=False, error=str(e))
    except Exception as e:
        return TweetResponse(success=False, error=f"Unexpected error: {str(e)}")
