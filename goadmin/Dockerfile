FROM golang:alpine as builder
ENV GOPROXY="https://goproxy.io"
ENV GO111MODULE="on"
WORKDIR /app
COPY . /app
RUN go build -o admin ./admin.go

From alpine:latest

WORKDIR /root/
COPY --from=builder /app .
ENTRYPOINT ["./admin"]
