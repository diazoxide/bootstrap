#!/bin/ash

if [ "$1" != "" ]; then
  CONTAINER=$1
  echo "CONTAINER: '$CONTAINER'"
else
  echo "CONTAINER name not provided;"
  exit 1
fi

if [ "$2" != "" ]; then
  HOST_NAME=$2
  echo "HOST: '$HOST_NAME'"
else
  echo "HOST name not provided;"
  exit 1
fi

if [ "$3" != "" ]; then
  PORT=$3
  echo "PORT: '$PORT'"
else
  echo "PORT not provided;"
  exit 1
fi

# External NGINX Config file
TEMP_CONF_FILE_PATH="$HOME/nginx-configs/${HOST_NAME}.conf"

echo "TEMP_CONF_FILE_PATH: ${TEMP_CONF_FILE_PATH}"

cp -rf ~/proxy.conf "$TEMP_CONF_FILE_PATH"

SANITIZED_HOST_NAME="${HOST_NAME/,/ }"

sed -i -e "s/__CONTAINER__/${CONTAINER}/g" "$TEMP_CONF_FILE_PATH"
sed -i -e "s/__SERVER_NAME__/${SANITIZED_HOST_NAME}/g" "$TEMP_CONF_FILE_PATH"
sed -i -e "s/__CERTIFICATE_NAME__/${HOST_NAME}/g" "$TEMP_CONF_FILE_PATH"
sed -i -e "s/__PORT__/${PORT}/g" "$TEMP_CONF_FILE_PATH"

yes | mv "$TEMP_CONF_FILE_PATH" "/etc/nginx/conf.d/${HOST_NAME}.conf"

up-certificate "$HOST_NAME"
