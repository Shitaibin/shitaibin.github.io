---
title: Go Modules 方法、问题汇总贴
date: 2019-10-31 17:07:59
tags: ['Go']
---


## 教程资料

- 简单操作：https://segmentfault.com/a/1190000016703769
- 多项介绍：https://learnku.com/golang/t/33859
- 官方教程：https://blog.golang.org/using-go-modules

## 问题汇总

### replace 使用http或https

在使用go replace时，有2点注意：
- 目标仓库不能带协议头，比如http、https，要从域名或者IP开始
- 版本号格式要符合语义格式化，测试版本是否符合规则：[Go playground 样例代码](https://play.golang.org/p/S_Jz3-Uxh_T)

直接修改 `go.mod` 文件格式：
```
replace github.com/hyperledger/fabric v1.4.1 => 192.168.9.251/hyperledger/fabric v1.4.1-alpha.11-yx
```

或使用命令：
```
go mod edit -replace=github.com/hyperledger/fabric@v1.4.1=192.168.9.251/hyperledger/fabric@v1.4.1
```

### Gitlab 仓库没开启https

go mod 默认使用 go get 下载依赖，而 go get 默认使用 https，如果 Gitlab 仓库没有启用 https，需要使用 `-insecure` 让go get走http。

问题：

```
GOPROXY="" go get github.com/hyperledger/fabric@v1.4.1
go: 192.168.9.251/hyperledger/fabric@v1.4.1-alpha.11-yx: unrecognized import path "192.168.9.251/hyperledger/fabric" (https fetch: Get https://192.168.9.251/hyperledger/fabric?go-get=1: dial tcp 192.168.9.251:443: connect: connection refused)
go: error loading module requirements
```

方案：

```
GOPROXY="" go get -insecure github.com/hyperledger/fabric@v1.4.1
```

> 注解：遇到问题时，使用 `go get -v` 可以看到更多信息，有助分析问题。

### Go Modules 代理

由于某些网络原因，国内下载 Github 等处的依赖，不够流程，需要设置代理，不同版本的设置如下：

- go1.12
  ```
  $ export GOPROXY=https://goproxy.cn
  ```

- go1.13
  ```
  $ export GOPRIVATE=192.168.9.251
  $ export GOPROXY=https://goproxy.cn,direct
  ```

### 私有仓库

如果仓库设置为私有，这要求用户必须登录才能访问仓库。

Go Modules 默认使用 go get 下载依赖，go get 利用 https 或者 http, 但下载过程没有设置用户名和密码的地方，下载依赖时，可能遇到一下错误：

- connection refused
- unkown revision

可以通过设置Github/Gitlab Access Token结果，通过token的方式，访问仓库，token的获取方式为，登录Gitlab仓库，进入以下页面：

Gitlab User Setting -> Access Tokens

在此页面复制下顶端的 `Your New Personal Access Token`, 然后填写token名字和勾选下方的权限进行创建 Token。


然后执行以下命令：

```bash
git config --global \
url."http://oauth2:${your_access_token}@ip_address_or_domain".insteadOf \
"http://ip_address_or_domain"
```

后面再去 go get 的时候，就可顺利下载依赖。