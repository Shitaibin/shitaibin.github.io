---
title: Etcd Raft架构设计和源码剖析1：宏观架构
date: 2019-08-19 09:42:37
tags: ['一致性', '共识', 'Raft']
---

## 序言

[Etcd](https://github.com/etcd-io/etcd)提供了一个样例[contrib/raftexample](https://github.com/etcd-io/etcd/tree/master/contrib/raftexample)，用来展示如何使用etcd raft。这篇文章通过raftexample介绍如何使用etcd raft。

## raft服务

raftexample是一个分布式KV数据库，客户端可以向集群的节点发送写数据和读数据，以及修改集群配置的请求，它使用etcd raft保持各集群之间数据的一致性。

![cluster](https://lessisbetter.site/images/2019-08-cluster.png)



## etcd raft

etcd raft实现了raft论文的核心，所有的IO（磁盘存储、网络通信）它都没有实现，它做了解耦。

它是一个状态机，有数据作为输入，经过当前状态和输入，得到确定性的输出，即每个节点上都是一样的。

![etcd-raft](https://lessisbetter.site/images/2019-08-etcd-raft.png)

## raft应用架构

raft集群会由多个节点组成，客户端的请求发送给raft leader，再由raft leader通过网络通信在集群之中对请求达成共识。

集群中的每个节点从架构上都可以分为两层：

- 应用层，负责处理用户请求，数据存储以及集群节点间的网络通信，
- 共识层，负责相同和输入数据和状态，生成确定性的、一致的输出，

共识层由etcd raft负责，应用层要负责业务逻辑，数据存储和网络通信不需要应用层实现，而是由不同的模块负责，应用层负责起**衔接**存储存储和网络通信即可。

![app-arch](https://lessisbetter.site/images/2019-08-app-arch.png)

应用层有3个重要组成部分：http API、kv store和raftNode。

###  http API

每个节点都会启动一个http API用来接受客户端请求，它只是接收请求，不对请求做处理。它会把客户端的写入请求PUT和查询请求GET都交给kv store。

对于修改raft集群配置请求，它会生成`ConfChange`交给raftNode。

### kv store

一个kv数据库服务，它保存有一个kv db，用来存储**用户数据**。

- 对于查询请求，它直接从db中读取数据。
- 对于写入请求，需要修改用户数据，这就需要集群节点使用raft对请求达成共识，它把请求传递给raftNode。

### raftNode

raftNode用来跟etcd raft交互，他需要：

- 把客户端的写请求，修改raft配置的请求交给etcd raft
- 衔接网络通信跟etcd raft之间的桥梁，把etcd raft的消息发送出去，或接受到的raft消息交给raft
- 保存raft的WAL和snapshot。

对于写请求，它会把请求**数据编码**后发送给etcd raft，etcd raft会把写请求封装成raft的Propose消息`MsgProp`，编码后的数据成为log Entry。因为raft并不关心具体的请求内容，它只需要保证每个集群节点在相同的log index拥有相同的log Entry，即请求即可。

raftNode还会启动1个http server，用来集群节点之间的通信，传递raft消息，让集群节点达成共识。它与http api是不同的，http api用来接收用户请求。

### raftNode与raft交互

raft模块内部定义了一个`Node`接口，它代表了raft集群中的一个raft节点，它是应用层跟共识层交互的接口。

其中有几个与数据传递相关函数的是：

- Propose：应用层通过此函数把客户端写请求传递raft。
- ProposeConfChange：应用层通过此函数把客户端**修改raft集群配置的请求**传递raft。
- Step：应用层把收到的raft集群之间通信的消息传递给raft。
- Ready：raft对外的出口只有1个，就是Ready函数，**Ready函数**返回一个通道，应用层可以从这个通道中读到raft要输出的所有数据，这个数据被称为**Ready结构体**，包括log entry，集群间的通信消息等。
- Advance：应用层处理完Ready结构体后，调用Advance通知raft，它已处理完刚读到的Ready结构体，raft可以根据最新状态生成下一个Ready结构体。

还有一个ApplyConfChange函数，当Ready结构体中包含修改raft集群配置的log entry时，应用层会调用此函数，把配置应用到raft。

## raft架构

瞄完raft应用架构，可以从宏观角度看一下raft是如何跟应用层对接的。

raft包内部有2个很重要的结构体：node和raft。

### node结构体

node结构体（后续称为raft.node）实现了`Node`接口，负责跟应用层对接，raft.node有个goroutine持续运行，应用层raftNode也有goroutine持续运行，raftNode调用raft.node的函数，每个函数都有对应的一个channel，用来把raftNode要传递给raft的数据，发送给raft.node。比如Propose函数的通道是proc，Step函数的通道是recvc。

### raft结构体

raft结构体（后续称为raft.raft）是raft算法的主要实现。

raft.node把输入推给raft.raft，raft.raft根据输入和**当前的状态数据**生成输出，输出临时保存在raft内，raft.node会检查raft.raft是否有输出，如果有输出数据，就把输出生成Ready结构体，并传递给应用层。

raft.raft应用层有一个storage，存放的是**当前的状态数据**，包含了保存在内存中的log entry，但这个storage并不是raft.raft的，是应用层的，raft.raft只从中读取数据，log entry的写入由应用层负责。

![raft-arch](https://lessisbetter.site/images/2019-08-raft-arch.png)



## 几个存储相关的概念

**WAL**是Write Ahead Logs的缩写，存储的是log entry记录，即所有写请求的记录。

**storage**也是存的log entry，只不过是保存在内存中的。

**kv db**是保存了所有数据的最新值，而log entry是修改数据值的操作记录。

log entry在集群节点之间达成共识之后，log entry会写入WAL文件，也会写入storage，然后会被应用到kv store中，改变kv db中的数据。

**Snapshot**是kv db是某个log entry被应用后生成的快照，可以根据快照快速回复kv db，而无需从所有的历史log entry依次应用，恢复kv db。

## 一个写请求的处理过程

有了上面架构层面的了解，我们从宏观的角度看一下一个写请求被处理的过程。

1. 客户端把写请求发给leader节点
2. leader节点的http api接收请求，并把请求传递给kv store，kv sotre把写请求发送给raftNode，raftNode把写请求传递给raft.node
3. leader节点的raft.node把写请求转化为log entry，并交给raft.raft，raft.raft生成发送给每一个follower的Append消息
4. leader节点的raft.node取出raft.raft中的Append消息以及其他数据，封装成Ready传递给raft.Node
5. leader节点的raft.Node把Ready中的entry保存到storage，然后把Ready中的消息，发送给相应的节点
6. follower节点的raft.Node收到消息，把消息传递给raft.node，raft.node推给raft.raft
7. follower的raft.raft处理Append消息，进行匹配和校验后，生成Append Response消息和保存log entry
8. follower的raft.node从raft.raft获取数据，然后生成Ready传递给raft.Node
9. follower节点的raft.Node把Ready中的entry保存到storage，然后把Ready中的消息，发送给相应的节点
10. leader节点的raft.Node收到消息，把消息传递给raft.node，raft.node推给raft.raft
11. leader节点的raft.raft处理Append Response消息，然后检查已经达成半数以上同意的log entry，更新已经被commit的log entry的index
12. leader节点的raft.raft在创建Append等消息的时候，填写了已被commited的log index，所以下次在生成消息，并发送给follower后，follower就根据committed log index提交本地的log entry
13. 无论是leader，还是follower在生成Ready的时候，会包含已经被committed的log entry，这些entry是等待应用到kv store的，raftNode拿到Ready后，会把这些entry取出来，传递给kv store，kv store会修改key-value的最新值。

## 总结

本文从宏观角度介绍了：
- 使用etcd raft应用的架构
- 使用etcd raft应用应当提供哪些功能供raft使用
- 应用是如何和etcd raft交互的
- etcd raft涉及到的存储概念
- 一个写请求从客户端到在节点之间达成一致，应用到状态机的过程


