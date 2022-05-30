#!/bin/sh

BIN_DIR=/usr/local/bin
INSTALL_DIR=/usr/local/lib/bs

mkdir -p $BIN_DIR
rm -rf $INSTALL_DIR && mkdir -p $INSTALL_DIR

cd "$INSTALL_DIR" \
&& git clone https://github.com/diazoxide/bootstrap.git . \
&& python3 -m pip install --upgrade pip \
&& pip3 install -r requirements.txt \
&& chmod +x "${INSTALL_DIR}/bs.sh" \
&& rm /usr/local/bin/bs \
&& ln -s "${INSTALL_DIR}/bs.sh" /usr/local/bin/bs \
&& echo "\033[92m --- Successfully done. Run 'bs help' to start. --- \033[0m"