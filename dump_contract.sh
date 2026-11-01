#!/bin/sh -e

find . -name "*.py" ! -name "*_impl.py" ! -name "tests_*.py" \
    -exec echo "=== File: {} ===" \; \
    -exec cat {} \; \
    -exec echo \; 
