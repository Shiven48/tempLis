from abc import ABC, abstractmethod


class LoggerBase(ABC):
    """Abstract Blueprint: Defines what all logger types must do."""
    @abstractmethod
    def log(self, message: str, tag: str):
        pass

    @abstractmethod
    def clear(self):
        pass