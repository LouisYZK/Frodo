#!/bin/bash 
set -x
cd python_web
if [ `arch` == "aarch64" ]; then
    echo "building arm64 image"
    docker buildx build --platform linux/arm64 -t frodo/pyweb -f Dockerfile.arm . 
elif [ `arch` == "i386" ];then
    echo "buiding x86 images"
    docker build  -t frodo/pyweb -f Dockerfile .
else
    echo "Unkonow Arch to build."
fi

cd ../goadmin
docker build -t frodo/goweb .