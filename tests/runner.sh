#!/bin/sh

set -e

for p in test_*.py; do
    echo "Running: $p"
    PYTHONPATH=.. python $p
done

find ./test-data/var/lib/apt/ -type f | xargs rm -f
