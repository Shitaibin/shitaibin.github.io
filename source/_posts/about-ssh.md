---
title: SSH常用命令和配置
date: 2020-07-28 21:11:15
tags: ['Linux']
---


## 生成SSH密钥

```sh
ssh-keygen -t rsa -f ~/.ssh/id_rsa -C "temp user" -N ""
```

-t：指定加密算法
-f：指定路径
-C：注释，可以填写用户名或邮箱
-N：密码

指定以上`f、C、N`这3个参数，可以避免交互式问答，快速生成密钥，在脚本中使用很方便。

## SSH客户端配置文件

`~/.ssh/config`文件内容如下：

```
# Read more about SSH config files: https://linux.die.net/man/5/ssh_config
Host 个人VM
    HostName 192.168.9.137
    User centos

Host 阿里云
    HostName 139.224.105.10
    User root
    
    
Host 腾讯云
    HostName 140.143.6.185
    User root
    Port 22
    IdentityFile ~/.ssh/id_rsa_tencent
```

- Host：自定义命名
- HostName：机器IP或者域名
- User：登录机器的用户名
- Port：登录机器的端口，默认为22，可省略
- IdentityFile：登录机器时使用的私钥，默认为`~/.ssh/id_rsa`，可省略；当某台机器使用单独密钥时，很有用