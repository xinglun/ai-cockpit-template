# Android stack preset for AI Cockpit.
# Requires: Android SDK, Gradle wrapper.
# Note: connectedDebugAndroidTest requires a connected device or emulator.

PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew testDebugUnitTest
PROJECT_LINT = ./gradlew lint
