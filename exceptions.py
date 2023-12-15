class TokenNotFoundError(Exception):
    """Вызывается при отсутствии обязательных переменных окружения."""


class NotOkStatusResponseError(Exception):
    """Вызывается, если код ответа отличен от 200."""


class BadRequestError(Exception):
    """Вызывается при провале запроса к API."""


class UnexpectedResponseError(Exception):
    """Вызывается, если ответ API не соответствует ожидаемому."""
