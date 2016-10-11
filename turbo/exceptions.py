class TurboException(Exception):

    def __init__(self, message=None, *, delete=0):
        self.message = message
        self.delete = delete


class InvalidUsage(TurboException):

    """
    Raised when a command has been used incorrectly
    """
    pass


class Shutdown(Exception):
    pass
