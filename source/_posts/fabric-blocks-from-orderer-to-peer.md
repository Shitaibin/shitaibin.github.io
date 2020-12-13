---
title: Fabric 1.4源码解读 8：Orderer和Peer的交互
date: 2019-12-17 20:14:34
tags: ['Fabric', '区块链']
---


Peer与Orderer的交互主要是组织的Peer主节点从Orderer获取区块，本文就来介绍，Peer是如何从Orderer获取区块的，顺带介绍为何Peer从Orderer获取的区块“好慢”。

## 网络拓扑


假设存在如下的Fabric网络拓扑情况，本文使用此拓扑进行介绍Orderer到Peer的区块传播情况：

网络中存在两家组织：Org1和Org2，它们分别拥有Peer1作为主节点，连向了排序服务的Orderer1节点。

网络中存在2个应用channel：channel1和channel2，它们的账本分别是channel1 ledger和channel2 ledger，Org1和Org2都加入了这2个channel。

**channel间是隔离的，所以Peer和Orderer对不同的channel都会分别处理**。

## 宏观视角


下图展示了Orderer向Peer传递区块的宏观视角，能够展示**多个通道在Orderer和Peer间传递区块的情况**：
1. Orderer上有2个通道的账本，每个Peer分别有2个Deliver Server对应2个通道的账本，从账本读取区块，发送给Peer。
1. 每个Peer有2个Deliver Client，也对应2个通道，接收Orderer发来的区块，加入到缓冲区Payloads Buffer，然后再从Payloads Buffer中提取区块，验证后写入对应的通道账本。

![](https://lessisbetter.site/images/2019-12-spread-of-blocks-new.png)

后面，介绍区块同步某个通道区块的情况。

## 单通道区块同步

**Peer利用Deliver从Orderer获取区块**，就像SDK利用Deliver从Peer获取区块一样，Deliver服务端的处理是一样的，Deliver客户端的处理就由SDK、Peer自行处理了。

Deliver本质是一个事件订阅接口，Leading Peer启动后，会为每个通道，分别向Orderer节点注册**区块事件**，并且指定结束的区块高度为`uint`类型的最大值，这是为了不停的从orderer获取区块。

通过建立的gRPC连接，Orderer源源不断的向Peer发送区块，具体流程，如下图所示：
1. Orderer调用`deliverBlock`函数，该函数是循环函数，获取区块直到指定高度。
1. 每当有新区块产生，`deliverBlock`能利用`NextBlock`从通道账本中读到最新的区块，如果没有最新区块，`NextBlock`会阻塞。
1. `deliverBlock`把获取的区块封装成区块事件，发送给Peer（写入到gRPC缓冲区）。
1. Peer从gRPC读到区块事件，把区块提取出来后，加入到**Payloads Buffer**，Payloads Buffer默认大小为200（通过源码和日志发现，Payloads Buffer实际存储202个区块），如果Orderer想向Peer发送更多的区块，必须等Payloads Buffer被消费，有空闲的位置才可以。
1. `deliverPayloads`为循环函数，不断**消费**Payloads Buffer中的区块，执行区块验证，添加区块剩余元数据，最后写入通道账本。
1. 写通道账本包含区块写入区块账本，修改世界状态数据库，历史索引等。


![](https://lessisbetter.site/images/2019-12-orderer-to-peer.png)


## 为何Peer从Orderer获取区块慢？

在性能测试过程中，我们发现Orderer排序完成后，Peer还在不断的从Orderer获取区块，而不是所有排序后的区块都先发送给Peer，Peer缓存起来，慢慢去验证？

上面提到Orderer向Peer发送的区块，Peer收到后先存到Payloads Buffer中，Buffer有空闲位置的时候，Orderer发送的区块才能写入Buffer，deliverBlock 1次循环才能完成，才可以发送下一个区块。

但Payloads Buffer大小是有限的，当Buffer满后，Orderer发送区块的操作也会收到阻塞。

我们可以把Orderer和Peer间发送区块可以抽象一下，它们就是**生产者-消费者模型**，它们中间是缓冲区，Orderer是生产者，向缓冲区写数据，Peer是消费者，从缓冲区读数据，缓冲区满了会阻塞生产者写数据。

所以**Orderer向Peer发送数据的快慢，取决消费者的速度，即取决于deliverPayloads处理一个区块的快慢**。

deliverPayloads慢在把区块写入区块账本，也就是写账本，成了整个网络的瓶颈。

## 为何不让Peer缓存所有未处理的区块？

从我们测试的情况看，Orderer排序的速度远快于Peer，Peer和Orderer的高度差可以达到10万+，如果让Peer来缓存这些区块，然后再做处理是需要耗费大量的空间。

在生产者-消费者模型中，只需要要消费者时刻都有数据处理即可。虽然Orderer和Peer之间是网络传输，测试网络比较可靠，传输速度远比Peer处理区块要快。

Payloads Buffer可以让网络传输区块和Peer处理区块并行，这样缩短了一个区块从Orderer中发出，到Peer写入区块到账本的总时间，提升Fabric网络整体性能。
