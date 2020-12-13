---
title: 让镜像飞，加速你的开发
date: 2019-07-13 11:15:51
tags: ['Linux', 'Mac', 'Docker']
---

由于你知我知的网络原因，开发者遇到了以下问题：

1. brew/apt-get/yum等安装软件慢、更新慢
1. docker下载镜像慢
1. go get某些package无法访问、超时
1. ...

怎么解决？

1. 挂代理，实现科学上网
2. 换镜像，曲线救国

镜像都在国内，所以镜像效果比代理好。

换代理请看[让终端科学上网](http://lessisbetter.site/2018/09/06/Science-and-the-Internet/)。

接下来看几个常用的镜像。

## Linux发行版镜像

[阿里镜像首页](https://opsx.alibaba.com/mirror)列出了所有发行版的镜像状态，以及【帮助】，展示了如何更换源。

这里不仅包含了发行版的镜像，还有homebrew、docker，但我认为这2个阿里的镜像不太好用，但列出来了。

## Brew镜像

你需要[让Homebrew飞](http://lessisbetter.site/2019/07/13/better-brew/)。

## Docker镜像

使用加速器的原理是，docker deamon会先去加速器寻找镜像，如果找不到才从docker官方仓库拉镜像。如果指定拉某个镜像仓库的镜像，镜像加速器是用不上的。

看如何配置[Docker镜像加速器](https://yeasy.gitbooks.io/docker_practice/install/mirror.html)。

推荐使用阿里云、七牛、DaoCloud的镜像。

## Go modules代理

现在国内已经有第三方的Go modules代理服务了，比如：

1. [goproxy.io](https://goproxy.io/zh/)，是[盛奥飞](https://github.com/aofei)小哥捐给了七牛搭建的Go modules代理服务。
1. [aliyun goproxy](http://mirrors.aliyun.com/goproxy/)，阿里云昨天（大概2019年07月15日）刚开放了Go modules代理服务。

fabric使用vendor，下载各种东西的时候需要翻墙，即便是可以翻墙，也是有缺点的：

1. 慢。
2. 翻墙有流量限制。