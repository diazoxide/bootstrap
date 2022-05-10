#!/bin/ash

if [ "$1" != "" ]; then
  HOST_NAME=$1
else
  echo "HOST name not provided;"
  exit 1
fi

certificates_dir="/etc/nginx/certificates"
mkdir -p certificates_dir
ssl_config_file="$certificates_dir/$HOST_NAME.conf"
ssl_key_file="$certificates_dir/$HOST_NAME.key"

if [ ! -f "$ssl_key_file" ]; then

i=1;
alt_names="";
common_name="";
for host in $(echo "$HOST_NAME" | tr "," "\n")
do
  if [ "$i" == "1" ]; then
    common_name="$host";
  fi
  alt_names=$alt_names"DNS.${i} = ${host}"$'\n'
  alt_names=$alt_names"DNS.$((i+1)) = *.${host}"$'\n';
  i=$((i+2));
done;

dt=${dt%$'\n'}

  cat <<EOF | tee "$ssl_config_file"
[ req ]
req_extensions     = req_ext
distinguished_name = req_distinguished_name
prompt             = no
[req_distinguished_name]
commonName=${common_name}
[req_ext]
subjectAltName   = @alt_names
[alt_names]
${alt_names}
EOF

  openssl req -x509 -config "$ssl_config_file" -extensions req_ext -nodes -days 730 -newkey rsa:2048 -sha256 -keyout "$certificates_dir/$HOST_NAME.key" -out "$certificates_dir/$HOST_NAME.crt"
  rm -rf "$ssl_config_file"
fi
