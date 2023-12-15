class NotOkStatusResponseError(Exception):
    """Вызывается, если код ответа отличен от 200."""

    def __init__(self, message, info):
        super().__init__(message)
        self.info = info
