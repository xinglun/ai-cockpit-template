# Java stack preset for AI Cockpit.
# For Spring Boot and server-side Gradle/Maven projects.
# Maven users: replace ./gradlew with mvn -q.
#   PROJECT_FORMAT_CHECK = mvn spotless:check -q
#   PROJECT_TEST         = mvn test -q
#   PROJECT_LINT         = mvn verify -q

PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew test
PROJECT_LINT = ./gradlew check
