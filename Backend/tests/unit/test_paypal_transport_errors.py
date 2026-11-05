"""Fallos de transporte deben respetar el contrato público, sin red."""
import httpx
import pytest

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_processor import PayPalPaymentProcessor


@pytest.mark.parametrize('stage', ['oauth', 'create', 'capture', 'get'])
@pytest.mark.parametrize('error', [httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError])
def test_transport_errors_are_safe_domain_errors(stage, error):
    secret = 'secret-must-not-leak'
    def handle(request):
        if stage == 'oauth' or request.url.path.endswith('/orders') or (stage == 'capture' and request.url.path.endswith('/capture')) or request.method == 'GET':
            raise error(secret, request=request)
        if request.url.path.endswith('/token'):
            return httpx.Response(200, json={'access_token': secret})
        return httpx.Response(422, json={})
    settings = Settings(paypal_mode='sandbox', paypal_client_id='id', paypal_client_secret=secret, paypal_return_url='https://example.org/return', paypal_cancel_url='https://example.org/cancel')
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        processor = PayPalPaymentProcessor(settings, client=client)
        with pytest.raises(DomainError) as raised:
            if stage in ('oauth', 'create'):
                processor.create_order('10.00', 'USD')
            else:
                processor.capture_order('PP-1')
    assert raised.value.code == 'PAYMENT_PROVIDER_ERROR'
    assert secret not in raised.value.message
