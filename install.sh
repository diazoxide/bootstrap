#!/bin/sh

INSTALL_DIR=/usr/local/lib/bs

mkdir -p $INSTALL_DIR \
&& git clone https://github.com/diazoxide/bootstrap.git $INSTALL_DIR \
&& sudo chmod +x "${INSTALL_DIR}/bs.sh" \
&& sudo rm /usr/local/bin/bs \
&& sudo ln -s "${INSTALL_DIR}/bs.sh" "" \
&& echo  -e "\033[92m --- Successfully done. Run 'bs help' to start. --- \033[0m"
