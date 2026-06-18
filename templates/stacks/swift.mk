# Swift stack preset for AI Cockpit.
# For Swift Package Manager (SPM) projects.
# Xcode projects: replace PROJECT_TEST in Makefile.ai.stack:
#   PROJECT_TEST = xcodebuild test \
#     -project MyApp.xcodeproj \
#     -scheme MyApp \
#     -destination 'platform=macOS'
# swift-format: install with 'brew install swift-format' (not bundled with Xcode).

PROJECT_FORMAT_CHECK = swift format lint --recursive .
PROJECT_TEST = swift test
PROJECT_LINT = swift build -Xswiftc -warnings-as-errors
