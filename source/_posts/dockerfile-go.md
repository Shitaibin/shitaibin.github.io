---
title: Go程序Dockerfile模板
date: 2020-11-10 13:25:04
tags: ['Docker', 'Go']
---


## 模板

```Dockerfile
# build时设置版本 --build-arg GO_VERSION=1.13，默认为go1.15
ARG GO_VERSION=1.15
FROM golang:${GO_VERSION} AS builder
ENV GOPROXY="https://goproxy.cn"

ENV APP_PATH="/app/goapp"
WORKDIR "/app"

# 拷贝构建文件
COPY . .

# 编译
RUN go mod download
RUN CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -a -o ${APP_PATH} .
RUN ls 


# 构建运行镜像
FROM alpine:3.10 AS final

ENV APP_PATH="/app/goapp"
WORKDIR "/app"

# 拷贝程序，如有必要另外拷贝其他文件
COPY --from=builder ${APP_PATH} ${APP_PATH} 

# 运行程序
ENTRYPOINT ["/app/goapp"]
```

构建命令：

```
docker build -t app:1.0 --build-arg GO_VERSION=1.13 .
```


模板说明：
1. 构建命令不指定`--build-arg GO_VERSION=1.13`时，默认使用go1.15进行编译。
2. 使用`alpine`作为运行基础镜像，减小镜像大小。
3. Dockerfile文件放到main.go所在目录。
4. 把`goapp`替换成真正的程序名称。

