import unittest

from bot.payment_providers.shared.http_client import (
    HttpClientMixin,
    _PAYMENT_REQUEST_USER_AGENT,
    _should_retry_transport_error,
)


class _DummyHttpClient(HttpClientMixin):
    def __init__(self):
        self._init_http_client(total_timeout=20)


class PaymentHttpClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_client_does_not_reuse_provider_tcp_connections(self):
        client = _DummyHttpClient()
        try:
            session = await client._get_session()
            self.assertTrue(session.connector.force_close)
            self.assertTrue(session.trace_configs)
            self.assertEqual(session.headers["User-Agent"], _PAYMENT_REQUEST_USER_AGENT)
        finally:
            await client.close()

    async def test_http_client_retries_only_before_headers_are_sent(self):
        self.assertTrue(
            _should_retry_transport_error(TimeoutError(), {"headers_sent": False})
        )
        self.assertFalse(
            _should_retry_transport_error(TimeoutError(), {"headers_sent": True})
        )
