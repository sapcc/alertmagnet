"""
This module defines custom exception classes for the AlertMagnet module.

Classes:
    AlertMagnetError: Base class for exceptions in the AlertMagnet module.
    InvalidQueryQueueError: Exception raised for invalid query queue errors.
    ConfigFileNotExistsError: Exception raised when the config file does not exist.
    InvalidConfigValueError: Exception raised for invalid config file values.
    RequiredConfigKeyNotFound: Exception raised when a required config key is not found.
"""

# TODO update the docstring to reflect the new exception classes


class AlertMagnetError(Exception):
    """
    Base class for exceptions in this module.

    Attributes:
        message (str): explanation of the error
    """

    def __init__(self, message: str = "An error occurred in the AlertMagnet module"):
        self.message = message
        super().__init__(self.message)


class InvalidQueryQueueError(AlertMagnetError):
    def __init__(self, *args):
        super().__init__(*args)


class ConfigFileNotExistsError(AlertMagnetError):
    def __init__(self, message: str = "The provided config file for the AlertMagnet doesn't exist"):
        self.message = message
        super().__init__(message)


class InvalidConfigValueError(AlertMagnetError):
    def __init__(self, message: str = "The provided config file value for the AlertMagnet is invalid"):
        self.message = message
        super().__init__(message)


class RequiredConfigKeyNotFound(AlertMagnetError):
    def __init__(self, message="A required config key was not found in the config file"):
        self.message = message
        super().__init__(message)
