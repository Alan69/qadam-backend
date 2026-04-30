"""Тесты SmsProvider адаптера."""

import logging

from services.sms import SmsSendResult, get_sms_provider
from services.sms.console import ConsoleSmsProvider


class TestConsoleProvider:
    def test_returns_success_result(self):
        provider = ConsoleSmsProvider()
        result = provider.send(phone="+77001234567", message="test 1234")
        assert isinstance(result, SmsSendResult)
        assert result.success is True
        assert result.provider_message_id is not None

    def test_logs_message(self, caplog):
        provider = ConsoleSmsProvider()
        with caplog.at_level(logging.INFO, logger="qadam.sms"):
            provider.send(phone="+77001234567", message="hello")
        assert any("+77001234567" in record.getMessage() for record in caplog.records)


class TestFactory:
    def test_default_provider_is_console(self, settings):
        settings.QADAM["SMS_PROVIDER"] = "console"
        get_sms_provider.cache_clear()  # type: ignore[attr-defined]
        provider = get_sms_provider()
        assert isinstance(provider, ConsoleSmsProvider)
