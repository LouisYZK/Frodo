set -x
cd python_web
docker build -t frodo/pyweb  .
cd ../goadmin
docker build -t frodo/goweb .