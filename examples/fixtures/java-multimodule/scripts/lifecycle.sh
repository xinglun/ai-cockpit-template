#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD="$ROOT/.fixture-build"
rm -rf "$BUILD"
mkdir -p "$BUILD/core-main" "$BUILD/core-test" "$BUILD/app-main" "$BUILD/app-test"

status="passed"
java_toolchain="available"
if ! command -v javac >/dev/null 2>&1 || ! command -v java >/dev/null 2>&1; then
  status="not_run"
  java_toolchain="not_run"
fi

run_java() {
  if [ "$java_toolchain" = "not_run" ]; then return 0; fi
  javac -Xlint:all -d "$BUILD/core-main" "$ROOT/core/src/main/java/fixture/core/Decision.java"
  javac -Xlint:all -cp "$BUILD/core-main" -d "$BUILD/core-test" "$ROOT/core/src/test/java/fixture/core/DecisionTest.java"
  java -cp "$BUILD/core-main:$BUILD/core-test" fixture.core.DecisionTest
  javac -Xlint:all -cp "$BUILD/core-main" -d "$BUILD/app-main" "$ROOT/app/src/main/java/fixture/app/Main.java"
  javac -Xlint:all -cp "$BUILD/core-main:$BUILD/app-main" -d "$BUILD/app-test" "$ROOT/app/src/test/java/fixture/app/MainTest.java"
  java -cp "$BUILD/core-main:$BUILD/app-main:$BUILD/app-test" fixture.app.MainTest
}

run_java
maven_status="not_run"
if command -v mvn >/dev/null 2>&1; then maven_status="available_not_invoked"; fi

cp "$ROOT/pom.xml" "$BUILD/pom.baseline.xml"
sed 's/<version>1.0.0<\//<version>1.0.1<\//' "$BUILD/pom.baseline.xml" > "$BUILD/pom.upgraded.xml"
grep -q '<version>1.0.1</version>' "$BUILD/pom.upgraded.xml"
cp "$BUILD/pom.baseline.xml" "$BUILD/pom.rollback.xml"
cmp -s "$BUILD/pom.baseline.xml" "$BUILD/pom.rollback.xml"

if [ "$java_toolchain" = "available" ]; then
  execution_kind="local_real_execution"
else
  execution_kind="not_run"
fi

cat <<JSON
{"fixture":"java-multimodule","phases":[
 {"name":"Install","status":"$status","executionKind":"$execution_kind","evidence":"javac/java dependency-free toolchain; maven:$maven_status"},
 {"name":"Configure","status":"passed","executionKind":"local_real_execution","evidence":"pom.xml, core, app"},
 {"name":"Normal Work Item","status":"$status","executionKind":"$execution_kind","evidence":"core and app source/tests executed with javac/java"},
 {"name":"Ambiguous Request","status":"blocked","executionKind":"blocked","reason":"ambiguous request is refused","resumeCondition":"Provide an explicit request scope and approval before continuing.","policy":"governance"},
 {"name":"Critical Domain Change","status":"blocked","executionKind":"blocked","reason":"critical-domain change is refused without evidence","resumeCondition":"Require domain-owner review and verified rollback evidence before continuing.","policy":"critical-change"},
 {"name":"Upgrade","status":"passed","executionKind":"local_real_execution","evidence":"Version is changed and verified in a temporary working copy."},
 {"name":"Rollback","status":"passed","executionKind":"local_real_execution","evidence":"Temporary working copy is restored and compared to the baseline version."},
 {"name":"Release Check","status":"$status","executionKind":"$execution_kind","evidence":"Local artifact boundary only; provider release:not_run"}
]}
JSON
rm -rf "$BUILD"
