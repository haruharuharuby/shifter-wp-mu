#!/bin/bash
set -eo pipefail

flake8
exec pytest -v