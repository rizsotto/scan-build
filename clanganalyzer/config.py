# SPDX-License-Identifier: MIT
"""Configuration constants and settings for the clanganalyzer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyzerConfig:
    """Configuration constants for analyzer behavior.

    This class centralizes all configuration constants that were previously
    scattered throughout the codebase, making them easier to maintain and
    understand.
    """

    # Compiler flags to ignore during analysis.
    # The dictionary maps flag names to the number of additional arguments
    # that should be skipped along with the flag.
    #
    # For example:
    # - "-o": 1 means skip "-o" and the next argument (output filename)
    # - "-g": 0 means skip only "-g" (no additional arguments)
    ignored_flags: dict[str, int] | None = None

    # Languages supported by the static analyzer
    supported_languages: frozenset[str] | None = None

    # Architectures that are disabled/not supported
    disabled_architectures: frozenset[str] | None = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.ignored_flags is None:
            # To have good results from static analyzer certain compiler options
            # shall be omitted. The compiler flag filtering only affects the
            # static analyzer run.
            object.__setattr__(
                self,
                "ignored_flags",
                {
                    # Core compilation flags that will be overwritten
                    "-c": 0,  # compile option will be overwritten
                    "-fsyntax-only": 0,  # static analyzer option will be overwritten
                    "-o": 1,  # will set up own output file
                    # Debug and temporary file flags
                    "-g": 0,
                    "-save-temps": 0,
                    # macOS/Darwin-specific linker flags (inherited from Perl implementation)
                    "-install_name": 1,
                    "-exported_symbols_list": 1,
                    "-current_version": 1,
                    "-compatibility_version": 1,
                    "-init": 1,
                    "-e": 1,
                    "-seg1addr": 1,
                    "-bundle_loader": 1,
                    "-multiply_defined": 1,
                    "-sectorder": 3,  # takes 3 arguments: segment section file
                    # Compiler-specific flags
                    "--param": 1,
                    "--serialize-diagnostics": 1,
                },
            )

        if self.supported_languages is None:
            object.__setattr__(
                self,
                "supported_languages",
                frozenset(
                    {"c", "c++", "objective-c", "objective-c++", "c-cpp-output", "c++-cpp-output", "objective-c-cpp-output"}
                ),
            )

        if self.disabled_architectures is None:
            # PowerPC architectures are not supported by modern Clang static analyzer
            object.__setattr__(self, "disabled_architectures", frozenset({"ppc", "ppc64"}))


# Default configuration instance
DEFAULT_CONFIG = AnalyzerConfig()


def get_ignored_flags() -> dict[str, int]:
    """Get the dictionary of ignored compiler flags.

    Returns:
        Dictionary mapping flag names to number of arguments to skip.
    """
    assert DEFAULT_CONFIG.ignored_flags is not None, "Configuration not initialized"
    return DEFAULT_CONFIG.ignored_flags


def get_supported_languages() -> frozenset[str]:
    """Get the set of supported programming languages.

    Returns:
        Frozen set of supported language identifiers.
    """
    assert DEFAULT_CONFIG.supported_languages is not None, "Configuration not initialized"
    return DEFAULT_CONFIG.supported_languages


def get_disabled_architectures() -> frozenset[str]:
    """Get the set of disabled processor architectures.

    Returns:
        Frozen set of disabled architecture names.
    """
    assert DEFAULT_CONFIG.disabled_architectures is not None, "Configuration not initialized"
    return DEFAULT_CONFIG.disabled_architectures
