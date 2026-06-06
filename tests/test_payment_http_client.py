import unittest

from bot.payment_providers.shared.http_client import (
    HttpClientMixin,
    _should_retry_transport_error,
)


class _DummyHttpClient(HttpClientMixin):
    def __init__(self):
        self._init_http_client(total_timeout=20)


class PaymentHttpClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_client_tracks_sent_headers_for_safe_retries(self):
        client = _DummyHttpClient()
        try:
            session = await client._get_session()
            self.assertFalse(session.connector.force_close)
            self.assertTrue(session.trace_configs)
        finally:
            await client.close()

    async def test_http_client_retries_only_before_headers_are_sent(self):
        self.assertTrue(
            _should_retry_transport_error(TimeoutError(), {"headers_sent": False})
        )
        self.assertFalse(
            _should_retry_transport_error(TimeoutError(), {"headers_sent": True})
        )
