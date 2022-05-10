FROM nginx:alpine

# region Certbot

RUN apk add --update python3 py3-pip certbot && \
    pip install certbot-nginx certbot-dns-cloudflare

# endregion

RUN apk upgrade --update-cache --available && \
    apk add openssl && \
    rm -rf /var/cache/apk/*

RUN mkdir ~/nginx-configs

COPY nginx.conf /etc/nginx/nginx.conf
COPY proxy.conf /root

COPY up-host.sh /usr/local/bin/up-host
RUN chmod +x /usr/local/bin/up-host

COPY down-host.sh /usr/local/bin/down-host
RUN chmod +x /usr/local/bin/down-host

COPY up-certificate.sh /usr/local/bin/up-certificate
RUN chmod +x /usr/local/bin/up-certificate