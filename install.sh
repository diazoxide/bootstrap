#!/bin/sh

BIN_DIR=/usr/local/bin
mkdir -p $BIN_DIR

INSTALL_DIR=/usr/local/lib/bs
rm -rf $INSTALL_DIR
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

git clone https://github.com/diazoxide/bootstrap.git . \
&& pip3 install -r requirements.txt \
&& chmod +x "${INSTALL_DIR}/bs.sh" \
&& ln -s "${INSTALL_DIR}/bs.sh" /usr/local/bin/bs \
|| echo "\033[92m --- Successfully done. Run 'bs help' to start. --- \033[0m"