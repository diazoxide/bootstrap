#!/bin/ash

if [ "$1" != "" ]; then
  HOST_NAME=$1
  echo "HOST: '$HOST_NAME'"
else
  echo "HOST name not provided;"
  exit 1
fi

rm -rf "/etc/nginx/conf.d/${HOST_NAME}.conf"