# SPDX-License-Identifier: MIT

import unittest

from clanganalyzer import config


class AnalyzerConfigTest(unittest.TestCase):
    """Test the AnalyzerConfig dataclass and configuration functions."""

    def test_default_config_initialization(self):
        """Test that the default configuration is properly initialized."""
        # Test that the default config instance is created
        self.assertIsInstance(config.DEFAULT_CONFIG, config.AnalyzerConfig)

        # Test that all fields are initialized (not None)
        self.assertIsNotNone(config.DEFAULT_CONFIG.ignored_flags)
        self.assertIsNotNone(config.DEFAULT_CONFIG.supported_languages)
        self.assertIsNotNone(config.DEFAULT_CONFIG.disabled_architectures)

    def test_ignored_flags_configuration(self):
        """Test that ignored flags are properly configured."""
        flags = config.get_ignored_flags()

        # Should be a dictionary
        self.assertIsInstance(flags, dict)

        # Should contain expected core flags
        self.assertIn("-c", flags)
        self.assertIn("-o", flags)
        self.assertIn("-fsyntax-only", flags)
        self.assertIn("-g", flags)

        # Verify specific flag behaviors
        self.assertEqual(flags["-c"], 0)  # no additional args
        self.assertEqual(flags["-o"], 1)  # skip output filename
        self.assertEqual(flags["-sectorder"], 3)  # skip 3 args

        # Should contain macOS/Darwin-specific flags
        self.assertIn("-install_name", flags)
        self.assertIn("-bundle_loader", flags)

    def test_supported_languages_configuration(self):
        """Test that supported languages are properly configured."""
        languages = config.get_supported_languages()

        # Should be a frozenset
        self.assertIsInstance(languages, frozenset)

        # Should contain expected languages
        expected_languages = {
            "c",
            "c++",
            "objective-c",
            "objective-c++",
            "c-cpp-output",
            "c++-cpp-output",
            "objective-c-cpp-output",
        }
        self.assertEqual(languages, expected_languages)

    def test_disabled_architectures_configuration(self):
        """Test that disabled architectures are properly configured."""
        archs = config.get_disabled_architectures()

        # Should be a frozenset
        self.assertIsInstance(archs, frozenset)

        # Should contain PowerPC architectures
        expected_archs = {"ppc", "ppc64"}
        self.assertEqual(archs, expected_archs)

    def test_custom_config_initialization(self):
        """Test creating a custom configuration."""
        custom_flags = {"-custom": 1}
        custom_languages = frozenset({"rust"})
        custom_archs = frozenset({"arm"})

        custom_config = config.AnalyzerConfig(
            ignored_flags=custom_flags, supported_languages=custom_languages, disabled_architectures=custom_archs
        )

        self.assertEqual(custom_config.ignored_flags, custom_flags)
        self.assertEqual(custom_config.supported_languages, custom_languages)
        self.assertEqual(custom_config.disabled_architectures, custom_archs)

    def test_config_immutability(self):
        """Test that the configuration is immutable."""
        # The dataclass should be frozen
        with self.assertRaises(AttributeError):
            config.DEFAULT_CONFIG.ignored_flags = {}

    def test_getter_functions_return_correct_types(self):
        """Test that getter functions return the expected types."""
        # Test return types
        flags = config.get_ignored_flags()
        languages = config.get_supported_languages()
        archs = config.get_disabled_architectures()

        self.assertIsInstance(flags, dict)
        self.assertIsInstance(languages, frozenset)
        self.assertIsInstance(archs, frozenset)

        # Test that values are not empty
        self.assertTrue(len(flags) > 0)
        self.assertTrue(len(languages) > 0)
        self.assertTrue(len(archs) > 0)

    def test_ignored_flags_completeness(self):
        """Test that ignored flags contain all expected categories."""
        flags = config.get_ignored_flags()

        # Core compilation flags
        core_flags = ["-c", "-fsyntax-only", "-o"]
        for flag in core_flags:
            self.assertIn(flag, flags)

        # Debug flags
        debug_flags = ["-g", "-save-temps"]
        for flag in debug_flags:
            self.assertIn(flag, flags)

        # Linker flags
        linker_flags = ["-install_name", "-exported_symbols_list", "-bundle_loader"]
        for flag in linker_flags:
            self.assertIn(flag, flags)

        # Compiler-specific flags
        compiler_flags = ["--param", "--serialize-diagnostics"]
        for flag in compiler_flags:
            self.assertIn(flag, flags)

    def test_configuration_consistency(self):
        """Test that configuration values are consistent and sensible."""
        flags = config.get_ignored_flags()

        # All values should be non-negative integers
        for _flag, count in flags.items():
            self.assertIsInstance(count, int)
            self.assertGreaterEqual(count, 0)
            self.assertLessEqual(count, 10)  # Sanity check - no flag should skip more than 10 args

        # Languages should all be lowercase strings
        languages = config.get_supported_languages()
        for lang in languages:
            self.assertIsInstance(lang, str)
            self.assertEqual(lang, lang.lower())

        # Architectures should all be lowercase strings
        archs = config.get_disabled_architectures()
        for arch in archs:
            self.assertIsInstance(arch, str)
            self.assertEqual(arch, arch.lower())
