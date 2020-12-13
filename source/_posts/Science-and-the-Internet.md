---
title: 让终端科学上网
date: 2018-09-06 20:35:40
tags: ['Mac']
---



# 前言

科学上网，为祖国建设添砖加瓦。

- 教你浏览器科学上网，获取学习资料。
- 教你终端科学上网，获取学习资料。



# 软件列表

- [Shadowsocks](https://github.com/shadowsocks/shadowsocks-iOS/wiki/Shadowsocks-for-OSX-%E5%B8%AE%E5%8A%A9):sock5代理
- proxychains-ng:为终端命令设置SOCKS5代理

<!--more-->

# shadowsocks

[ShadowsocksX-NG-R8](https://raw.githubusercontent.com/VeniZ/ShadowsocksX-NG-R8-Bakup/master/ShadowsocksX-NG-R8.dmg)是Mac版本，可单独使用，不需要配置Chrome代理插件，使用用的PAC白名单上网模式，可以减少很多配置，并且体验更好。

最厉害的是，可以把一切TCP转为SOCKS5，也就是说http和https也都可以转换的，只配置一个socks5代理就行了。

设置步骤：
1. 添加服务器信息。
2. 设置全局模式
3. 更新PAC列表
4. 访问Google搜索
5. 设置为PAC模式

![](https://lessisbetter.site/images/2019-01-ss-ng.png)


经过以上配置，浏览器可以直接科学上网了，如果让终端和其他服务器上网，可设置Shadowsocks的http代理和socks5代理。

## 自定义过滤规则

从网上更新来的PAC，有些网址并没有走代理，这样访问速度依然很慢，比如我经常访问Fabric的网站，每个网页都也2s以上才能刷新出来，刷新完成就要更久了。

SSR提供了用户自定义PAC的方法，只要把自定义规则黏贴在里面就可以了：

![](https://lessisbetter.site/images/2019-08-ssr-user-pac.png)


自定义PAC编写规则，下面的`.hyperledger.org`，所有`hyperledger.org`网站的连接都会走`remote proxy`，注意前面的`.`不要少了，这个正则规则可以匹配`*.hyperledger.org`以及`hyperledger.org`本身。

```
.hyperledger.org remoteproxy
```


## 开启HTTP代理

点击状态栏shadowsocks图标，【HTTP代理设置...】是配置Http代理。【高级设置...】是socks5代理设置。

![](https://lessisbetter.site/images/2019-07-ss_http.png)


**http代理支持http和https2个协议的代理**，IP设置为0.0.0.0就可以为其他机器做http和https代理，如果只有本机用，可以使用默认的127。

![](https://lessisbetter.site/images/2019-07-ss-http-set.png)

## 开启SOCKS5代理

socks5的ip设置同http代理。

![](https://lessisbetter.site/images/2019-07-ss-socks5.png)


# 终端科学上网

## 用proxychains做socks5代理


作为研发，天天和国外资源打交道，必需让终端也能科学上网，不然下载个、更新软件，或者下载源码就吐血了。

用下来最稳定省心的办法是proxychains-ng，优点突出：

- 必要特性：稳定可行
- 加分特性：代理只局限于使用的软件，不会污染整个系统的代理



安装proxychains-ng

```
brew install proxychains-ng
```

运行会列出配置文件位置

```
proxychains4 wget www.google.com
[proxychains] config file found: /usr/local/etc/proxychains.conf
[proxychains] preloading /usr/local/Cellar/proxychains-ng/4.13/lib/libproxychains4.dylib
```

打开配置文件：`/usr/local/etc/proxychains.conf`。

- dynamic_chain，取消这行注释
- strict_chain， 注释
- 最后一行添加`socks5 127.0.0.1 1086`

**验证科学上网的唯一标准：能用wget下载google主页**，什么`curl ip.cn`这种不一定准，虽然显示你的是国外IP了，说明这次`curl`走了代理，但不代表你能使用wget下载，能更新源码。

```
➜  t proxychains4 wget www.google.com
[proxychains] config file found: /usr/local/etc/proxychains.conf
[proxychains] preloading /usr/local/Cellar/proxychains-ng/4.13/lib/libproxychains4.dylib
[proxychains] DLL init: proxychains-ng 4.13
--2018-09-06 20:24:26--  http://www.google.com/
正在解析主机 www.google.com (www.google.com)... 224.0.0.1
正在连接 www.google.com (www.google.com)|224.0.0.1|:80... [proxychains] Strict chain  ...  127.0.0.1:1080  ...  www.google.com:80  ...  OK
已连接。
已发出 HTTP 请求，正在等待回应... 200 OK
长度：未指定 [text/html]
正在保存至: “index.html.10”

index.html.10                    [ <=>                                           ]  11.11K  --.-KB/s  用时 0s

2018-09-06 20:24:27 (59.9 MB/s) - “index.html.10” 已保存 [11375]
```

为了方便使用proxychains可以设置命令昵称，比如我的：

```
alias py4="proxychains4"
alias wget="py4 wget"
```

使用这种方式还遇到过某些https就是连接超时的情况，比如`google.golang.org`，可以这么解决：

```
proxychains4 zsh
```

这样会新启动一个zsh会话，当前会话的所有连接都转换为socks5代理。


## 设置环境变量

如果不想安装proxychain，另外一种简便的方式是，设置全局的http和https代理，建议不要加到`.bash_profile`等，不然始终都走代理了，建议在使用的时候，设置代理即可，可以把羡慕代码直接黏贴到终端，但先换成自己的SS http代理服务的IP和端口。

```bash
export http_proxy="http://192.168.102.143:1087"
export https_proxy="http://192.168.102.143:1087"
```

使用`export http_proxy=127.0.0.1:1087`，大多数情况也没毛病，但由此在Docker里更新系统时，IP和端口识别不正确的情况，建议使用带协议头的方式，还有就是使用主机实际的IP，不要使用127或者localhost，因为在docker里的命令走代理的时候，可能会连接到docker本身的端口，导致连接被拒绝。

另外，`https_proxy="http://192.168.102.143:1087`，这让https_proxy实际走的是http代理，如果不这样设置，访问goolge某些网站的时候，可能会遇到超时、握手失败的情况。