#!/bin/sh

INSTALL_DIR=/usr/local/lib/bs
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR
git pull || git clone https://github.com/diazoxide/bootstrap.git . \
&& chmod +x "${INSTALL_DIR}/bs.sh" \
&& ln -s "${INSTALL_DIR}/bs.sh" "" \
|| echo -e "\033[92m --- Successfully done. Run 'bs help' to start. --- \033[0m"
