"""
Stub xpost service — X (Twitter) posting is not required by the hackathon.
This stub replaces the missing real implementation so the server starts cleanly.
"""


class XPostService:
    async def get_status(self):
        return {
            "authenticated": False,
            "screen_name": None,
            "user_id": None,
            "error": "X posting is not configured for this deployment.",
        }

    async def post_tweet(self, text: str):
        return {
            "success": False,
            "tweet_id": None,
            "tweet_url": None,
            "error": "X posting is not configured for this deployment.",
        }


_service_instance = XPostService()


async def get_xpost_service() -> XPostService:
    return _service_instance
