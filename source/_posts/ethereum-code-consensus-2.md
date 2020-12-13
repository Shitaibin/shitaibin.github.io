---
title: 以太坊源码分析：共识（2）接口
date: 2018-06-22 20:15:16
tags: ['以太坊', '区块链']
---

## 前言

`engine`是以太坊封定义的一个接口，它的功能可以分为3类：

1. 验证区块类，主要用在将区块加入到区块链前，对区块进行共识验证。
2. 产生区块类，主要用在挖矿时。
3. 辅助类。

<!--more-->

接下来我们看一下`engine`具体定义了哪些功能，还有各功能的使用场景。

## engine定义的具体功能

engine有3类功能，验证区块类、产生区块类、辅助类。因为产生区块在前，验证区块在后，接下来采用产生区块类、验证区块类、辅助类，分别介绍它们的功能和使用场景。

![engine接口调用图](http://img.lessisbetter.site/2018-12-engine-interface.png) 


### 验证区块类

1. `Prepare`：初始化区块头信息，不同的共识算法初始化不同。使用场景是，worker创建work的时候调用。
2. `Finalize`：根据数据生成“基本定型”的区块，但区块头中还缺少部分数据。使用场景是，1）模拟区块链的时候，被`GenerateChain`调用，用来生成区块链。2）交易状态管理时，被`StateProcessor.Process`调用用来执行交易。3）worker创建work的时候调用。
3. `Seal`：根据传入的块，进行的是挖矿工作，使用挖矿的结果，修改区块头，然后生成新的区块。使用场景是，被`agent.mine`调用。

### 验证区块类

1. `VerifyHeader`：验证区块头。使用在fetcher中，当fetcher要插入区块的时候，需要先对区块头进行校验。
2. `VerifyHeaders`：验证一批区块头。有2种使用场景，1）区块链中，`insertChain`当把一批区块插入到区块链这个链条的时候，需要进行检查；2）LightChain中，把一批区块头插入到本地链。
3. `VerifyUncles`：验证区块中的叔块。`insertChain`当区块插入区块链的时候，需要对叔块进行验证，调用在VerifyHeaders之后。
4. `VerifySeal`：针对Seal函数做的功能进行验证。验证Seal()所修改的区块头中的数据。对外的使用场景是，把Work发送给远端Agent的时候调用。对内的使用场景是，验证区块头的时候会被调用。

### 辅助类

1. `APIs`：生成以太坊共识相关的API。在以太坊启动RPC服务时，生成API。
2. `Author`：读取区块头中的`coinbase`。被ethstats使用，ethstats是以太坊状态管理服务，当报告数据的时候，需要获取区块的Author信息。

最后关注一下蓝色的线条，它们代表insertChain所调用的范围，先关的有VerifyHeaders、VerifyUncles、Finalize，涉及到块头的验证、叔块的验证，以及执行区块中的交易，一个区块加入到区块链中，不仅要验证，还要执行各种交易，改变各种状态，所有节点执行确定性的行为之后，达成一致性。

## FAQ

- Q：谁实现engine 
  A：以太坊中的Ethash和Clique实现了`engine`，Ethash是基于PoW的共识，Clique是基于PoA的共识。
- Q：为什么`insertChain`没有调用`VerifySeal`？ 
  A：因为`Seal()`修改的是header中的部分数据，在验证区块头的时候，会被调用。只是调用流程在Ethash和Clique中的实现略有不同，后续讲解。

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/06/22/ethereum-code-consensus-2/](http://lessisbetter.site/2018/06/22/ethereum-code-consensus-2/)