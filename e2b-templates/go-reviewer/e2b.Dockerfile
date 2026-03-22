FROM golang:1.22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest \
    && go install github.com/securego/gosec/v2/cmd/gosec@latest

RUN mkdir /workspace
WORKDIR /workspace
