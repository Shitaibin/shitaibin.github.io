---
title: 为什么PBFT需要View Changes
date: 2020-03-22 14:10:53
tags: ['区块链','一致性','共识算法', 'PBFT']
---

## 前言

在当前的PBFT资料中，尤其是中文资料，多数都在介绍PBFT的3阶段消息过程，很少提及View Changes（视图切换），View Changes对PBFT的重要性，如同Leader Election对Raft的重要性，它是一个一致性算法中，不可或缺的部分。

作者为大家介绍下，为什么View Changes如此重要，即为什么PBFT需要View Changes，以及View Changes的原理。


## 为什么PBFT需要View Changes

一致性算法都要提供：
- safety ：原意指不会出现错误情况，一致性中指操作是正确的，得到相同的结果。
- liveness ：操作过程能在有限时间内完成。

![一致性协议需要满足的特性](https://lessisbetter.site/images/2020-03-consistency-property.png)

**safety通常称为一致性，liveness通常称为可用性**，没有liveness的一致性算法无法长期提供一致性服务，没有safety的一致性算法称不上一致性算法，所以，所有的一致性算法都在做二者之间的折中。


所以对一致性和可用性不同的要求，就出现了你常听见的ACID原理、CAP理论、BASE理论。

PBFT作为一个一致性算法，它也需要提供一致性和可用性。在[为什么PBFT需要3个阶段消息](https://lessisbetter.site/2020/03/15/why-pbft-needs-3-phase-message/)中，介绍了PBFT算法的如何达成一致性，并且请求可以在有限时间内达成一致，客户端得到响应，也满足可用性。

但没有介绍，当遇到以下情况时，是否还能保住一致性和可用性呢？
1. 主节点是拜占庭节点（宕机、拒绝响应...）
2. 主节点不是拜占庭节点，但非拜占庭副本节点参与度不足，不足以完成3阶段消息
3. 网络不畅，丢包严重，造成不足以完成3阶段消息
4. ...

在以上场景中，**新的请求无法在有限时间内达成一致，老的数据可以保持一致性，所以一致性是可以满足的，但可用性无法满足**。必须寻找一个方案，恢复集群的可用性。

**PBFT算法使用View Changes，让集群重新具有可用性**。通过View Changes，可以选举出新的、让请求在有限时间内达成一致的主节点，向客户端响应，从而满足可用性的要求。

让集群重新恢复可用，需要做到什么呢？**让至少f+1个非拜占庭节点迁移到，新的一致的状态**。然后这些节点，运行3阶段消息协议，处理新的客户端请求，并达成一致。

## 不同版本的View Changes协议有什么不同？

PBFT算法有1999年和2001年2个版本：
- 99年：[Practical Byzantine Fault Tolerance](http://pmg.csail.mit.edu/papers/osdi99.pdf)，PBFT初次发表。
- 01年：[Practical Byzantine Fault Tolerance and Proactive Recovery](http://www.pmg.csail.mit.edu/papers/bft-tocs.pdf)，又称PBFT-PR，让PBFT受攻击时，具有主动恢复能力。

PBFT-PR并非只是在PBFT上增加了PR，同时也对PBFT算法做了详细的介绍和改进，View Changes的改进就是其中一项。

PBFT中View Changes介绍比较简单，没有说明以下场景下，View Changes协议如何处理：

- 如果下一个View的主节点宕机了怎么办
- 如果下一个View的主节点是恶意节点，作恶怎么办
- 如果非拜占庭恶意发起View Changes，造成主节点切换怎么办？
- 如果参与View Changes的节点数量不足怎么办

如果，以上场景下，节点处在View Changes阶段，持续的等待下去，就无法恢复集群的可用性。

PBFT-PR中的View Changes协议进行了细化，可以解决以上问题。

## 2001年版本View Changes协议原理

每个主节点都拥有一个View，就如同Raft中每个leader都拥有1个term。不同点是term所属的leader是选举出来的，而View所属的主节点是计算出的： `primary = v % R`，R是运行PBFT协议的节点数量。

View Changes的战略是：当副本节点怀疑主节点无法让请求达成一致时，发起视图切换，新的主节点收集当前视图中已经Prepared，但未Committed的请求，传递到下一个视图中，所有非拜占庭节点基于以上请求，会达到一个新的、一致的状态。然后，正常运行3阶段消息协议。

为什么要包含已经Prepared，但未Committed的请求？如果一个请求，在副本节点i上，已经是Prepared状态，证明至少f+1的非拜占庭节点，已经拥有此请求并赞成请求req在视图v中使用序号n。如果没有问题，不发生视图切换，这些请求可以在有限的时间内达成一致，新的主节点把已经Prepared的请求，带到新的view，并证明给其他节点，请求已经Prepared，那只需1轮Commit就可以达成一致。



### View Changes主要流程简介

对View Changes的流程可以分为2部分：
- View Changes的开端，即每一次View的开始
- View Changes的中间过程，以及View Changes的结束，切换到正常流程

这2部分分别占据了下图的左右两部分。实线代表流程线，虚线代表网络消息。蓝色代表正常操作流程（三阶段消息：Preprepare、Prepare、Commit），青色代表View Changes流程，蓝青相接就是正常流程和View Changes流程切换的地方。

![](https://lessisbetter.site/images/2020-04-09-blueprint-view-changes.png)


View Changes的开端流程是通用的，主节点和副本节点都遵守这一流程：`新视图：v=v+1`，代表一个新的View开始，指向它的每一个箭头，都是视图切换的一种原因。某个副本节点，新视图的开始，还伴随着广播`view-change`消息，告诉其他节点，本节点开启了一个新的视图。

主节点是通过公式算出来的，其余为副本节点，在View Changes流程中，副本节点会和主节点交互，共同完成View Changes过程。副本节点会对收到的`view-change`消息进行检查，然后把一条对应的`view-change-ack`消息发送给主节点，主节点会依赖收到的`view-change`消息和`view-change-ack`消息数量和内容，产生能让所有节点移动到统一状态的`new-view`消息，并且对`new-view`消息进行3阶段共识，即对`new-view`消息达成一致，从而让至少`f+1`个非拜占庭节点达成一致。

### View Changes的开端

View Change的核心因素只有一个：怀疑当前的主节点在有限的时间内，无法达成一致。

具体有4个路径：
1. 正常阶段定时器超时，代表一定时间内无法完成Pre-prepare -> Prepare -> Commit
2. View Changes阶段定时器超时，代表一定时间内无法完成正在进行的View Change
3. 定时器未超时，但有效的view-change消息数量达到f+1个，代表当前已经有f+1个非拜占庭节点发起了新的视图切换，本节点为了不落后，不等待超时而进入视图切换
4. new-view消息不合法，代表当前View Changes阶段的主节点为拜占庭节点

图中【正常阶段定时器超时】被标记为蓝色，是因为它是正常阶段进入视图切换阶段的开端，【有效的view-change消息数量达到f+1个】即有可能是正常阶段的定时器，也有可能是视图切换过程中的定时器，所以颜色没做调整。

### 主副节点主要交互流程 

视图切换过程中有3个消息：view-change消息、view-change-ack消息和new-view消息，下文围绕这3个消息，对主副节点的交互流程做详细介绍。

### view-change消息阶段

在view v时，副本节点怀疑主节点fault时，会发送view-change消息，该消息包含：
1. h：副本i最新的稳定检查点序号
2. C：副本i保存的h之后的（非稳定）检查点
3. P和Q
4. i：副本i
5. α：副本i对本消息的数字签名

P和Q是2个集合。

P是已经Prepared消息的信息集合：消息既然已经Prepared，说明**至少2f+1的节点拥有了消息，并且认可`<view, n, d>`**，即为消息分配的view和序号，只是还差一步commit阶段就可以完成一致性确认。P中包含的就是已经达到Prepared的消息的摘要d，无需包含完整的请求消息。新的view中，这些请求会使用老的序号n，而无需分配新的序号。

Q是已经Pre-prepared消息的信息集合，主节点已经发送Pre-prepare或副本节点i为请求已经发送Prepare消息，证明**该节点认可`<n, d, v>`**。

P、Q中的请求都是高低水位之间的，无View Changes时，P、Q都是空的，也就是说不包含已经committed的请求。new-view消息中的数据（View Changes的决策结果），都是基于P、Q集合计算出的。

在发送view-change消息前，副本节点会利用日志中的三阶段消息计算P、Q集合，发送view-change消息后，就删除日志中的三阶段消息。

### view-change-ack消息阶段

视图`v+1`的主节点在收到其他节点发送的view-change消息后，并不确认view-change消息是是否拜占庭节点发出的，即不确定消息是否是正确无误的，如果基于错误的消息做决策，就会得到错误的结果，违反一致性：一切操作都是正确的。

设置view-change-ack消息的目的是，让所有副本节点对所有它收到的view-change消息进行检查和确认，只不过确认的结果都发送给新的主节点。主节点统计ack消息，可以辨别哪些view-change是正确的，哪些是拜占庭节点发出的。


副本节点会对view-change消息中的P、Q集合进行检查，要求集合中的请求消息小于等于视图`v`，满足则发送view-change-ack消息：
1. v：v+1
2. i：发送ack消息的副本序号
3. j：副本i要确认的view-change消息的发送方
4. d：副本i要确认的view-change消息的摘要
5. μip：i向主节点p发送消息的通信密钥计算出的MAC，这里需要保证i和p之间通信的私密性，所以不使用数字签名

### new-view消息阶段

新视图主节点p负责基于view-change消息做决策，决策放到new-view消息中。

主节点p维护了一个集合S，用来存放正确的view-change消息。只有view-change消息，以及为该消息背书的view-change-ack消息达到`2f-1`个时，view-change消息才能加入到集合S，但view-change-ack消息不加入集合S。

当集合S的大小达到`2f+1`时，证明有足够多的非拜占庭节点认为需要进行视图变更，并提供了变更的依据：2f+1个view-change消息，主节点p使用S做决策。以下便是**决策逻辑**。

主节点p先确定h：所有view-change消息中最大的稳定检查点。h和h+L其实就是高低水位。

然后依次检查h到h+L中的每一个序号n，对序号n对于的请求进行的处理为：请求m已经Prepared并且Pre-prepared，则收集序号n对应的请求。否则，说明没有请求在序号n能达到committed，为序号n分配一个空请求，并收集起来。它们最后会被放到new-view消息的X集合中。

主节点会创建new-view消息：
- view：当前新视图的编号
- V：是一个集合，每个元素是一对`(i, d)`，代表i发送的view-change消息摘要是d，每一对都与集合S中消息对应，可以使用V证明主节点是在满足条件下，创建new-view消息的，即V是新视图的证明。因为其它多数副本节点已经接收view-change消息，所以此处发送消息的摘要做对比即可。
- X：是一个集合，包含检查点以及选定的请求
- α：主节点p对new-view消息的数字签名


之后，主节点会把new-view消息广播给每一个副本节点。

### 处理new-view消息

#### 主节点处理new-view消息

在发生View Changes时，主节点的状态可能也不是最全的，如果它没有X结合中的请求或者检查点，它可以从其他节点哪拉去。

主节点需要使用new-view消息，达到视图切换的最后一步状态：在新视图v+1中，让集合X中的请求，全部是Pre-prepared状态。为何是Pre-prepared状态呢？因为new-view消息，可以看做一次特殊的Pre-prepare消息。

为什么不直接标记为Committed呢？因为主节点也可能是拜占庭节点，副本节点需要检查new-view消息，向所有节点广播自己检查的结果，满足条件后才能达成一致性。

#### 副本节点处理new-view消息

副本节点在视图v+1，会持续接收view-change消息和new-view消息，它会把new-view消息V集合中的view-change消息，跟它收到的消息做对比，如果它本地不存在某条view-change消息，它可以要求主节点向他提供view-change消息和view-change-ack消息集合，证明至少f+1个非拜占庭副本节点收到过此view-change消息。

副本节点拥有所有的view-change消息之后，副本节点会和主节点运行相同的决策逻辑，以校验new-view消息的正确性。

如果new-view消息是正确的，副本节点会和主节点一样移动到相同的状态，然后广播一条Prepare消息给所有节点，这样就恢复到了正常情况下的：`Pre-prepare -> Prepare -> Commit` 一致性逻辑。这样就完成了从View Changes到正常处理流程的迁移。

如果new-view消息是错误的，说明主节点p是拜占庭节点，副本节点会直接进入v+2，发送view-change消息，进行新的一轮视图切换。


### View Changes如何提供liveness

在一轮视图切换无法完成的时候，会开启新的一轮视图切换，由于拜占庭节点的数量最多为f个，最终会在某一轮视图切换中，能够完成视图切换，所有非拜占庭节点达成一致的状态，保证liveness和safety。

本文前面列出了几种异常情况，下面就看一下View Changes是如何应对这些异常情况的，以及如何提供活性。


Q1：如果下一个View的主节点宕机了怎么办？

A1：副本节点在收集到2f+1个view-change消息后，会启动定时器，超时时间为T，新view的主节点宕机，必然会导致定时器超时时，未能完成View Changes流程，会进入新一轮视图切换。

Q2：如果下一个View的主节点是恶意节点，作恶怎么办？

A2：新view的主节点是恶意节点，如果它做恶了，生成的new-view消息不合法，副本节点可以检测出来。或者new-view消息是合法的，但它只发送给了少数副本节点，副本节点在对new-view消息进行正常的3阶段流程，参与的节点太少，在定时器超时前，不足以完成3阶段流程，副本节点会进入下一轮视图切换。

Q3：如果非拜占庭恶意发起View Changes，造成主节点切换怎么办？

A3：定时器未超时情况下，只有有效的f+1个view-change消息，才会引发其他副本节点进行主节点切换，否则无法造成主节点切换。但PBFT的前提条件是恶意节点不足f个，所以只有恶意节点发起view-change消息时，无法造成主节点切换。

Q4：如果参与View Changes的节点数量不足怎么办？

A4：这个问题可以分几种情况。
- 发起view-change的节点数量不足f+1个，这种情况不会发生整个集群的视图切换。
- 视图切换过程中，不满足各节点的数量要求，无法完成本轮视图切换，会进入下一轮视图切换。


## 结语

View Changes是PBFT中一个重要的环节，它能保证整个协议的liveness，是PBFT不可或缺的一部分。

