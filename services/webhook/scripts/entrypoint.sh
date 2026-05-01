#!/bin/sh
apk add --no-cache -q git docker-cli docker-compose openssh-client python3 py3-yaml
exec /usr/local/bin/webhook "$@"