#!/bin/bash
set -eo pipefail

flake8
cd mylibs
exec pytest test/ -v