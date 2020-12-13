---
title: 以太坊源码分析：交易缓冲池txpool
date: 2018-12-11 10:51:00
tags: ['以太坊', '区块链']
---


区块链就是何交易打交道，我们今天就介绍下，交易处理过程中的一个重要组成部分：txpool。这篇文章主要从功能角度介绍，通过这篇文章会了解：

1. txpool的在交易中的位置和作用。
2. txpool的功能，核心组成部分queued和pending。
3. txpool如何实现它的功能。
4. txpool源码的重要关注点。

<!-- more -->

以太坊内部有个重要的内部功能是txpool，从字面意思就能看出来，交易池就是存放交易的池子。它在以太坊中的位置如下图，只要有新交易，无论是本节点创建的，还是其他peer节点广播来的，都会先加入到交易池里，在打包区块的时候，就从这个池子里提取，区块产生之后，共识区块，交易上链。

![txpool主图](https://lessisbetter.site/images/2018-txpool-position.png)

txpool有4个功能：

1. 作为存放交易的缓冲区，大量交易到来时，先存起来
2. 为打包区块服务，合适交易会被打包到区块
3. 清理交易
4. 当交易的数量多于缓冲区大小时，过滤/惩罚发送大量交易的账户（攻击者）



我们来一张稍微详细点的模块交互图，看txpool怎么实现上面4个功能的。

![txpool模块交互](https://lessisbetter.site/images/2018-txpool-module-interactive.png)

### 缓存功能的设计

txpool中的交易分为queued和pending 2种，其中**queued存放未来的、当前无法执行的交易**。以太坊使用nonce值决定某个账户的交易顺序，多条交易值nonce值必须连续，如果和过去的交易不连续，则无法执行，我们不妨使用nonce值，标记交易的号码，nonce为10的交易，称为第10号交易。举个例子，当前账户的nonce是10，txpool中有该账户的第100号交易，但txpool中没有第11~99号交易，这些交易的缺失，造成第100号交易无法执行，所以第100号交易就是未来的交易、不可执行的交易，存放在queue中。

**pending存放可执行的交易**。比如我们把上面的11~99号交易补全了，那么11~100号交易都可以进入到pending，因为这些交易都是连续的，都可以打包进区块。

当节点收到交易（本地节点发起的或peer广播来的）时，会先存放到queued，txpool在某些情况下，把queued中可执行的交易，转移到pending中。

### 为区块打包服务

**这是txpool最核心的功能**，worker在打包区块的时候，会获取**所有的pending交易**，但这些交易还存在txpool中，worker只是读取出来，至于txpool何时删除交易，稍后从txpool清理交易的角度单独在看。

### 清理交易

txpool清理交易有以下**几种条件**，符合任意以下1条的，都是**无效交易，会被从pending或者queued中移除**：

1. 交易的nonce值已经低于账户在当前高度上的nonce值，代表交易已过期，交易已经上链就属于这种情况
2. 交易的GasLimit大于区块的GasLimit，区块容不下交易
3. 账户的余额已不足以支持该交易要消耗的费用
4. 交易的数量超过了queued和pending的缓冲区大小，需要进行清理

交易清理主要有**3个场景**：

1. txpool订阅了`ChainHeadEvent`事件，该事件代表主链上有新区块产生，txpool会根据最新的区块，检查每个账号的交易，有些无效的会被删除，有些由于区块回滚会从pending移动到queued，然后把queued中可执行的交易移动到pending，为下一轮区块打包组号准备。

1. queued交易移动到pending被称为“提升”（promote），这个过程中，同样会检查交易，当交易不符合以上条件时，就会被直接从queued中删除。
2. 删除停留在queued中超过3小时的交易，3小时这个超时时间是可以通过`geth`的启动参数调整的。txpool记录了某个账户交易进入pending的时间，如果这个时间超过了3小时，代表该账号的交易迟迟不能被主链打包，既然无法被主链接受，就删除掉在queued中本来就无法执行的交易。

### 惩罚恶意账号

这也是txpool很重要的一个属性，可以防止恶意账户以发起大量垃圾交易。防止恶意用户造成：

1. 占用txpool空间
2. 浪费节点大量内存和CPU
3. 降低打包性能

**只有当交易的总数量超过缓冲区大小时，txpool才会认为有恶意账户发起大量交易。**pending和queued缓冲区大小不同，但处理策略类似：

1. pending的缓冲区容量是4096，当pending的交易数量多于此时，就会运行检查，每个账号的交易数量是否多于16，把这些账号搜集出来，进行循环依次清理，什么意思呢？就是每轮只删除（移动到queued）这些账号的每个账号1条交易，然后看数量是否降下来了，不满足再进行下一轮，直到满足。
2. queued的缓冲区容量是1024，超过之后清理策略和pending差不多，但这里可是真删除了。

该部分功能未抽象成单独的函数，而是在`promoteExecutables()`中，就是在每次把queued交易转移到pending后执行的。

**本地交易的特权**，txpool虽然对交易有诸多限制，但如果交易是本节点的账号发起的，以上数量限制等都对他无效。所以，如果你用本节点账号不停的发送交易，并不会被认为是攻击者，你用`txpool.status`命令，可以查看到交易的数量，肯定可以大于4096，我曾达到过60000+。

### 重点关注的源码

txpool的主要设计上面就讲完了，如果你想把txpool的代码阅读一番，我建议你重点关注一下这些函数和变量，按图索骥能就完全掌握txpool的实现。

- `TxPoolConfig`：txpool的配置参数
- `chainHeadCh`：txpool订阅了新区块事件
- `pending`：pending的交易，每个账号都有一个交易列表
- `queue`：queued的交易，每个账号都有一个交易列表
- `loop`：txpool的事件处理函数
- `addTx`：添加1条交易的源头，你能找到类似的函数
- `promoteExecutables`：queued交易移动到pending
- `reset`：根据当前区块的最新高度，重置txpool中的交易

仔细阅读一遍，你会发现txpool会涉及多个锁（TxPool.mu, TxPool.all, TxPool.priced.all），所以当txpool中的交易很多时，它的性能是很低的，这也会影响到区块的打包。


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/12/11/ethereum-design-of-txpool/](http://lessisbetter.site/2018/12/11/ethereum-design-of-txpool/)

<div style="text-align:center">关注公众号，获取最新Golang文章。</div>

<img src="https://lessisbetter.site/images/image/png/gzh/gzh-%E5%B8%A6%E5%AD%97%E4%BA%8C%E7%BB%B4%E7%A0%81.png" style="border:0" width="256" hegiht="30" align=center />


<div style="color:#0096FF; text-align:center">一起学Golang-分享有料的Go语言技术</div>