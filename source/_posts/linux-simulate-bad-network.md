---
title: Linux内网测试环境模拟网络丢包和延时
date: 2019-05-18 15:37:05
tags: ['Linux']
---



> 本文源自同事分享，在此基础之上做简要修改而成。

Linux下有2traffic control（简写TC）和netem这2个工具。Netem 是 Linux 2.6 及以上内核版本提供的一个网络模拟功能模块，该功能模块可以用来在性能良好的局域网中，模拟出复杂的互联网传输性能，诸如低带宽、传输延迟、丢包等等情况。使用 Linux 2.6 (或以上) 版本内核的很多发行版 Linux 都开启了该内核功能，比如Fedora、Ubuntu、Redhat、OpenSuse、CentOS、Debian等等。TC可以用来控制 netem 的工作模式，可完成如下功能：（故障模拟） 模拟时延，丢包，重复包，乱序，控制带宽等。

本文介绍简单的使用方法，更详细的介绍及用法见：[wiki:network emulation](<https://wiki.linuxfoundation.org/networking/netem>)。

# TC实现原理

TC用于Linux内核的流量控制，主要是通过在输出端口处建立一个队列来实现流量控制。接收包从输入接口（Input Interface）进来后，经过流量限制（Ingress Policing）丢弃不符合规定的数据包，由输入多路分配器（Input De-Multiplexing）进行判断选择：如果接收包的目的是本主机，那么将该包送给上层处理；否则需要进行转发，将接收包交到转发块（Forwarding Block）处理。转发块同时也接收本主机上层（TCP、UDP等）产生的包。转发块通过查看路由表，决定所处理包的下一跳。然后，对包进行排列以便将它们传送到输出接口（Output Interface）。一般我们只能限制网卡发送的数据包，不能限制网卡接收的数据包，所以我们可以通过改变发送次序来控制传输速率。Linux流量控制主要是在输出接口排列时进行处理和实现的。

# 使用方法

以下模拟命令可配合使用，实现即延迟又丢包等情况。

## 模拟延迟传输

```bash
tc qdisc add dev eth0 root netem delay 100ms
```

该命令将 eth0 网卡的传输设置为延迟100毫秒发送。
更真实的情况下，延迟值不会这么精确，会有一定的波动，我们可以用下面的情况来模拟出带有波动性的延迟值：

````bash
tc qdisc add dev eth0 root netem delay 100ms 50ms
````

该命令将 eth0 网卡的传输设置为延迟 100ms ± 50ms （50 ~ 150 ms 之间的任意值）发送。
还可以更进一步加强这种波动的随机性：

```bash
tc qdisc add dev eth0 root netem delay 100ms 50ms 30%
```

该命令将 eth0 网卡的传输设置为 100ms ，同时，大约有 30% 的包会延迟 ± 50ms 发送。
　　

## 模拟网络丢包

```bash
tc qdisc add dev eth0 root netem loss 10%
```

该命令将 eth0 网卡的传输设置为随机丢掉 10% 的数据包。
也可以设置丢包的成功率：

```bash
tc qdisc add dev eth0 root netem loss 10% 30%
```

## 模拟包重复

```bash
tc qdisc add dev eth0 root netem duplicate 10%
```

该命令将 eth0 网卡的传输设置为随机产生 10% 的重复数据包 。

## 模拟包损坏

```bash
tc qdisc add dev eth0 root netem corrupt 1%
```

## 模拟包乱序

```bash
tc qdisc change dev eth0 root netem delay 10ms reorder 10% 50%
```

该命令将 eth0 网卡的传输设置为:有 10% 的数据包（50%相关）会被立即发送，其他的延迟 10 秒。

## 删除设备及显示设置

显示配置：

```bash
tc qdisc sh dev eth0
```

删除配置：

```bash
tc qd del dev eth0 root
```

# 参考资料

[Linux网络流量控制工具—Netem](<https://www.cnblogs.com/fsw-blog/p/4788036.html>)


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/05/18/linux-simulate-bad-network/](http://lessisbetter.site/2019/05/18/linux-simulate-bad-network/)

<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="https://lessisbetter.site/images/2019-01-article_qrcode.jpg" style="border:0"  align=center />