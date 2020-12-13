---
title: Fabric 1.4源码解读 7：Orderer架构解读
date: 2019-11-21 20:07:54
tags: ['Fabric', '区块链']
---


## Orderer介绍

排序服务由一组**排序节点**组成，它接收客户端提交的交易，把交易打包成区块，确保排序节点间达成一致的区块内容和顺序，提供区块链的**一致性**服务。


![](http://img.lessisbetter.site/2019-11-fabric-orderer-network.png)
> 图片源自《区块链原理、设计与应用》，当时Fabric还不支持raft

排序服务所提供的一致性，依赖**确定性的共识算法**，而非比特币、以太坊等公有链，所采用的概率性共识算法。确定性的共识算法是区块上链，即不可修改。Fabric所采用的共识算法有Solo、Kafka、EtcdRaft。

客户端**通过Broadcast接口向Orderer提交背书过的交易**，客户端（此处广义指用户客户端和**Peer节点**）**通过Deliver接口订阅区块事件，从Orderer获取区块**。

更多的排序服务介绍请参考这篇官方文档[排序服务](https://hyperledger-fabric-cn.readthedocs.io/zh/latest/orderer/ordering_service.html)。

## 架构

![Architecture of Orderer](http://img.lessisbetter.site/2019-11-arch-of-orderer.png)

> 本图依赖 Fabric 1.4 源码分析而得


Orderer由：多通道、共识插件、消息处理器、本地配置、区块元数据、gRPC服务端、账本等组成，其中gRPC中的Deliver、Ledger是通用的（Peer也有），其余都是Orderer独有的。

### 多通道

Fabric 支持多通道特性，而Orderer是多通道的核心组成部分。多通道由Registrar、ChainSupport、BlockWriter等一些重要部件组成。

Registrar是所有通道资源的汇总，访问每一条通道，都要经由Registrar，更多信息请看[Registrar](http://lessisbetter.site/2019/11/18/fabric-orderer-structs/#Registrar)。

ChainSupport代表了每一条通道，它融合了一条通道所有的资源，更多信息请看[ChainSupport](http://lessisbetter.site/2019/11/18/fabric-orderer-structs/#ChainSupport)。

BlockWriter 是区块达成共识后，Orderer写入区块到账本需要使用的接口。

### 共识插件

Fabric的共识是插件化的，抽象出了Orderer所使用的共识接口，任何一种共识插件，只要满足给定的接口，就可以配合Fabric Orderer使用。

当前共识有3种插件：Solo、Kafka、EtcdRaft。Solo用于实验环境，Kafka和EtcdRaft用于生产环境，Kafka和EtcdRaft都是CFT算法，但EtcdRaft比Kafka更易配置。

EtcdRaft实在Fabric 1.4开始引入的，如果之前的生产环境使用Kafka作为共识，可以遵循Fabric给的指导，把Kafka共识，迁移到Raft共识。


### gRPC通信


Orderer只有2个gRPC接口：
- Broadcast：用来接收客户端提交的待排序交易
- Deliver：客户端（包括Peer节点）用来从Orderer节点获取已经达成一致的区块

其中，Broadcast是Orderer独有的，而Devliver是通用的，因为客户端也可以利用Deliver接口从Peer节点获取区块、交易等。

关于Broadcast和Orderer更多介绍可以参考杨保华的2篇笔记：
- [Orderer 节点 Broadcast 请求的处理](https://github.com/yeasy/hyperledger_code_fabric/blob/master/process/orderer_broadcast.md)
- [Orderer 节点 Deliver 请求的处理](https://github.com/yeasy/hyperledger_code_fabric/blob/master/process/orderer_deliver.md)。
### Local Config

用来解析orderer节点的配置文件: `orderer.yaml`，并保存入内存。

该配置文件中的配置，是节点本地的配置，不需要Orderer节点间统一的配置，因此不需要上链，相关配置有：
- 网络相关配置
- 账本类型、位置
- raft文件位置
- ...

而上链的配置，被称为通道配置，需要使用配置交易进行更新，这部分配置，写在`configtx.yaml`中，和Orderer相关的有：
- 共识类型
- 区块大小
- 切区块的时间
- 区块内交易数
- 各种共识的相关配置
- ...


### Metadata

区块中有4个元数据：
- 区块签名，存放orderer对区块的SignatureHeader
- 最新配置区块的高度，方便获取当前通道最新配置
- 交易过滤，为数组，存放区块内所有交易的有效性，使用数字代表无效的原因，由验证交易的记账节点填写
- orderer相关元数据，不同的共识类型，该元数据不同

区块Header中记录了Data.Hash()，Data是所有交易后序列化的结果，但不包含区块元数据，所以区块元数据是可以在产生区块后修改的。即，即使元数据上链了，但这数据是可以修改的，只不过修改也没有什么意义。

### MsgProcessor

orderer收到交易后需要对交易进行多项检查，不同的通道可以设置不同的MsgProcessor，也就可以进行不同的检查。

当前Processor分2个：
- 应用通道的叫StandardChannel
- 系统通道的叫SystemChannel

StandardChannel会对交易进行以下检查：
- 交易内容不能为空
- 交易大小不能超过区块大小最大值（默认10MB）
- 交易交易签名不符合签名策略
- 签名者证书是否过期

SystemChannel只比StandardChannel多一项：系统配置检查，用来检查以下交易中包含的配置，配置项是否有缺失，或者此项配置是否允许更新等。

### BlockCutter

BlockCutter用来把收到的交易分成多个组，每组交易会打包到一个区块中。而分组的过程，就是切块，每组交易被称为一个Batch，它有一个缓冲区用来存放待切块交易。

切块有3个可配置条件：
- 缓冲区内交易数，达到区块包含的交易上限（默认500）
- 缓冲区内交易总大小，达到区块大小上限（默认10MB）
- 缓冲区存在交易，并且未出块的时间，达到切块超时时间（默认2s）

切块有1个不可配置条件：
- 缓冲区收到配置交易，配置交易要放到单独区块，如果缓冲区有交易，缓冲区已有交易会切到1个区块

超多刚接触Fabric的人有这样一个疑问：排序节点是按什么规则对交易排序的？

按什么顺序对交易排序并不重要，只要交易在区块内的顺序是一致的，然后所有记账节点，按交易在区块内的顺序，处理交易，最后得到的状态必然是一致的，这也是区块链保持一致性的原理。

再回过头来说一下实现是什么顺序：哪个交易先写入BlockCutter的缓冲区，哪个交易就在前面，仅此而已。

### BlockWriter

Orderer的BlockWriter是基于common/ledger实现的，**它用来保存区块文件**，不包含状态数据库等其他数据库，其中有3类区块文件:ram，json和file，file是Orderer和Peer都可使用的，另外2个只能Orderer使用。

BlockWriter用来向Peer的账本追加区块，但追加区块之前，还需要做另外1件事情，设置区块的元数据。

区块元数据包含：
- 区块签名，存放orderer对区块的SignatureHeader
- 最新配置区块的高度，方便获取当前通道最新配置
- 交易过滤，为数组，存放区块内所有交易的有效性，使用数字代表无效的原因，由验证交易的记账节点填写
- orderer相关元数据，不同的共识类型，该元数据不同

但此时只设置其中的3个：区块签名、配置区块高度、orderer相关的元数据。因为交易的有效性在记账节点检查后才能设置。

**为何不在创建区块的时候就设置这些元数据信息，而是在区块经过共识之后？**

共识的过程会传播区块，只让区块包含必要的信息，可以减少区块大小，降低通信量。但元数据占用大小非常小，所以这未必是真实原因。

BlockWriter还有**另外一个功能：根据一个Batch创建下一个高度的区块**。一个区块包含了：
- Header：区块高度、前一个区块Hash、Data的哈希值
- Data：被序列化的交易列表
- Metadata：区块元数据

Header只记录Data的哈希值，不包含Metadata哈希值，这样的目的是，在区块创建之后，仍能修改区块。

## Orderer节点启动

根据Fabric 1.4源码梳理Orderer启动步骤：
- 加载配置文件
- 设置Logger
- 设置本地MSP
- 核心启动部分：
    - 加载创世块
    - 创建账本工厂
    - 创建本机gRPCServer
    - 如果共识需要集群(raft)，创建集群gRPCServer
    - 创建Registrar：设置好共识插件，启动各通道，如果共识是raft，还会设置集群的gRPC接口处理函数Step
    - 创建本机server：它是原子广播的处理服务，融合了Broadcast处理函数、deliver处理函数和registrar
    - 开启profile
    - 启动集群gRPC服务
    - 启动本机gRPC服务

启动流程图可请参考杨宝华的笔记[Orderer 节点启动过程](https://github.com/yeasy/hyperledger_code_fabric/blob/master/process/orderer_start.md)，笔记可能是老版本的Fabric，但依然有参考价值。


## Orderer处理交易的流程

### 普通交易在Orderer中的流程

交易是区块链的核心，交易在Orderer中的流程分3阶段：
1. Orderer 的 Broadcast 接口收到来自客户端提交的交易，会获取交易所在的链的资源，并进行首次检查，然后提交给该链的共识，对交易进行排序，最后向客户端发送响应，为下图蓝色部分。
1. 共识实例是单独运行的，也就是说Orderer把交易交给共识后，共识可能还在处理交易，然而Orderer已经开始向客户端发送提交交易的响应。共识如果发现排序服务的配置如果进行了更新，会再次检查交易，然后利用把Pending的交易分割成一组，然后打包成区块，然后共识机制确保各Orderer节点对区块达成一致，最后将区块写入账本。为下图绿色部分。
1. Peer会向Orderer订阅区块事件，每当新区块被Orderer写入账本时，Orderer会把新区块以区块事件的方式，发送给Peer。为下图换色部分。

![](http://img.lessisbetter.site/2019-11-21-orderer-tx-flow.png)

上面提到Orderer和共识实例分别会对交易进行2次检查，这些检查是相同的，为何要进行两次检查呢？

代码如下：ProcessMessage 会调用`ProcessNormalMsg`，对交易进行第一次检查，如果有错误，会向客户端返回错误响应。 SomeConsensurFunc 是一个假的函数名称，但3种共识插件实现，都包含相同的代码片，当消息中 configSeq < seq 时，再次对交易进行检查，如果错误，则丢次此条交易。configSeq是Order函数传入的，即第一次检查交易时的配置号，seq为共识当前运行时的配置号。

```go
func (bh *Handler) ProcessMessage(msg *cb.Envelope, addr string) (resp *ab.BroadcastResponse) {
    // ...
    configSeq, err := processor.ProcessNormalMsg(msg)
    if err != nil {
        logger.Warningf("[channel: %s] Rejecting broadcast of normal message from %s because of error: %s", chdr.ChannelId, addr, err)
        return &ab.BroadcastResponse{Status: ClassifyError(err), Info: err.Error()}
    }
    // ...
    err = processor.Order(msg, configSeq)
    // ...
}

func SomeConsensurFunc() {
    // ...
    if msg.configSeq < seq {
        _, err = ch.support.ProcessNormalMsg(msg.normalMsg)
        if err != nil {
            logger.Warningf("Discarding bad normal message: %s", err)
            continue
        }
    }
    // ...
}
```

我认为如此设计的原因，考量如下：
共识插件应当尽量高效，orderer尽量把能做的做掉，把不能做的交给共识插件，而交易检查就是orderer能做的。共识插件只有在排序服务配置更新后，才需要重新检查交易，以判断是否依然满足规则。排序服务的配置通常是比较稳定的，更新频率很低，所以进行2次校验的频率也是非常低。这种方式，比只在共识插件校验，会拥有更高的整体性能。

### 配置交易在Orderer中的流程

配置交易可以用来创建通道、更新通道配置，与普通交易的处理流程总体是相似的，只不过多了一些地方或者使用不同的函数，比如：
- 交易检查函数不是ProcessNormalMsg，而是ProcessConfigMsg
- 配置交易单独打包在1个区块
- 配置交易写入账本后，要让配置生效，即Orderer应用最新的配置
- ...

### 使用Raft共识，交易在Orderer中的流程

上面2中流程都是与具体共识算法无关的，这里补充一个Raft共识的。

![](http://img.lessisbetter.site/2020-01-orderer-using-raft.png)

使用Raft共识的链处理交易包含了上图中的4步：
- 交易：处理交易
- 区块：创建区块
- Raft：使用Raft对区块达成共识
- 账本：写区块元数据，把区块写入到账本

如果把图中提到的：转发和Raft去掉，就是以Solo为共识的链的过程。

下图是更加细化一层的，如果看不懂，建议先读下[Etcd Raft架构设计和源码剖析2：数据流](http://lessisbetter.site/2019/08/22/etcd-raft-source-data-flow/)这篇文章。


![](http://img.lessisbetter.site/2020-01-fabric-order-with-etcdraft.png)

红色圈出来的是etcd/raft的实现，蓝色圈出来的是Fabric使用raft为共识的部分，外面的Broadcast、Deliver是属于Orderer但不属于某条链。

这张图和etcd与raft交互没有太多不同，只有2个地方：
1. chains要把交易转化为区块，再交给raft去共识
1. chains的Apply并不是去修改状态机，而是把取消写到账本

## 源码简介

Orderer的代码位于`fabric/orderer`，其目录结构如下，标注了每个目录结构的功能：

```
➜  fabric git:(readCode) ✗ tree -L 2 orderer
orderer
├── README.md
├── common
│   ├── blockcutter 缓存待打包的交易，切块
│   ├── bootstrap 启动时替换通道创世块
│   ├── broadcast orderer的Broadcast接口
│   ├── cluster （Raft）集群服务
│   ├── localconfig 解析orderer配置文件orderer.yaml
│   ├── metadata 区块元数据填写
│   ├── msgprocessor 交易检查
│   ├── multichannel 多通道支持：Registrar、chainSupport、写区块
│   └── server Orderer节点的服务端程序
├── consensus 共识插件
│   ├── consensus.go 共识插件需要实现的接口等定义
│   ├── etcdraft raft共识插件
│   ├── inactive 未激活时的raft
│   ├── kafka kafka共识插件
│   ├── mocks 测试用的共识插件
│   └── solo solo共识插件
├── main.go orderer程序入口
├── mocks
│   ├── common
│   └── util
└── sample_clients orderer的客户端程序样例
    ├── broadcast_config
    ├── broadcast_msg
    └── deliver_stdout

23 directories, 3 files
```

阅读Orderer源码，深入学习Orderer的时候，建议以下顺序：
- 核心的数据结构，主要在multichannel、consensus.go：[Fabric 1.4源码解读 6：Orderer核心数据结构](http://lessisbetter.site/2019/11/18/fabric-orderer-structs/)
- Orderer的启动
- Broadcast接口
- msgprocessor
- 通过Solo掌握共识插件需要做哪些工作
- 切块：blockcutter
- 写区块：BlockWriter、metadata


## 总结

本文从宏观的角度介绍了Orderer的功能、核心组成，以及交易在Orderer中的流程，Peer如何从Orderer获取区块。



