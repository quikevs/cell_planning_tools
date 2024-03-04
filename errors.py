
class NotInitialized(AttributeError):
    def __init__(self, message, errors) -> None:
        super().__init__(message)
        self.errors = errors
        return


class OutOfRangeError(ValueError):
    def __init__(self, message, errors) -> None:
        super().__init__(message)
        self.errors = errors
        return