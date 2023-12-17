class NotOkStatusResponseError(Exception):
    """Вызывается, если код ответа отличен от 200."""


class ResponseError(Exception):
    """Вызывается, если ответ API не соответствует ожидаемому."""
