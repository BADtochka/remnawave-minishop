from aiohttp import web

from .paykilla_service import PaykillaService


async def paykilla_webhook_route(request: web.Request) -> web.Response:
    return await request.app["paykilla_service"].webhook_route(request)
