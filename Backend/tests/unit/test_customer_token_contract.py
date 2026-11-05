"""Contrato observable de tokens; el SQL usa cursores controlados, sin servidor."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from tallerclaro.infrastructure.security.token_service import CustomerTokenService
from tests.fakes import FakeCustomerTokenRepository, FakeUnitOfWork

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.now = NOW
    def __call__(self):
        return self.now
    def __deepcopy__(self, memo):
        raise AssertionError('A transaction must not copy the clock')


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
@pytest.mark.parametrize('case', ['valid', 'unknown', 'tampered', 'expired', 'used', 'boundary'])
def test_token_verification_contract(kind, case):
    clock = Clock()
    conn = MagicMock()
    if kind == 'fake':
        repo = FakeCustomerTokenRepository(clock=clock, ttl_hours=1)
    else:
        repo = CustomerTokenService(conn, secret='test-secret', ttl_hours=1, clock=clock)
    token = repo.create(7, 9)
    if kind == 'postgres':
        sql, params = conn.execute.call_args.args
        assert 'INSERT INTO tallerclaro.cliente_token' in sql
        assert params[:2] == (7, 9)
        assert params[2] != token and len(params[2]) == 64
        assert params[3] == NOW + timedelta(hours=1)
        row = None if case in ('unknown', 'tampered') else (7, 9, params[3], case == 'used')
        conn.execute.return_value.fetchone.return_value = row
    elif case == 'used':
        repo._tokens[token]['used'] = True
    if case == 'expired':
        clock.now += timedelta(hours=1, microseconds=1)
    elif case == 'boundary':
        clock.now += timedelta(hours=1)
    candidate = 'unknown' if case == 'unknown' else token + '-tampered' if case == 'tampered' else token
    assert repo.verify(candidate) == ((7, 9) if case in ('valid', 'boundary') else None)
    if kind == 'postgres':
        sql, params = conn.execute.call_args.args
        assert 'WHERE token_hash = %s' in sql
        assert len(params) == 1 and params[0] != candidate


def test_token_transaction_does_not_copy_or_replace_clock():
    clock = Clock()
    tokens = FakeCustomerTokenRepository(clock=clock)
    uow = FakeUnitOfWork(tokens=tokens)
    with uow:
        abandoned = uow.tokens.create(1, 2)
    with uow:
        assert uow.tokens.verify(abandoned) is None
        kept = uow.tokens.create(1, 2)
        uow.commit()
    clock.now += timedelta(hours=73)
    with uow:
        assert uow.tokens.verify(kept) is None
        assert uow.tokens._clock is clock
