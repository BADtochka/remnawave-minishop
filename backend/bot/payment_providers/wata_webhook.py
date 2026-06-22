from aiohttp import web

from .wata_service import WataService


async def wata_webhook_route(request: web.Request) -> web.Response:
    return await request.app["wata_service"].webhook_route(request)
