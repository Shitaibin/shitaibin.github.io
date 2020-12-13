---
title: Docker网络代理和仓库镜像加速
date: 2020-09-05 14:48:04
tags: ['Docker']
---

对于Docker官方镜像仓库`Registry`，没有仓库镜像加速，寸步难行。

对于国外非Docker官方镜像仓库，并且还被墙的仓库`Registry`，没有网络代理，寸步难行。

镜像仓库加速器`Registry Mirrors`，是国内对官方`Registry`的"镜像(mirror)"，当拉取image时，Docker Daemon先去 `Registry Mirrors` 拉去镜像，如果没找到镜像，`Registry Mirrors`找官方`Registry`拉去镜像，然后再返回给本地。

网络代理是给Docker设置http和https代理，最原始的方式，适合有代理的情况。主要用于服务器上有**稳定可访问**的代理或者当前主机上有稳定代理的情况。对于代理和docker不在同一台机器上时，稳定可访问就成了一个问题，比如代理在笔记本上，IP随时都可能变化，服务器连接笔记本做代理，就算法上稳定可访问，而docker也在笔记本上运行，通过环回地址就能稳定访问。

**不推荐给Docker设置代理，而应当优先使用`Registry Mirrors`**。代理也是有副作用的，你需要保证非本机能稳定连接到代理，并且能够转发数据，不然端口拒绝访问、TLS握手失败等问题，需要花费更多的时间。

可访问的Registry有：
- [quay.io](https://quay.io/) : 只是访问慢一些而已，可以拉下镜像来

## 镜像仓库加速器(推荐)

如果指定拉某个镜像仓库的镜像，镜像加速器是用不上的。如果该仓库可以访问，非本机有代理的情况，无需配置网络代理。

看如何配置[Docker镜像加速器](https://yeasy.gitbooks.io/docker_practice/install/mirror.html)。

推荐使用阿里云、七牛、DaoCloud的镜像仓库加速器。

`/etc/docker/daemon.json` 配置如下：

```
{
    "insecure-registries":["192.168.9.8:80"],
    "registry-mirrors": ["https://a90tkz28.mirror.aliyuncs.com"]
}
```

然后冲抵daemon：

```
$ sudo systemctl daemon-reload
$ sudo systemctl restart docker
```


## 为Docker Daemon设置网络代理(不推荐)

我Mac上的http、https、socks5代理，http和https监听的是7890端口，sock5监听的是7891端口。

拉镜像时，可以看到docker连接了7890端口走http代理。

```
[/private/tmp]$ lsof -i:7890
COMMAND     PID      USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
....
com.docke 73371 shitaibin   50u  IPv4 0xa8184ba4240fbe99      0t0  TCP localhost:58847->localhost:7890 (ESTABLISHED)
com.docke 73371 shitaibin   53u  IPv4 0xa8184ba4035deb09      0t0  TCP localhost:58857->localhost:7890 (ESTABLISHED)
com.docke 73371 shitaibin   58u  IPv4 0xa8184ba42d889861      0t0  TCP localhost:58893->localhost:7890 (ESTABLISHED)
```

[官方设置代理教程](https://docs.docker.com/network/proxy/)，2选1:
1. 给Docker客户端设置代理，拉去镜像、创建新容器时，客户端会把变量发送给Daemon。支持17.07及以上版本，这是官方推荐方式。
2. 给Daemon设置代理，通过环境变量的方式。支持17.06及以下版本，不推荐。

给Daemon设置的代理的另外方法：

创建Daemon的代理配置文件：

```
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo touch /etc/systemd/system/docker.service.d/http-proxy.conf
```

内容为：

```
[Service]
Environment="HTTP_PROXY=http://proxy.server.com:913/" "HTTPS_PROXY=http://proxy.server.com:913/" "NO_PROXY=localhost,127.0.0.1,10.96.0.0/16, 10.244.0.0/16"
```

然后重启Daemon：

```
sudo systemctl daemon-reload
sudo systemctl restart docker

systemctl show --property=Environment docker
```

## 关于Docker代理的另外一件事：容器内的代理(几乎不用)

默认情况`~/.docker/config.json`是docker客户端的配置文件，其中可以配置Http和Https代理，这些环境变量会通过`--build-arg`的方式，在执行`docker build`时传递到镜像中。

**容器内的服务通常不需要代理，所以这个无需设置**。


看个测试demo，config.json内容如下：

```json
{
 "proxies":
 {
   "default":
   {
     "httpProxy": "http://127.0.0.1:3001",
     "httpsProxy": "http://127.0.0.1:3001",
     "noProxy": "*.test.example.com,.example2.com"
   }
 }
}
```

Dockerfile如下：


```dockerfile
FROM busybox
RUN env
```

构建过程如下，可以看到设置了http等环境变量：

```
$ docker build .
Sending build context to Docker daemon  2.048kB
Step 1/2 : FROM busybox
 ---> f0b02e9d092d
Step 2/2 : RUN env
 ---> Running in 2a8fe4fad631
HTTPS_PROXY=http://127.0.0.1:3001
no_proxy=*.test.example.com,.example2.com
HOSTNAME=2a8fe4fad631
SHLVL=1
HOME=/root
NO_PROXY=*.test.example.com,.example2.com
https_proxy=http://127.0.0.1:3001
http_proxy=http://127.0.0.1:3001
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PWD=/
HTTP_PROXY=http://127.0.0.1:3001
Removing intermediate container 2a8fe4fad631
 ---> 89c86d136d8d
Successfully built 89c86d136d8d
```

启动容器后http环境变量依然生效：

```
[~/test]$ docker run -it --rm 89c86d136d8d sh
/ # env
HTTPS_PROXY=http://127.0.0.1:3001
no_proxy=*.test.example.com,.example2.com
HOSTNAME=e9c131f55062
SHLVL=1
HOME=/root
NO_PROXY=*.test.example.com,.example2.com
https_proxy=http://127.0.0.1:3001
http_proxy=http://127.0.0.1:3001
TERM=xterm
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PWD=/
HTTP_PROXY=http://127.0.0.1:3001
```