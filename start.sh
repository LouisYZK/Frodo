set -x

cd goadmin
go run admin.go &

cd ..
source ./venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8004