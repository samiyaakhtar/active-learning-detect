#!/bin/bash  
#
#This script automates the instructions from here:
#https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/installation.md
#

#Fail on first error
set -e
#Suppress expanding variables before printing.
set +x
set +v

#When executing on a DSVM over SSH some paths for pip, cp, make, etc may not be in the path,
export PATH=/anaconda/envs/py35/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:/opt/caffe/build/install/bin/:/usr/local/cuda/bin:/dsvm/tools/cntk/cntk/bin:/usr/local/cuda/bin:/dsvm/tools/cntk/cntk/bin:/dsvm/tools/spark/current/bin:/opt/mssql-tools/bin:/bin

echo -e '\n*******\tClone Tensorflow Models\t*******\n'
git clone https://github.com/tensorflow/models.git repos/models

echo -e '\n*******\tInstall Tensorflow package\t*******\n'
cd repos/models/ && pip install tensorflow-gpu

echo -e '\n*******\tInstall COCO API\t*******\n'
cd ~/
git clone https://github.com/cocodataset/cocoapi.git repos/cocoapi
cd repos/cocoapi/PythonAPI/
make 
cp -r pycocotools ~/repos/models/research/

echo -e '\n*******\tSetup Protocal Buffer\t******\n'
cd ~/
cd repos/models/research/
wget -O protobuf.zip https://github.com/google/protobuf/releases/download/v3.0.0/protoc-3.0.0-linux-x86_64.zip
unzip -o protobuf.zip
./bin/protoc object_detection/protos/*.proto --python_out=.

echo -e '\n*******\tSetup Python Path\t******\n'
export PYTHONPATH=$PYTHONPATH:`pwd`:`pwd`/slim

echo -e '\n*******\tRunning Object Detection Tests\t******\n'
python object_detection/builders/model_builder_test.py

echo -e '\n*******\tClone Active Learning\t*******\n'
git clone https://github.com/CatalystCode/active-learning-detect


#Update the config.ini file at repos/models/research/active-learning-detect
echo -e 'Objection dectection install validation complete'