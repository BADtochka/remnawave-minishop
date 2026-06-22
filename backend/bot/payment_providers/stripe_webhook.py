from aiohttp import web

from .stripe_service import StripeService


async def stripe_webhook_route(request: web.Request) -> web.Response:
    return await request.app["stripe_service"].webhook_route(request)
