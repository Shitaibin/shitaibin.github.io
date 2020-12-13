---
title: Dockerfile ARG指令
date: 2020-11-10 10:52:35
tags: ['Docker']
---


Docker的文档关于[ARG和FROM指令配合使用](https://docs.docker.com/engine/reference/builder/#understand-how-arg-and-from-interact)做了详细说明：

ARG用于传入外部参数，定义在FROM指令前，FROM后的其他指令无法使用ARG定义的环境变量，如果FROM指令后的指令要使用ARG定义的值，需要在FROM后再次定义。如果FROM不使用定义的ARG，可以直接定义到FROM后。

### 传递参数



### 定义在FROM前

```Dockerfile
ARG UBUNTU_VERSION=16.04
FROM ubuntu:${UBUNTU_VERSION}
RUN env | grep UBUNTU_VERSION
```

从结果可以看到FROM后的指令**无法访问**ARG定义的`UBUNTU_VERSION`。

```
$ docker build -t test:afterfrom .
Sending build context to Docker daemon  37.38kB
Step 1/3 : ARG UBUNTU_VERSION=16.04
Step 2/3 : FROM ubuntu:${UBUNTU_VERSION}
 ---> 4b22027ede29
Step 3/3 : RUN env | grep UBUNTU_VERSION
 ---> Running in 8e93ca5e376b
The command '/bin/sh -c env | grep UBUNTU_VERSION' returned a non-zero code: 1
```

### 定义在FROM后

```Dockerfile
ARG UBUNTU_VERSION=16.04
FROM ubuntu:${UBUNTU_VERSION}
ARG UBUNTU_VERSION
RUN env | grep UBUNTU_VERSION
```

从结果可以看到FROM后的指令**可以访问**ARG定义的`UBUNTU_VERSION`。

```
$ docker build -t test:afterfrom .
Sending build context to Docker daemon  37.38kB
Step 1/4 : ARG UBUNTU_VERSION=16.04
Step 2/4 : FROM ubuntu:${UBUNTU_VERSION}
 ---> 4b22027ede29
Step 3/4 : ARG UBUNTU_VERSION
 ---> Using cache
 ---> e3bae0875e66
Step 4/4 : RUN env | grep UBUNTU_VERSION
 ---> Running in 02438aff1f75
UBUNTU_VERSION=16.04
Removing intermediate container 02438aff1f75
 ---> 646eec496165
Successfully built 646eec496165
Successfully tagged test:afterfrom
```

### 传递多个ARG参数

```Dockerfile
ARG UBUNTU_VERSION=16.04
ARG FILE_NAME=test
FROM ubuntu:${UBUNTU_VERSION}

ARG FILE_NAME
WORKDIR /test/
RUN touch ${FILE_NAME}
RUN ls ${FILE_NAME}
```

传递多个参数需要多次使用`--build-arg`，可以看到传递的`FILE_NAME=app`生效了，而不是默认值。

```
$ docker build -t test:twoargs --build-arg UBUNTU_VERSION=18.04 --build-arg FILE_NAME=app .
Sending build context to Docker daemon  37.38kB
Step 1/7 : ARG UBUNTU_VERSION=16.04
Step 2/7 : ARG FILE_NAME=test
Step 3/7 : FROM ubuntu:${UBUNTU_VERSION}
18.04: Pulling from library/ubuntu
171857c49d0f: Pull complete
419640447d26: Pull complete
61e52f862619: Pull complete
Digest: sha256:646942475da61b4ce9cc5b3fadb42642ea90e5d0de46111458e100ff2c7031e6
Status: Downloaded newer image for ubuntu:18.04
 ---> 56def654ec22
Step 4/7 : ARG FILE_NAME
 ---> Running in bee623328f35
Removing intermediate container bee623328f35
 ---> 52f803da2959
Step 5/7 : WORKDIR /test/
 ---> Running in fa4542584af1
Removing intermediate container fa4542584af1
 ---> 5ebd782db9b8
Step 6/7 : RUN touch ${FILE_NAME}
 ---> Running in 0cd5723b744d
Removing intermediate container 0cd5723b744d
 ---> 920c6bd75bab
Step 7/7 : RUN ls ${FILE_NAME}
 ---> Running in b94a33093ddf
app
Removing intermediate container b94a33093ddf
 ---> 804bf831059a
Successfully built 804bf831059a
Successfully tagged test:twoargs
```