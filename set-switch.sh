#!/bin/sh

cd ~p4/p4-tools/bmv2-$1 || echo 'No such switch version'
sudo make install
sudo ldconfig
