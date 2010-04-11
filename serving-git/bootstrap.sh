#!/usr/bin/env bash

# bootstrap.sh - bootstrap dependencies for git/twisted tutorial
# http://www.deadpuck.net/blag/serving-git/

PYTHON=$1
VE='http://bitbucket.org/ianb/virtualenv/raw/2d398ad81b7f/virtualenv.py'
ENV=GITEX

wget "${VE}"
${PYTHON} virtualenv.py --no-site-packages ${ENV}
source ${ENV}/bin/activate
easy_install pip
pip install -e "git://github.com/ligthyear/twisted.git#egg=Twisted"
pip install pycrypto pyasn1

# Cleanup
rm virtualenv.py
rm virtualenv.pyc
