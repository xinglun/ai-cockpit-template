# Android stack preset for AI Cockpit.
# Requires: Android SDK, Gradle wrapper.
# Default task names are calibration starting points for flavor-heavy apps.
# Replace them with the actual variant-specific tasks exposed by the Gradle wrapper.
# Note: connectedDebugAndroidTest requires a connected device or emulator.

PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew testDebugUnitTest
PROJECT_LINT = ./gradlew lint
