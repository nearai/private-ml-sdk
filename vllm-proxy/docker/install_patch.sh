#!/bin/bash

cp dependencies
tar xvf local_gpu_verifier.tar.gz
cd local_gpu_verifier && pip3 install . && cd ..


echo '>>> done'
