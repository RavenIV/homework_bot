class NotOkStatusResponseError(Exception):
    """Вызывается, если код ответа отличен от 200."""


class UnexpectedResponseError(Exception):
    """Вызывается, если ответ API не соответствует ожидаемому."""
