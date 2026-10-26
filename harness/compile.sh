#!/bin/sh
# usage: compile.sh <worktree-path> <modules comma list>
MSYS_NO_PATHCONV=1 docker run --rm -v "$1":/src -v pulsar-m2:/root/.m2 -w /src maven:3.9-eclipse-temurin-21 \
  mvn -B -q -o -pl "$2" compile -DskipTests -Dlicense.skip=true -Drat.skip=true -Dcheckstyle.skip=true -Dspotbugs.skip=true -Dmaven.javadoc.skip=true -Dmaven.source.skip=true 2>&1 | tail -40
