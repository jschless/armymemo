"""Exceptions for the standalone Army memo library."""


class MemoParseError(ValueError):
    """Raised when memo input cannot be parsed."""


class TypstNotFoundError(FileNotFoundError):
    """Raised when a Typst binary cannot be resolved."""


class TypstCompileError(RuntimeError):
    """Raised when Typst compilation fails."""
