#!/bin/sh
set -eu

# Database migrations belong to the dedicated Compose migrate service.
exec "$@"
