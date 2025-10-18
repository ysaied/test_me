#!/bin/sh
set -e

if [ -w /etc/resolv.conf ]; then
  {
    echo "nameserver 8.8.8.8"
    echo "nameserver 8.8.4.4"
  } > /etc/resolv.conf
fi

exec "$@"
