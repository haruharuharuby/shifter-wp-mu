#!/bin/bash
set -eo --pipefail

cd mylibs
exec pytest test/ -v