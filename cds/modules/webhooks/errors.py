"""Webhook errors."""

from __future__ import absolute_import


class WebhooksError(Exception):
    """General webhook error."""


class ReceiverDoesNotExist(WebhooksError):
    """Raised when receiver does not exist."""


class InvalidPayload(WebhooksError):
    """Raised when the payload is invalid."""


class InvalidSignature(WebhooksError):
    """Raised when the signature does not match."""
