# Swift stack preset for AI Cockpit.
# Default scope: Swift Package Manager (SPM) only (`swift test`, `swift build`).
# Hosted "verified" status for swift uses a minimal SPM fixture in mobile-stack-quality;
# it does not validate Xcode workspaces, .xcodeproj layouts, or CocoaPods.
# Non-SPM layouts: keep this preset as a starting point, then complete Project
# Calibration (configure_ai_cockpit) with project-specific xcodebuild commands.
# Example Xcode replacement for Makefile.ai.stack:
#   PROJECT_TEST = xcodebuild test \
#     -project MyApp.xcodeproj \
#     -scheme MyApp \
#     -destination 'platform=macOS'
# CocoaPods: run pod install outside AI Cockpit; doctor does not auto-generate commands.
# swift-format: install with 'brew install swift-format' (not bundled with Xcode).

PROJECT_FORMAT_CHECK = swift format lint --recursive .
PROJECT_TEST = swift test
PROJECT_LINT = swift build -Xswiftc -warnings-as-errors
