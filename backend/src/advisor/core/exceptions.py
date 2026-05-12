from __future__ import annotations


class AdvisorError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class ConfigurationError(AdvisorError):
    """Raised when required configuration is missing or invalid."""


class AgentError(AdvisorError):
    """Raised when the agent encounters an error."""


class STTError(AdvisorError):
    """Raised on speech-to-text failures."""


class TTSError(AdvisorError):
    """Raised on text-to-speech failures."""


class LLMError(AdvisorError):
    """Raised on LLM call failures."""


class RAGError(AdvisorError):
    """Raised on retrieval failures."""


class VisionError(AdvisorError):
    """Raised on computer vision pipeline failures."""


class ComplianceError(AdvisorError):
    """Raised when a response violates compliance rules."""


class MemoryError(AdvisorError):
    """Raised on memory storage/retrieval failures."""
