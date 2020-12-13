---
title: Etcd Raft架构设计和源码剖析2：数据流
date: 2019-08-22 20:24:08
tags: ['一致性', '共识', 'Raft']
---


## 前言

之前看到一幅描述etcd raft的流程图，感觉非常直观，但和自己看源码的又有些不同，所以自己模仿着画了一下，再介绍一下。

下图从左到右依次分为4个部分：

1. raft：raft主体功能部分
1. Node：raft提供的接口，raft跟上层的通信接口，会运行一个run函数，持续循环处理通道上的数据
1. raftNode：上层应用逻辑
1. 其他：Client、Network、State

![etcd raft workflow](http://img.lessisbetter.site/2019-09-etcd-raft-msg-flow.png)

图中的箭头为数据的流向，这幅图包含了多个流程，接下来会分成4个流程介绍：

1. 客户端请求
1. 发送消息给其他节点
1. 接收其他节点消息及处理
1. 应用达成一致的日志



## 客户端请求

客户端请求的流程，在下图已经使用红色箭头标出，流程如下：

1. 客户端将请求发送给应用层raftNode
1. raftNode使用Propose方法，请求写入到propc通道
1. raft.Step接收到通道数据，会通过append等函数加入到raftLog
1. raftLog用来暂时存储和查询日志，请求会先加入到unstable


![etcd raft request flow](http://img.lessisbetter.site/2019-09-etcd-raft-msg-flow-req.png)

## 发送消息

发送消息的数据流，已经用红色箭头标出，流程如下：

1. raft发现有数据发送给其他节点，数据可以是leader要发送给follower的日志、snapshot，或者其他类型的消息，比如follower给leader的响应消息
1. 利用NewReady创建结构体Ready，并写入到readyc通道
1. raftNode从通道读到Ready，取出其中的消息，交给Network发送给其他节点

![etcd raft send message flow](http://img.lessisbetter.site/2019-09-etcd-raft-msg-flow-send.png)

## 接收消息

接收消息的数据流，已经在下图用红色箭头标出，流程如下：

1. 从Network收到消息，可以是leader给follower的消息，也可以是follower发给leader的响应消息，Network的handler函数将数据回传给raftNode
1. raftNode调用Step函数，将数据发给raft，数据被写入recvc通道
1. raft的Step从recvc收到消息，并修改raftLog中的日志

![etcd raft receive msg flow](http://img.lessisbetter.site/2019-09-etcd-raft-msg-flow-recv.png)

## 应用日志

raft会将达成一致的log通知给raftNode，让它应用到上层的数据库，数据流已经在下图用红色箭头标出，流程如下：

1. raft发现有日志需要交给raftNode，调用NewReady创建Ready，从raftLog读取日志，并存到Ready结构体
1. Ready结构体写入到readyc通道
1. raftNode读到Ready结构体，发现Ready结构体中包含日志
1. raftNode会把日志写入到storage和WAL，把需要应用的日志，提交给状态机或数据库，去修改数据
1. raftNode处理完Ready后，调用Advance函数，通过advancec发送一个信号给raft，告知raft传出来的Ready已经处理完毕

可以发现有2个storage，1个是raftLog.Storage，一个是raftNode.storage，Storage是一个接口，可以用来读取storage中的数据，但不写入，storage的数据写入是由raftNode完成的，但raftNode.storage就是raft.MemoryStorage，所以不稳定的、稳定的都由raft存储，持久化存储由WAL负责，etcd中有现成实现的WAL操作可用，用来存储历史Entry、快照。

Storage接口更多信息请看[Storage接口介绍](http://lessisbetter.site/2019/09/05/etcd-raft-sources-structs/#Storage)。

![etcd raft apply logs flow](http://img.lessisbetter.site/2019-09-etcd-raft-msg-flow-commit.png)

