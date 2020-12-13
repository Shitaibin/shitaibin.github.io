---
title: 以太坊源码分析：共识（1）矿工
date: 2018-06-22 20:12:57
tags: ['以太坊', '区块链']
---

## 前言

矿工在PoW中负责了产生区块的工作，把一大堆交易交给它，它生成一个证明自己工作了很多区块，然后将区块加入到本地区块链并且广播给其他节点。

接下来我们将从以下角度介绍矿工：

1. 角色。矿工不是一个人，而是一类人，可以把这一类人分成若干角色。
2. 一个区块产生的主要流程。
3. 矿工的主要函数介绍，掌握矿工的主要挖矿机制。

<!--more-->

介绍矿工由哪些部分组成，会和哪些其他模块进行交互，这些部分是如何协作产生区块的。

## 角色

有3种角色：miner、worker、agent。

- miner：是矿长，负责管理整个矿场的运作，比如：启动、停止挖矿，处理外部请求，设置挖矿获得的奖励的钱包地址等等。
- worker：副矿长，负责具体挖矿工作的安排，把挖矿任务（Work）安排给agent。
- agent：真实的矿工，他们负责挖矿，把自己的劳动成果（Result）交给worker，agent默认只有1个，可以通过API创建多个。

![img](http://img.lessisbetter.site/2018-06-22-121153.jpg)

## 一个区块产生的主要流程

实际的挖矿过程基本不涉及miner，只涉及worker、agent和engine，engine是共识引擎模块，我们利用下图介绍生成一个区块的主要流程。

> 挖矿过程中只涉及engine的3个接口：1）Prepare()挖矿前的准备工作，2）Finalize()形成一个基本定型的区块，3）Seal()形成最终的区块。

1. worker把区块头、交易、交易执行的收据等传递给engine.Finalize。
2. engine.Finalize返回一个`block`，该block的header中缺少`Nonce`和`MixDigest`，这两个值是挖矿获取的。
3. worker把block封装到`work`，把work发送给所有的agent。
4. agent.update把work传递给agent.mine。
5. agent.mine把work传递给engine.Seal，调用engine.Seal挖矿。
6. engine.Seal把`Nonce`和`MixDigest`填到区块头，生成一个`new block`交给agent.mine.
7. agent.mine把`new block`封装成`Result`，发送给worker。

![img](http://img.lessisbetter.site/2018-06-22-121152.jpg)

## 矿工的主要函数

介绍miner、worker和agent的主要函数，他们是矿工的具体运作机制。

### miner的主要函数

主要关注2个函数：

1. `New()`：负责创建miner。还创建1个worker和1个agent，但agent还可以通过API创建，然后启动`update`函数。
2. `update()`：负责关注downloader的3个事件：StartEvent、DoneEvent、FailedEvent。StartEvent是开始同步区块，必须停止挖矿，DoneEvent和FailedEvent是同步成功或者失败，是同步的结束，已经可以挖矿了。**表明：挖矿和同步区块不可同时进行，尽量降低了区块冲突的可能。**

### worker的主要函数

主要是3个函数：

1. `commitNewWork()`：负责生成work，分配agent。这个阶段做了很多工作，调用Engine.Prepare进行准备工作，创建Header，**执行交易**，获取Uncle，使用Engine.Finalize形成“基本定型”的临时区块，创建Work，最后把work传递给agent。另外`commitNewWork`存在多处调用，并且worker有`wait`和`update`另外2个协程，他们都会调用`commitNewWork`，所以存在临界区需要谨慎加锁。
2. `update()`：负责处理外部事件。它是死循环，主要处理3种事件：1）ChainHeadEvent，有了新区块头，所以得切换到挖下一个高度的区块，2）ChainSideEvent，收到了uncle区块，缓存起来，3）TxPreEvent，预处理交易，如果在挖矿执行`commitNewWork`，如果未挖矿，则交易设置为未决状态。
3. `wait()`：负责处理agent挖矿的结果。它是死循环，一直等待接收agent发回的result，然后把区块加入到本地数据库，如果没有问题，就发布`NewMinedBlockEvent`事件，通告其他节点挖到了一个新块。

![img](http://img.lessisbetter.site/2018-06-22-121154.jpg)
*图片来自网络，原出处已不详，如果侵犯您的权益，请通知我立即删除*

### agent的主要函数

主要2个函数:

1. `update()`：负责接收worker发来的任务（work）。它是死循环，把work交给mine去挖矿。
2. `mine()`：负责挖矿。它拥有挖矿的能力，调用Engine.Seal挖矿，如果挖矿成功则生成result，发送给worker。 
   ![img](http://img.lessisbetter.site/2018-06-22-121151.jpg)
    *图片来自网络，原出处已不详，如果侵犯您的权益，请通知我立即删除*


> 最后两张图片来源网络，侵删。

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/06/22/ethereum-code-consensus-1/](http://lessisbetter.site/2018/06/22/ethereum-code-consensus-1/)