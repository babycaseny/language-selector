#!/bin/sh

set -e

for p in *.py; do
    echo "Running: $p"
    python $p
done