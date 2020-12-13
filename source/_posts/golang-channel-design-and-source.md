---
title: 深入理解channel：设计+源码
date: 2019-03-03 15:32:15
tags: ['Go']
---

channel是大家在Go中用的最频繁的特性，也是Go最自豪的特性之一，你有没有思考过：
- Why：为什么要设计channel？
- What：channel是什么样的？
- How：channel是如何实现的？

这篇文章，就来回答这3个问题。

### channel解决什么问题？


在Golang诞生之前，各编程语言都使用多线程进行编程，但多线程复杂、混乱、难以管理，对开发者并不是多么友好。

Golang是Google为了解决高并发搜索而设计的，它们想使用简单的方式，高效解决并发问题，最后做成了，然后又把Golang开源了出来，以及到处推广，所以Golang自从诞生之初，就风风火火。

从Golang文档中，我们可以知道，为啥Golang设计了channel，以及channel解决了什么问题？

[Go Concurrency Patterns:](https://golang.org/doc/#go_concurrency_patterns)
> Concurrency is the key to designing high performance network services. Go's concurrency primitives (goroutines and channels) provide a simple and efficient means of expressing concurrent execution. In this talk we see how tricky concurrency problems can be solved gracefully with simple Go code.

Golang使用`goroutine`和`channel`简单、高效的解决并发问题，**channel解决的是goroutine之间的通信**。



### channel是怎么设计的？

我们以为channel是一个通道：

![](http://img.lessisbetter.site/2019-03-pipeline.jpeg)

实际上，channel的内在是这样的：

![](http://img.lessisbetter.site/2019-03-channel_design.png)

channel设计涉及的数据结构很简单，这就是**channel的本质**：
- 基于数组的循环队列，有缓冲的channel用它暂存数据
- 基于链表的单向队列，用于保存阻塞在此channel上的goroutine
- 锁，用于实现goroutine对channel并发安全，保证某一时刻只有1个goroutine操作channel，


我本来想自己码一篇channel的设计文章，但已经有大牛：Kavya深入分析了Channel的设计，我也相信自己写的肯定不如他好，所以我把**Kavya在Gopher Con上的PPT推荐给你，如果你希望成为Go大牛，你一定要读一下，现在请收藏好**。

Kavya在Gopher Con上的演讲主题是：理解channel，他并不是教你如何使用channel，而是**把channel的设计和goroutine的调度结合起来，从内在方式向你介绍**。这份PPT足足有80页，包含了大量的动画，非常容易理解，你会了解到：
- channel的创建
- 各种场景的发送和接收
- goroutine的调度
- goroutine的阻塞和唤醒
- channel和goroutine在select操作下

Kavya的PPT应该包含了channel的80%的设计思想，但也有一些缺失，需要你阅读源码：
- channel关闭时，gorontine的处理
- 创建channel时，不同的创建方法
- 读channel时的非阻塞操作
- ...

PPT在此：[Understanding Channels](https://speakerdeck.com/kavya719/understanding-channels)，如果你有心，还可以在这个网站看到Kavya关于goroutine调度的PPT，福利哦😝。(访问不了请翻墙，或阅读原文从博客文章最下面看Github备份)

微信二维码跳转：
![](http://img.lessisbetter.site/2019-03-channel_design_qrcode.png)


### channel是怎么实现的？

[chan.go](https://github.com/golang/go/blob/master/src/runtime/chan.go)是channel的主要实现文件，只有700行，十分佩服Go团队，**实现的如此精简，却发挥如此大的作用**！！！

看完Kavya的PPT，你已经可以直接看channel的源码了，如果有任何问题，思考一下你也可以想通，如果有任何问题可博客文章留言或公众号私信进行讨论。

另外，推荐一篇在Medium（国外高质量文章社区）上获得500+赞的源码分析文章，非常详细。

文章链接：[Diving deep into the golang channels](https://codeburst.io/diving-deep-into-the-golang-channels-549fd4ed21a8)

微信二维码跳转：

![](http://img.lessisbetter.site/2019-03-channel_source_qrcode.png)

### 我学到了什么？

阅读channel源码我学到了一些东西，分享给大家。

channel的4个特性的实现：
- channel的goroutine安全，是通过mutex实现的。
- channel的FIFO，是通过循环队列实现的。
- channel的通信：在goroutine间传递数据，是通过仅共享hchan+数据拷贝实现的。
- channel的阻塞是通过goroutine自己挂起，唤醒goroutine是通过对方goroutine唤醒实现的。


channel的其他实现：
- 发送goroutine是可以访问接收goroutine的内存空间的，接收goroutine也是可以直接访问发送goroutine的内存空间的，看`sendDirect`、`recvDirect`函数。
- 无缓冲的channel始终都是直接访问对方goroutine内存的方式，把手伸到别人的内存，把数据放到接收变量的内存，或者从发送goroutine的内存拷贝到自己内存。省掉了对方再加锁获取数据的过程。
- 有缓冲的channel在缓冲区空时，接收数据的goroutine无法读数据，会把自己阻塞放到接收链表，当发送goroutine到来时，发送goroutine直接使用`sendDirect`把数据放到第一个阻塞的接收goroutine，然后把它唤醒。`recvDirect`在有缓冲区通道的情况，反过来。
- 接收goroutine读不到数据和发送goroutine无法写入数据时，是把自己挂起的（创建一个节点，插入到双向链表的尾部），这就是channel的阻塞操作。阻塞的接收goroutine是由发送goroutine唤醒的，阻塞的发送goroutine是由接收goroutine唤醒的，看`gopark`、`goready`函数在`chan.go`中的调用。
- 接收goroutine当channel关闭时，读channel会得到0值，并不是channel保存了0值，而是它发现channel关闭了，把接收数据的变量的值设置为0值。
- channel的操作/调用，是通过reflect实现的，可以看reflect包的`makechan`, `chansend`, `chanrecv`函数。
- channel关闭时，所有在channel上读数据的g都会收到通知。其实并非关闭channel的g给每个接收的g发送信号，而是关闭channel的g，把channel关闭后，会唤醒每一个读取channel的g，它们发现channel关闭了，把待读的数据设置为零值并返回，所以这并非一次性的事件通知，。看到这种本质，你应当理解下面这种奇淫巧计：这种“通知”效果并不一定需要接收数据的g先启动，先把channel关闭了，然后启动读取channel的g依然是可行的，代码无需任何改变，任何逻辑也都无需改变，它会发现channel关闭了，然后走原来的逻辑。


如果阅读[chan_test.go](https://github.com/golang/go/blob/master/src/runtime/chan_test.go)还会学到一些骚操作，比如：

```go
if <-stopCh {
    // do stop
}
```

而不是写成：
```go
if stop := <-stopCh; stop {
    // do stop
}
```

这就是关于channel的设计和实现的分享，希望你通过Kavya的PPT和代码阅读能深入了解channel。

### 链接


- chan.go：https://github.com/golang/go/blob/master/src/runtime/chan.go
- chan_test.go：https://github.com/golang/go/blob/master/src/runtime/chan_test.go
- Understanding channels在Github的备份: https://github.com/Shitaibin/shitaibin.github.io/blob/hexo_resource/files/GopherCon_v10.0.pdf


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://www.lessisbetter.site/2019/03/03/golang-channel-design-and-source/](http://www.lessisbetter.site/2019/03/03/golang-channel-design-and-source/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="http://img.lessisbetter.site/2019-01-article_qrcode.jpg" style="border:0"  align=center />