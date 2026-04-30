"""SMS / WhatsApp delivery layer.

Use `get_sms_provider()` to obtain the configured provider (chosen via
`QADAM["SMS_PROVIDER"]` setting). The returned object is a plain-python adapter
that hides whether messages go to console (dev), to WhatsApp Business API
(prod), or to a different vendor in the future.
"""

from .base import SmsProvider, SmsSendResult
from .factory import get_sms_provider

__all__ = ("SmsProvider", "SmsSendResult", "get_sms_provider")
