---
title: 以太坊交易广播：从宏观到微观
date: 2019-03-15 21:01:43
tags: ['区块链','以太坊']
---



从宏观看，交易在区块链网络中的传播，像广度搜索算法，也像湖面上的水纹，一圈圈向外扩散。但实际场景由于网络通信环境，可能效果上并非一圈一圈向外的，但总体上是向外扩散。

![](https://lessisbetter.site/images/2019-03-tx-macro.png)



从微观上讲，两个节点间交易的传播如下图。从钱包到节点，节点把可打包的交易发送给相连的节点。主要流程如下：

1. 钱包（浏览器、APP）发送交易到节点。
2. 节点把收到的交易插入`txpool`。
3. 可打包（`nonce`值连续）的交易加入`txpool.pending`，不可打包的交易(`nonce`值存在断开)插入到`txpool.queued`。
4. 交易进入`txpool.pending`后，`txpool`发布`NewTxsEvent`。
5. `Protocol Manager`收到事件后，`txBroadcastLoop`将交易加入到连接的peer的交易队列（得缓冲一下，不一定能很快发，毕竟连接上有很多类型的数据需要传送）。
6. 各peer协程从各自的交易队列取交易合成消息，发送给peer。
7. peer收到交易消息后，加入`txpool`，回到步骤2。


![](https://lessisbetter.site/images/2019-03-tx-micro.png)