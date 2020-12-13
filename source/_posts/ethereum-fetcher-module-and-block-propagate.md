---
title: 以太坊源码分析：fetcher模块和区块传播
date: 2018-08-30 16:49:47
tags: ['以太坊', '区块链']
---


# 前言

这篇文章从区块传播策略入手，介绍新区块是如何传播到远端节点，以及新区块加入到远端节点本地链的过程，同时会介绍fetcher模块，fetcher的功能是处理Peer通知的区块信息。在介绍过程中，还会涉及到p2p，eth等模块，不会专门介绍，而是专注区块的传播和加入区块链的过程。

当前代码是以太坊Release 1.8，如果版本不同，代码上可能存在差异。

<!--more-->

# 总体过程和传播策略

本节从宏观角度介绍，节点产生区块后，为了传播给远端节点做了啥，远端节点收到区块后又做了什么，每个节点都连接了很多Peer，它传播的策略是什么样的？

总体流程和策略可以总结为，传播给远端Peer节点，Peer验证区块无误后，加入到本地区块链，继续传播新区块信息。具体过程如下。

先看总体过程。产生区块后，`miner`模块会发布一个事件`NewMinedBlockEvent`，订阅事件的协程收到事件后，就会把新区块的消息，广播给它所有的peer，peer收到消息后，会交给自己的fetcher模块处理，fetcher进行基本的验证后，区块没问题，发现这个区块就是本地链需要的下一个区块，则交给`blockChain`进一步进行完整的验证，这个过程会执行区块所有的交易，无误后把区块加入到本地链，写入数据库，这个过程就是下面的流程图，图1。

![图1：新区块传播总体流程图](https://lessisbetter.site/images/image-20180821115214521.png-own)

总体流程图，能看到有个分叉，是因为节点传播新区块是有策略的。它的传播策略为：

1. 假如节点连接了`N`个Peer，它只向Peer列表的`sqrt(N)`个Peer广播**完整的区块**消息。
2. 向所有的Peer广播**只包含区块Hash**的消息。

策略图的效果如图2，红色节点将区块传播给黄色节点：![图2：产生区块后传播给相邻节点](https://lessisbetter.site/images/image-20180821114210114.png-own)

收到区块Hash的节点，需要从发送给它消息的Peer那里获取对应的完整区块，获取区块后就会按照图1的流程，加入到fetcher队列，最终插入本地区块链后，**将区块的Hash值广播给和它相连，但还不知道这个区块的Peer**。非产生区块节点的策略图，如图3，黄色节点将区块Hash传播给青色节点：![图3：非产块节点传播新区块](https://lessisbetter.site/images/image-20180821114756055.png-own)

至此，可以看出**以太坊采用以石击水的方式，像水纹一样，层层扩散新产生的区块**。

# Fetcher模块是干啥的

fetcher模块的功能，就是收集其他Peer通知它的区块信息：1）完整的区块2）区块Hash消息。根据通知的消息，获取完整的区块，然后传递给`eth`模块把区块插入区块链。

如果是完整区块，就可以传递给eth插入区块，如果只有区块Hash，则需要从其他的Peer获取此完整的区块，然后再传递给eth插入区块。

![fetcher功能抽象](https://lessisbetter.site/images/image-20180821175330370.png-own)

# 源码解读

本节介绍区块传播和处理的细节东西，方式仍然是先用图解释流程，再是代码流程。

## 产块节点的传播新区块

节点产生区块后，广播的流程可以表示为图4：

1. 发布事件
2. 事件处理函数选择要广播完整的Peer，然后将区块加入到它们的队列
3. 事件处理函数把区块Hash添加到所有Peer的另外一个通知队列
4. 每个Peer的广播处理函数，会遍历它的待广播区块队列和通知队列，把数据封装成消息，调用P2P接口发送出去

![图4：产块节点的传播图](https://lessisbetter.site/images/image-20180821115537184.png-own)

再看下代码上的细节。

1. `worker.wait()`函数发布事件`NewMinedBlockEvent`。
2. `ProtocolManager.minedBroadcastLoop()`是事件处理函数。它调用了2次`pm.BroadcastBlock()`。

```go
// Mined broadcast loop
func (pm *ProtocolManager) minedBroadcastLoop() {
	// automatically stops if unsubscribe
	for obj := range pm.minedBlockSub.Chan() {
		switch ev := obj.Data.(type) {
		case core.NewMinedBlockEvent:
			pm.BroadcastBlock(ev.Block, true)  // First propagate block to peers
			pm.BroadcastBlock(ev.Block, false) // Only then announce to the rest
		}
	}
}
```

1. `pm.BroadcastBlock()`的入参`propagate`为真时，向部分Peer广播完整的区块，调用`peer.AsyncSendNewBlock()`，否则向所有Peer广播区块头，调用`peer.AsyncSendNewBlockHash()`，这2个函数就是把数据放入队列，此处不再放代码。

```go
// BroadcastBlock will either propagate a block to a subset of it's peers, or
// will only announce it's availability (depending what's requested).
func (pm *ProtocolManager) BroadcastBlock(block *types.Block, propagate bool) {
	hash := block.Hash()
	peers := pm.peers.PeersWithoutBlock(hash)

	// If propagation is requested, send to a subset of the peer
	// 这种情况，要把区块广播给部分peer
	if propagate {
		// Calculate the TD of the block (it's not imported yet, so block.Td is not valid)
		// 计算新的总难度
		var td *big.Int
		if parent := pm.blockchain.GetBlock(block.ParentHash(), block.NumberU64()-1); parent != nil {
			td = new(big.Int).Add(block.Difficulty(), pm.blockchain.GetTd(block.ParentHash(), block.NumberU64()-1))
		} else {
			log.Error("Propagating dangling block", "number", block.Number(), "hash", hash)
			return
		}
		// Send the block to a subset of our peers
		// 广播区块给部分peer
		transfer := peers[:int(math.Sqrt(float64(len(peers))))]
		for _, peer := range transfer {
			peer.AsyncSendNewBlock(block, td)
		}
		log.Trace("Propagated block", "hash", hash, "recipients", len(transfer), "duration", common.PrettyDuration(time.Since(block.ReceivedAt)))
		return
	}
	// Otherwise if the block is indeed in out own chain, announce it
	// 把区块hash值广播给所有peer
	if pm.blockchain.HasBlock(hash, block.NumberU64()) {
		for _, peer := range peers {
			peer.AsyncSendNewBlockHash(block)
		}
		log.Trace("Announced block", "hash", hash, "recipients", len(peers), "duration", common.PrettyDuration(time.Since(block.ReceivedAt)))
	}
}
```

1. `peer.broadcase()`是每个Peer连接的广播函数，它只广播3种消息：交易、完整的区块、区块的Hash，这样表明了节点只会主动广播这3中类型的数据，剩余的数据同步，都是通过**请求-响应**的方式。

   ```go
   // broadcast is a write loop that multiplexes block propagations, announcements
   // and transaction broadcasts into the remote peer. The goal is to have an async
   // writer that does not lock up node internals.
   func (p *peer) broadcast() {
   	for {
   		select {
   		// 广播交易
   		case txs := <-p.queuedTxs:
   			if err := p.SendTransactions(txs); err != nil {
   				return
   			}
   			p.Log().Trace("Broadcast transactions", "count", len(txs))
   		// 广播完整的新区块
   		case prop := <-p.queuedProps:
   			if err := p.SendNewBlock(prop.block, prop.td); err != nil {
   				return
   			}
   			p.Log().Trace("Propagated block", "number", prop.block.Number(), "hash", prop.block.Hash(), "td", prop.td)
   
   		// 广播区块Hash
   		case block := <-p.queuedAnns:
   			if err := p.SendNewBlockHashes([]common.Hash{block.Hash()}, []uint64{block.NumberU64()}); err != nil {
   				return
   			}
   			p.Log().Trace("Announced block", "number", block.Number(), "hash", block.Hash())
   
   		case <-p.term:
   			return
   		}
   	}
   }
   ```

   

## Peer节点处理新区块

本节介绍远端节点收到2种区块同步消息的处理，其中`NewBlockMsg`的处理流程比较清晰，也简洁。`NewBlockHashesMsg`消息的处理就绕了2绕，从总体流程图1上能看出来，它需要先从给他发送消息Peer那里获取到完整的区块，剩下的流程和`NewBlockMsg`又一致了。

这部分涉及的模块多，画出来有种眼花缭乱的感觉，但只要抓住上面的主线，代码看起来还是很清晰的。通过图5先看下整体流程。

消息处理的起点是`ProtocolManager.handleMsg`，`NewBlockMsg`的处理流程是蓝色标记的区域，红色区域是单独的协程，是fetcher处理队列中区块的流程，如果从队列中取出的区块是当前链需要的，校验后，调用`blockchian.InsertChain()`把区块插入到区块链，最后写入数据库，这是黄色部分。最后，绿色部分是`NewBlockHashesMsg`的处理流程，代码流程上是比较复杂的，为了能通过图描述整体流程，我把它简化掉了。

![图5：远端节点处理新区块](https://lessisbetter.site/images/image-20180821143403650.png-own)

仔细看看这幅图，掌握整体的流程后，接下来看每个步骤的细节。

### NewBlockMsg的处理

本节介绍节点收到完整区块的处理，流程如下：

1. 首先进行RLP编解码，然后标记发送消息的Peer已经知道这个区块，这样本节点最后广播这个区块的Hash时，不会再发送给该Peer。
2. 将区块存入到fetcher的队列，`调用fetcher.Enqueue`。
3. 更新Peer的Head位置，然后判断本地链是否落后于Peer的链，如果是，则通过Peer更新本地链。

只看`handle.Msg()`的`NewBlockMsg`相关的部分。

```go
case msg.Code == NewBlockMsg:
	// Retrieve and decode the propagated block
	// 收到新区块，解码，赋值接收数据
	var request newBlockData
	if err := msg.Decode(&request); err != nil {
		return errResp(ErrDecode, "%v: %v", msg, err)
	}
	request.Block.ReceivedAt = msg.ReceivedAt
	request.Block.ReceivedFrom = p

	// Mark the peer as owning the block and schedule it for import
	// 标记peer知道这个区块
	p.MarkBlock(request.Block.Hash())
	// 为啥要如队列？已经得到完整的区块了
	// 答：存入fetcher的优先级队列，fetcher会从队列中选取当前高度需要的块
	pm.fetcher.Enqueue(p.id, request.Block)

	// Assuming the block is importable by the peer, but possibly not yet done so,
	// calculate the head hash and TD that the peer truly must have.
	// 截止到parent区块的头和难度
	var (
		trueHead = request.Block.ParentHash()
		trueTD   = new(big.Int).Sub(request.TD, request.Block.Difficulty())
	)
	// Update the peers total difficulty if better than the previous
	// 如果收到的块的难度大于peer之前的，以及自己本地的，就去和这个peer同步
	// 问题：就只用了一下块里的hash值，为啥不直接使用这个块呢，如果这个块不能用，干嘛不少发送些数据，减少网络负载呢。
	// 答案：实际上，这个块加入到了优先级队列中，当fetcher的loop检查到当前下一个区块的高度，正是队列中有的，则不再向peer请求
	// 该区块，而是直接使用该区块，检查无误后交给block chain执行insertChain
	if _, td := p.Head(); trueTD.Cmp(td) > 0 {
		p.SetHead(trueHead, trueTD)

		// Schedule a sync if above ours. Note, this will not fire a sync for a gap of
		// a singe block (as the true TD is below the propagated block), however this
		// scenario should easily be covered by the fetcher.
		currentBlock := pm.blockchain.CurrentBlock()
		if trueTD.Cmp(pm.blockchain.GetTd(currentBlock.Hash(), currentBlock.NumberU64())) > 0 {
			go pm.synchronise(p)
		}
	}
//------------------------ 以上 handleMsg

// Enqueue tries to fill gaps the the fetcher's future import queue.
// 发给inject通道，当前协程在handleMsg，通过通道发送给fetcher的协程处理
func (f *Fetcher) Enqueue(peer string, block *types.Block) error {
	op := &inject{
		origin: peer,
		block:  block,
	}
	select {
	case f.inject <- op:
		return nil
	case <-f.quit:
		return errTerminated
	}
}

//------------------------ 以下 fetcher.loop处理inject部分
case op := <-f.inject:
	// A direct block insertion was requested, try and fill any pending gaps
	// 区块加入队列，首先也填入未决的间距
	propBroadcastInMeter.Mark(1)
	f.enqueue(op.origin, op.block)

//------------------------  如队列函数

// enqueue schedules a new future import operation, if the block to be imported
// has not yet been seen.
// 把导入的新区块加入到队列，主要操作queue, queues, queued这3个变量，quque用来保存要插入的区块，
// 按高度排序，queues记录了在队列中某个peer传来的区块的数量，用来做对抗DoS攻击，queued用来
// 判断某个区块是否已经在队列，防止2次插入，浪费时间
func (f *Fetcher) enqueue(peer string, block *types.Block) {
	hash := block.Hash()

	// Ensure the peer isn't DOSing us
	// 防止peer的DOS攻击
	count := f.queues[peer] + 1
	if count > blockLimit {
		log.Debug("Discarded propagated block, exceeded allowance", "peer", peer, "number", block.Number(), "hash", hash, "limit", blockLimit)
		propBroadcastDOSMeter.Mark(1)
		f.forgetHash(hash)
		return
	}
	// Discard any past or too distant blocks
	// 高度检查：未来太远的块丢弃
	if dist := int64(block.NumberU64()) - int64(f.chainHeight()); dist < -maxUncleDist || dist > maxQueueDist {
		log.Debug("Discarded propagated block, too far away", "peer", peer, "number", block.Number(), "hash", hash, "distance", dist)
		propBroadcastDropMeter.Mark(1)
		f.forgetHash(hash)
		return
	}
	// Schedule the block for future importing
	// 块先加入优先级队列，加入链之前，还有很多要做
	if _, ok := f.queued[hash]; !ok {
		op := &inject{
			origin: peer,
			block:  block,
		}
		f.queues[peer] = count
		f.queued[hash] = op
		f.queue.Push(op, -float32(block.NumberU64()))
		if f.queueChangeHook != nil {
			f.queueChangeHook(op.block.Hash(), true)
		}
		log.Debug("Queued propagated block", "peer", peer, "number", block.Number(), "hash", hash, "queued", f.queue.Size())
	}
}
```

### fetcher队列处理

本节我们看看，区块加入队列后，fetcher如何处理区块，为何不直接校验区块，插入到本地链？

由于以太坊又Uncle的机制，节点可能收到老一点的一些区块。另外，节点可能由于网络原因，落后了几个区块，所以可能收到“未来”的一些区块，这些区块都不能直接插入到本地链。

区块入的队列是一个优先级队列，高度低的区块会被优先取出来。`fetcher.loop`是单独协程，不断运转，清理fecther中的事务和事件。首先会清理正在`fetching`的区块，但已经超时。然后处理优先级队列中的区块，判断高度是否是下一个区块，如果是则调用`f.insert()`函数，校验后调用`BlockChain.InsertChain()`，成功插入后，**广播新区块的Hash**。

```go
// Loop is the main fetcher loop, checking and processing various notification
// events.
func (f *Fetcher) loop() {
	// Iterate the block fetching until a quit is requested
	fetchTimer := time.NewTimer(0)
	completeTimer := time.NewTimer(0)

	for {
		// Clean up any expired block fetches
		// 清理过期的区块
		for hash, announce := range f.fetching {
			if time.Since(announce.time) > fetchTimeout {
				f.forgetHash(hash)
			}
		}
		// Import any queued blocks that could potentially fit
		// 导入队列中合适的块
		height := f.chainHeight()
		for !f.queue.Empty() {
			op := f.queue.PopItem().(*inject)
			hash := op.block.Hash()
			if f.queueChangeHook != nil {
				f.queueChangeHook(hash, false)
			}
			// If too high up the chain or phase, continue later
			// 块不是链需要的下一个块，再入优先级队列，停止循环
			number := op.block.NumberU64()
			if number > height+1 {
				f.queue.Push(op, -float32(number))
				if f.queueChangeHook != nil {
					f.queueChangeHook(hash, true)
				}
				break
			}
			// Otherwise if fresh and still unknown, try and import
			// 高度正好是我们想要的，并且链上也没有这个块
			if number+maxUncleDist < height || f.getBlock(hash) != nil {
				f.forgetBlock(hash)
				continue
			}
			// 那么，块插入链
			f.insert(op.origin, op.block)
		}
        
        //省略
    }
}
```

```go
func (f *Fetcher) insert(peer string, block *types.Block) {
	hash := block.Hash()

	// Run the import on a new thread
	log.Debug("Importing propagated block", "peer", peer, "number", block.Number(), "hash", hash)
	go func() {
		defer func() { f.done <- hash }()

		// If the parent's unknown, abort insertion
		parent := f.getBlock(block.ParentHash())
		if parent == nil {
			log.Debug("Unknown parent of propagated block", "peer", peer, "number", block.Number(), "hash", hash, "parent", block.ParentHash())
			return
		}
		// Quickly validate the header and propagate the block if it passes
		// 验证区块头，成功后广播区块
		switch err := f.verifyHeader(block.Header()); err {
		case nil:
			// All ok, quickly propagate to our peers
			propBroadcastOutTimer.UpdateSince(block.ReceivedAt)
			go f.broadcastBlock(block, true)

		case consensus.ErrFutureBlock:
			// Weird future block, don't fail, but neither propagate

		default:
			// Something went very wrong, drop the peer
			log.Debug("Propagated block verification failed", "peer", peer, "number", block.Number(), "hash", hash, "err", err)
			f.dropPeer(peer)
			return
		}
		// Run the actual import and log any issues
		// 调用回调函数，实际是blockChain.insertChain
		if _, err := f.insertChain(types.Blocks{block}); err != nil {
			log.Debug("Propagated block import failed", "peer", peer, "number", block.Number(), "hash", hash, "err", err)
			return
		}
		// If import succeeded, broadcast the block
		propAnnounceOutTimer.UpdateSince(block.ReceivedAt)
		go f.broadcastBlock(block, false)

		// Invoke the testing hook if needed
		if f.importedHook != nil {
			f.importedHook(block)
		}
	}()
}
```



### NewBlockHashesMsg的处理

本节介绍NewBlockHashesMsg的处理，其实，消息处理是简单的，而复杂一点的是从Peer哪获取完整的区块，下节再看。

流程如下:

1. 对消息进行RLP解码，然后标记Peer已经知道此区块。
2. 寻找出本地区块链不存在的区块Hash值，把这些未知的Hash通知给fetcher。
3. `fetcher.Notify`记录好通知信息，塞入`notify`通道，以便交给fetcher的协程。
4. `fetcher.loop()`会对`notify`中的消息进行处理，确认区块并非DOS攻击，然后检查区块的高度，判断该区块是否已经在`fetching`或者`comleting(代表已经下载区块头，在下载body)`，如果都没有，则加入到`announced`中，触发0s定时器，进行处理。

关于`announced`下节再介绍。

```go
// handleMsg()部分
case msg.Code == NewBlockHashesMsg:
	var announces newBlockHashesData
	if err := msg.Decode(&announces); err != nil {
		return errResp(ErrDecode, "%v: %v", msg, err)
	}
	// Mark the hashes as present at the remote node
	for _, block := range announces {
		p.MarkBlock(block.Hash)
	}
	// Schedule all the unknown hashes for retrieval
	// 把本地链没有的块hash找出来，交给fetcher去下载
	unknown := make(newBlockHashesData, 0, len(announces))
	for _, block := range announces {
		if !pm.blockchain.HasBlock(block.Hash, block.Number) {
			unknown = append(unknown, block)
		}
	}
	for _, block := range unknown {
		pm.fetcher.Notify(p.id, block.Hash, block.Number, time.Now(), p.RequestOneHeader, p.RequestBodies)
	}
```

```go
// Notify announces the fetcher of the potential availability of a new block in
// the network.
// 通知fetcher（自己）有新块产生，没有块实体，有hash、高度等信息
func (f *Fetcher) Notify(peer string, hash common.Hash, number uint64, time time.Time,
	headerFetcher headerRequesterFn, bodyFetcher bodyRequesterFn) error {
	block := &announce{
		hash:        hash,
		number:      number,
		time:        time,
		origin:      peer,
		fetchHeader: headerFetcher,
		fetchBodies: bodyFetcher,
	}
	select {
	case f.notify <- block:
		return nil
	case <-f.quit:
		return errTerminated
	}
}
```

```go
// fetcher.loop()的notify通道消息处理
case notification := <-f.notify:
	// A block was announced, make sure the peer isn't DOSing us
	propAnnounceInMeter.Mark(1)
	count := f.announces[notification.origin] + 1
	if count > hashLimit {
		log.Debug("Peer exceeded outstanding announces", "peer", notification.origin, "limit", hashLimit)
		propAnnounceDOSMeter.Mark(1)
		break
	}

	// If we have a valid block number, check that it's potentially useful
	// 高度检查
	if notification.number > 0 {
		if dist := int64(notification.number) - int64(f.chainHeight()); dist < -maxUncleDist || dist > maxQueueDist {
			log.Debug("Peer discarded announcement", "peer", notification.origin, "number", notification.number, "hash", notification.hash, "distance", dist)
			propAnnounceDropMeter.Mark(1)
			break
		}
	}

	// All is well, schedule the announce if block's not yet downloading
	// 检查是否已经在下载，已下载则忽略
	if _, ok := f.fetching[notification.hash]; ok {
		break
	}
	if _, ok := f.completing[notification.hash]; ok {
		break
	}
	// 更新peer已经通知给我们的区块数量
	f.announces[notification.origin] = count
	// 把通知信息加入到announced，供调度
	f.announced[notification.hash] = append(f.announced[notification.hash], notification)
	if f.announceChangeHook != nil && len(f.announced[notification.hash]) == 1 {
		f.announceChangeHook(notification.hash, true)
	}
	if len(f.announced) == 1 {
		// 有通知放入到announced，则重设0s定时器，loop的另外一个分支会处理这些通知
		f.rescheduleFetch(fetchTimer)
	}
```

### fetcher获取完整区块

本节介绍fetcher获取完整区块的过程，这也是fetcher最重要的功能，会涉及到fetcher至少80%的代码。单独拉放一大节吧。

## Fetcher的大头

Fetcher最主要的功能就是获取完整的区块，然后在合适的实际交给InsertChain去验证和插入到本地区块链。我们还是从宏观入手，看Fetcher是如何工作的，一定要先掌握好宏观，因为代码层面上没有这么清晰。

### 宏观

首先，看两个节点是如何交互，获取完整区块，使用时序图的方式看一下，见图6，流程很清晰不再文字介绍。

![图6：节点获取完整区块的时序图](https://lessisbetter.site/images/image-20180822103401508.png-own)



再看下获取区块过程中，fetcher内部的状态转移，它使用状态来记录，要获取的区块在什么阶段，见图7。我稍微解释一下：

1. 收到`NewBlockHashesMsg`后，相关信息会记录到`announced`，进入`announced`状态，代表了本节点接收了消息。
2. `announced`由fetcher协程处理，经过校验后，会向给他发送消息的Peer发送请求，请求该区块的区块头，然后进入`fetching`状态。
3. 获取区块头后，如果区块头表示没有交易和uncle，则转移到`completing`状态，并且使用区块头合成完整的区块，加入到`queued`优先级队列。
4. 获取区块头后，如果区块头表示该区块有交易和uncle，则转移到`fetched`状态，然后发送请求，请求交易和uncle，然后转移到`completing`状态。
5. 收到交易和uncle后，使用头、交易、uncle这3个信息，生成完整的区块，加入到队列`queued`。



![图7：获取区块状态转移图](https://lessisbetter.site/images/image-20180822103701006.png-own)





### 微观

接下来就是从代码角度看如何获取完整区块的流程了，有点多，看不懂的时候，再回顾下上面宏观的介绍图。



首先看Fetcher的定义，它存放了通信数据和状态管理，捡加注释的看，上文提到的状态，里面都有。

```go
// Fetcher is responsible for accumulating block announcements from various peers
// and scheduling them for retrieval.
// 积累块通知，然后调度获取这些块
type Fetcher struct {
	// Various event channels
    // 收到区块hash值的通道
	notify chan *announce
    // 收到完整区块的通道
	inject chan *inject

	blockFilter chan chan []*types.Block
	// 过滤header的通道的通道
	headerFilter chan chan *headerFilterTask
	// 过滤body的通道的通道
	bodyFilter chan chan *bodyFilterTask

	done chan common.Hash
	quit chan struct{}

	// Announce states
	// Peer已经给了本节点多少区块头通知
	announces map[string]int // Per peer announce counts to prevent memory exhaustion
	// 已经announced的区块列表
	announced map[common.Hash][]*announce // Announced blocks, scheduled for fetching
	// 正在fetching区块头的请求
	fetching map[common.Hash]*announce // Announced blocks, currently fetching
	// 已经fetch到区块头，还差body的请求，用来获取body
	fetched map[common.Hash][]*announce // Blocks with headers fetched, scheduled for body retrieval
	// 已经得到区块头的
	completing map[common.Hash]*announce // Blocks with headers, currently body-completing

	// Block cache
	// queue，优先级队列，高度做优先级
	// queues，queued队列中某个peer发来的区块数量
	// queued，等待插入到区块链的区块，实际插入时从queue取，queued就是用来快速判断区块是否在队列的
	queue  *prque.Prque            // Queue containing the import operations (block number sorted)
	queues map[string]int          // Per peer block counts to prevent memory exhaustion
	queued map[common.Hash]*inject // Set of already queued blocks (to dedupe imports)

	// Callbacks
	getBlock       blockRetrievalFn   // Retrieves a block from the local chain
	verifyHeader   headerVerifierFn   // Checks if a block's headers have a valid proof of work，验证区块头，包含了PoW验证
	broadcastBlock blockBroadcasterFn // Broadcasts a block to connected peers，广播给peer
	chainHeight    chainHeightFn      // Retrieves the current chain's height
	insertChain    chainInsertFn      // Injects a batch of blocks into the chain，插入区块到链的函数
	dropPeer       peerDropFn         // Drops a peer for misbehaving

	// Testing hooks
	announceChangeHook func(common.Hash, bool) // Method to call upon adding or deleting a hash from the announce list
	queueChangeHook    func(common.Hash, bool) // Method to call upon adding or deleting a block from the import queue
	fetchingHook       func([]common.Hash)     // Method to call upon starting a block (eth/61) or header (eth/62) fetch
	completingHook     func([]common.Hash)     // Method to call upon starting a block body fetch (eth/62)
	importedHook       func(*types.Block)      // Method to call upon successful block import (both eth/61 and eth/62)
}
```



`NewBlockHashesMsg`消息的处理[前面的小节已经讲过了](#NewBlockHashesMsg的处理)，不记得可向前翻看。这里从`announced`的状态处理说起。`loop()`中，`fetchTimer`超时后，代表了收到了消息通知，需要处理，会从`announced`中选择出需要处理的通知，然后创建请求，请求区块头，由于可能有很多节点都通知了它某个区块的Hash，所以**随机**的从这些发送消息的Peer中选择一个Peer，发送请求的时候，为每个Peer都创建了单独的协程。

```go
case <-fetchTimer.C:
	// At least one block's timer ran out, check for needing retrieval
	// 有区块通知，去处理
	request := make(map[string][]common.Hash)

	for hash, announces := range f.announced {
		if time.Since(announces[0].time) > arriveTimeout-gatherSlack {
			// Pick a random peer to retrieve from, reset all others
			// 可能有很多peer都发送了这个区块的hash值，随机选择一个peer
			announce := announces[rand.Intn(len(announces))]
			f.forgetHash(hash)

			// If the block still didn't arrive, queue for fetching
			// 本地还没有这个区块，创建获取区块的请求
			if f.getBlock(hash) == nil {
				request[announce.origin] = append(request[announce.origin], hash)
				f.fetching[hash] = announce
			}
		}
	}
	// Send out all block header requests
	// 把所有的request发送出去
	// 为每一个peer都创建一个协程，然后请求所有需要从该peer获取的请求
	for peer, hashes := range request {
		log.Trace("Fetching scheduled headers", "peer", peer, "list", hashes)

		// Create a closure of the fetch and schedule in on a new thread
		fetchHeader, hashes := f.fetching[hashes[0]].fetchHeader, hashes
		go func() {
			if f.fetchingHook != nil {
				f.fetchingHook(hashes)
			}
			for _, hash := range hashes {
				headerFetchMeter.Mark(1)
				fetchHeader(hash) // Suboptimal, but protocol doesn't allow batch header retrievals
			}
		}()
	}
	// Schedule the next fetch if blocks are still pending
	f.rescheduleFetch(fetchTimer)
```

从`Notify`的调用中，可以看出，`fetcherHeader()`的实际函数是`RequestOneHeader()`，该函数使用的消息是`GetBlockHeadersMsg`，可以用来请求多个区块头，不过fetcher只请求一个。

```go
pm.fetcher.Notify(p.id, block.Hash, block.Number, time.Now(), p.RequestOneHeader, p.RequestBodies)

// RequestOneHeader is a wrapper around the header query functions to fetch a
// single header. It is used solely by the fetcher.
func (p *peer) RequestOneHeader(hash common.Hash) error {
	p.Log().Debug("Fetching single header", "hash", hash)
	return p2p.Send(p.rw, GetBlockHeadersMsg, &getBlockHeadersData{Origin: hashOrNumber{Hash: hash}, Amount: uint64(1), Skip: uint64(0), Reverse: false})
}
```

`GetBlockHeadersMsg`的处理如下：因为它是获取多个区块头的，所以处理起来比较“麻烦”，还好，fetcher只获取一个区块头，其处理在20行~33行，获取下一个区块头的处理逻辑，这里就不看了，最后调用`SendBlockHeaders()`将区块头发送给请求的节点，消息是`BlockHeadersMsg`。

```go
// handleMsg()
// Block header query, collect the requested headers and reply
case msg.Code == GetBlockHeadersMsg:
	// Decode the complex header query
	var query getBlockHeadersData
	if err := msg.Decode(&query); err != nil {
		return errResp(ErrDecode, "%v: %v", msg, err)
	}
	hashMode := query.Origin.Hash != (common.Hash{})

	// Gather headers until the fetch or network limits is reached
	// 收集区块头，直到达到限制
	var (
		bytes   common.StorageSize
		headers []*types.Header
		unknown bool
	)
	// 自己已知区块 && 少于查询的数量 && 大小小于2MB && 小于能下载的最大数量
	for !unknown && len(headers) < int(query.Amount) && bytes < softResponseLimit && len(headers) < downloader.MaxHeaderFetch {
		// Retrieve the next header satisfying the query
		// 获取区块头
		var origin *types.Header
		if hashMode {
            // fetcher 使用的模式
			origin = pm.blockchain.GetHeaderByHash(query.Origin.Hash)
		} else {
			origin = pm.blockchain.GetHeaderByNumber(query.Origin.Number)
		}
		if origin == nil {
			break
		}
		number := origin.Number.Uint64()
		headers = append(headers, origin)
		bytes += estHeaderRlpSize

		// Advance to the next header of the query
		// 下一个区块头的获取，不同策略，方式不同
		switch {
		case query.Origin.Hash != (common.Hash{}) && query.Reverse:
            // ...
        }
    }
	return p.SendBlockHeaders(headers)
```

`BlockHeadersMsg`的处理很有意思，因为`GetBlockHeadersMsg`并不是fetcher独占的消息，downloader也可以调用，所以，响应消息的处理需要分辨出是fetcher请求的，还是downloader请求的。它的处理逻辑是：fetcher先过滤收到的区块头，如果fetcher不要的，那就是downloader的，在调用`fetcher.FilterHeaders`的时候，fetcher就将自己要的区块头拿走了。

```go
// handleMsg()
case msg.Code == BlockHeadersMsg:
	// A batch of headers arrived to one of our previous requests
	var headers []*types.Header
	if err := msg.Decode(&headers); err != nil {
		return errResp(ErrDecode, "msg %v: %v", msg, err)
	}
	// If no headers were received, but we're expending a DAO fork check, maybe it's that
	// 检查是不是当前DAO的硬分叉
	if len(headers) == 0 && p.forkDrop != nil {
		// Possibly an empty reply to the fork header checks, sanity check TDs
		verifyDAO := true

		// If we already have a DAO header, we can check the peer's TD against it. If
		// the peer's ahead of this, it too must have a reply to the DAO check
		if daoHeader := pm.blockchain.GetHeaderByNumber(pm.chainconfig.DAOForkBlock.Uint64()); daoHeader != nil {
			if _, td := p.Head(); td.Cmp(pm.blockchain.GetTd(daoHeader.Hash(), daoHeader.Number.Uint64())) >= 0 {
				verifyDAO = false
			}
		}
		// If we're seemingly on the same chain, disable the drop timer
		if verifyDAO {
			p.Log().Debug("Seems to be on the same side of the DAO fork")
			p.forkDrop.Stop()
			p.forkDrop = nil
			return nil
		}
	}
	// Filter out any explicitly requested headers, deliver the rest to the downloader
	// 过滤是不是fetcher请求的区块头，去掉fetcher请求的区块头再交给downloader
	filter := len(headers) == 1
	if filter {
		// If it's a potential DAO fork check, validate against the rules
		// 检查是否硬分叉
		if p.forkDrop != nil && pm.chainconfig.DAOForkBlock.Cmp(headers[0].Number) == 0 {
			// Disable the fork drop timer
			p.forkDrop.Stop()
			p.forkDrop = nil

			// Validate the header and either drop the peer or continue
			if err := misc.VerifyDAOHeaderExtraData(pm.chainconfig, headers[0]); err != nil {
				p.Log().Debug("Verified to be on the other side of the DAO fork, dropping")
				return err
			}
			p.Log().Debug("Verified to be on the same side of the DAO fork")
			return nil
		}
		// Irrelevant of the fork checks, send the header to the fetcher just in case
		// 使用fetcher过滤区块头
		headers = pm.fetcher.FilterHeaders(p.id, headers, time.Now())
	}
	// 剩下的区块头交给downloader
	if len(headers) > 0 || !filter {
		err := pm.downloader.DeliverHeaders(p.id, headers)
		if err != nil {
			log.Debug("Failed to deliver headers", "err", err)
		}
	}
```

`FilterHeaders()`是一个很有大智慧的函数，看起来耐人寻味，但实在妙。它要把所有的区块头，都传递给fetcher协程，还要获取fetcher协程处理后的结果。`fetcher.headerFilter`是存放通道的通道，而`filter`是存放包含区块头过滤任务的通道。它先把`filter`传递给了`headerFilter`，这样`fetcher`协程就在另外一段等待了，而后将`headerFilterTask`传入`filter`，fetcher就能读到数据了，处理后，再将数据写回`filter`而刚好被`FilterHeaders`函数处理了，该函数实际运行在`handleMsg()`的协程中。

每个Peer都会分配一个ProtocolManager然后处理该Peer的消息，但`fetcher`只有一个事件处理协程，如果不创建一个`filter`，fetcher哪知道是谁发给它的区块头呢？过滤之后，该如何发回去呢？

```go
// FilterHeaders extracts all the headers that were explicitly requested by the fetcher,
// returning those that should be handled differently.
// 寻找出fetcher请求的区块头
func (f *Fetcher) FilterHeaders(peer string, headers []*types.Header, time time.Time) []*types.Header {
	log.Trace("Filtering headers", "peer", peer, "headers", len(headers))

	// Send the filter channel to the fetcher
	// 任务通道
	filter := make(chan *headerFilterTask)

	select {
	// 任务通道发送到这个通道
	case f.headerFilter <- filter:
	case <-f.quit:
		return nil
	}
	// Request the filtering of the header list
	// 创建过滤任务，发送到任务通道
	select {
	case filter <- &headerFilterTask{peer: peer, headers: headers, time: time}:
	case <-f.quit:
		return nil
	}
	// Retrieve the headers remaining after filtering
	// 从任务通道，获取过滤的结果并返回
	select {
	case task := <-filter:
		return task.headers
	case <-f.quit:
		return nil
	}
}
```

接下来要看`f.headerFilter`的处理，这段代码有90行，它做了以下几件事：

1. 从`f.headerFilter`取出`filter`，然后取出过滤任务`task`。
2. 它把区块头分成3类：`unknown`这不是分是要返回给调用者的，即`handleMsg()`, `incomplete`存放还需要获取body的区块头，`complete`存放只包含区块头的区块。遍历所有的区块头，填到到对应的分类中，具体的判断可看18行的注释，记住宏观中将的状态转移图。
3. 把`unknonw`中的区块返回给`handleMsg()`。
4. 把 `incomplete`的区块头获取状态移动到`fetched`状态，然后触发定时器，以便去处理`complete`的区块。
5. 把`compelete`的区块加入到`queued`。

```go
// fetcher.loop()
case filter := <-f.headerFilter:
	// Headers arrived from a remote peer. Extract those that were explicitly
	// requested by the fetcher, and return everything else so it's delivered
	// to other parts of the system.
	// 收到从远端节点发送的区块头，过滤出fetcher请求的
	// 从任务通道获取过滤任务
	var task *headerFilterTask
	select {
	case task = <-filter:
	case <-f.quit:
		return
	}
	headerFilterInMeter.Mark(int64(len(task.headers)))

	// Split the batch of headers into unknown ones (to return to the caller),
	// known incomplete ones (requiring body retrievals) and completed blocks.
	// unknown的不是fetcher请求的，complete放没有交易和uncle的区块，有头就够了，incomplete放
	// 还需要获取uncle和交易的区块
	unknown, incomplete, complete := []*types.Header{}, []*announce{}, []*types.Block{}
	// 遍历所有收到的header
	for _, header := range task.headers {
		hash := header.Hash()

		// Filter fetcher-requested headers from other synchronisation algorithms
		// 是正在获取的hash，并且对应请求的peer，并且未fetched，未completing，未queued
		if announce := f.fetching[hash]; announce != nil && announce.origin == task.peer && f.fetched[hash] == nil && f.completing[hash] == nil && f.queued[hash] == nil {
			// If the delivered header does not match the promised number, drop the announcer
			// 高度校验，竟然不匹配，扰乱秩序，peer肯定是坏蛋。
			if header.Number.Uint64() != announce.number {
				log.Trace("Invalid block number fetched", "peer", announce.origin, "hash", header.Hash(), "announced", announce.number, "provided", header.Number)
				f.dropPeer(announce.origin)
				f.forgetHash(hash)
				continue
			}
			// Only keep if not imported by other means
			// 本地链没有当前区块
			if f.getBlock(hash) == nil {
				announce.header = header
				announce.time = task.time

				// If the block is empty (header only), short circuit into the final import queue
				// 如果区块没有交易和uncle，加入到complete
				if header.TxHash == types.DeriveSha(types.Transactions{}) && header.UncleHash == types.CalcUncleHash([]*types.Header{}) {
					log.Trace("Block empty, skipping body retrieval", "peer", announce.origin, "number", header.Number, "hash", header.Hash())

					block := types.NewBlockWithHeader(header)
					block.ReceivedAt = task.time

					complete = append(complete, block)
					f.completing[hash] = announce
					continue
				}
				// Otherwise add to the list of blocks needing completion
				// 否则就是不完整的区块
				incomplete = append(incomplete, announce)
			} else {
				log.Trace("Block already imported, discarding header", "peer", announce.origin, "number", header.Number, "hash", header.Hash())
				f.forgetHash(hash)
			}
		} else {
			// Fetcher doesn't know about it, add to the return list
			// 没请求过的header
			unknown = append(unknown, header)
		}
	}
	// 把未知的区块头，再传递会filter
	headerFilterOutMeter.Mark(int64(len(unknown)))
	select {
	case filter <- &headerFilterTask{headers: unknown, time: task.time}:
	case <-f.quit:
		return
	}
	// Schedule the retrieved headers for body completion
	// 把未完整的区块加入到fetched，跳过已经在completeing中的，然后触发completeTimer定时器
	for _, announce := range incomplete {
		hash := announce.header.Hash()
		if _, ok := f.completing[hash]; ok {
			continue
		}
		f.fetched[hash] = append(f.fetched[hash], announce)
		if len(f.fetched) == 1 {
			f.rescheduleComplete(completeTimer)
		}
	}
	// Schedule the header-only blocks for import
	// 把只有头的区块入队列
	for _, block := range complete {
		if announce := f.completing[block.Hash()]; announce != nil {
			f.enqueue(announce.origin, block)
		}
	}
```

跟随状态图的转义，剩下的工作是`fetched`转移到`completing`，上面的流程已经触发了`completeTimer`定时器，超时后就会处理，流程与请求Header类似，不再赘述，此时发送的请求消息是`GetBlockBodiesMsg`，实际调的函数是`RequestBodies`。

```go
// fetcher.loop()
case <-completeTimer.C:
	// At least one header's timer ran out, retrieve everything
	// 至少有1个header已经获取完了
	request := make(map[string][]common.Hash)

	// 遍历所有待获取body的announce
	for hash, announces := range f.fetched {
		// Pick a random peer to retrieve from, reset all others
		// 随机选一个Peer发送请求，因为可能已经有很多Peer通知它这个区块了
		announce := announces[rand.Intn(len(announces))]
		f.forgetHash(hash)

		// If the block still didn't arrive, queue for completion
		// 如果本地没有这个区块，则放入到completing，创建请求
		if f.getBlock(hash) == nil {
			request[announce.origin] = append(request[announce.origin], hash)
			f.completing[hash] = announce
		}
	}
	// Send out all block body requests
	// 发送所有的请求，获取body，依然是每个peer一个单独协程
	for peer, hashes := range request {
		log.Trace("Fetching scheduled bodies", "peer", peer, "list", hashes)

		// Create a closure of the fetch and schedule in on a new thread
		if f.completingHook != nil {
			f.completingHook(hashes)
		}
		bodyFetchMeter.Mark(int64(len(hashes)))
		go f.completing[hashes[0]].fetchBodies(hashes)
	}
	// Schedule the next fetch if blocks are still pending
	f.rescheduleComplete(completeTimer)
```

`handleMsg()`处理该消息也是干净利落，直接获取RLP格式的body，然后发送响应消息。

```go
// handleMsg()
case msg.Code == GetBlockBodiesMsg:
	// Decode the retrieval message
	msgStream := rlp.NewStream(msg.Payload, uint64(msg.Size))
	if _, err := msgStream.List(); err != nil {
		return err
	}
	// Gather blocks until the fetch or network limits is reached
	var (
		hash   common.Hash
		bytes  int
		bodies []rlp.RawValue
	)

	// 遍历所有请求
	for bytes < softResponseLimit && len(bodies) < downloader.MaxBlockFetch {
		// Retrieve the hash of the next block
		if err := msgStream.Decode(&hash); err == rlp.EOL {
			break
		} else if err != nil {
			return errResp(ErrDecode, "msg %v: %v", msg, err)
		}
		// Retrieve the requested block body, stopping if enough was found
		// 获取body，RLP格式
		if data := pm.blockchain.GetBodyRLP(hash); len(data) != 0 {
			bodies = append(bodies, data)
			bytes += len(data)
		}
	}
	return p.SendBlockBodiesRLP(bodies)
```

响应消息`BlockBodiesMsg`的处理与处理获取header的处理原理相同，先交给fetcher过滤，然后剩下的才是downloader的。需要注意一点，响应消息里只包含交易列表和叔块列表。

```go
// handleMsg()
case msg.Code == BlockBodiesMsg:
	// A batch of block bodies arrived to one of our previous requests
	var request blockBodiesData
	if err := msg.Decode(&request); err != nil {
		return errResp(ErrDecode, "msg %v: %v", msg, err)
	}
	// Deliver them all to the downloader for queuing
	// 传递给downloader去处理
	transactions := make([][]*types.Transaction, len(request))
	uncles := make([][]*types.Header, len(request))

	for i, body := range request {
		transactions[i] = body.Transactions
		uncles[i] = body.Uncles
	}
	// Filter out any explicitly requested bodies, deliver the rest to the downloader
	// 先让fetcher过滤去fetcher请求的body，剩下的给downloader
	filter := len(transactions) > 0 || len(uncles) > 0
	if filter {
		transactions, uncles = pm.fetcher.FilterBodies(p.id, transactions, uncles, time.Now())
	}

	// 剩下的body交给downloader
	if len(transactions) > 0 || len(uncles) > 0 || !filter {
		err := pm.downloader.DeliverBodies(p.id, transactions, uncles)
		if err != nil {
			log.Debug("Failed to deliver bodies", "err", err)
		}
	}
```

过滤函数的原理也与Header相同。

```go
// FilterBodies extracts all the block bodies that were explicitly requested by
// the fetcher, returning those that should be handled differently.
// 过去出fetcher请求的body，返回它没有处理的，过程类型header的处理
func (f *Fetcher) FilterBodies(peer string, transactions [][]*types.Transaction, uncles [][]*types.Header, time time.Time) ([][]*types.Transaction, [][]*types.Header) {
	log.Trace("Filtering bodies", "peer", peer, "txs", len(transactions), "uncles", len(uncles))

	// Send the filter channel to the fetcher
	filter := make(chan *bodyFilterTask)

	select {
	case f.bodyFilter <- filter:
	case <-f.quit:
		return nil, nil
	}
	// Request the filtering of the body list
	select {
	case filter <- &bodyFilterTask{peer: peer, transactions: transactions, uncles: uncles, time: time}:
	case <-f.quit:
		return nil, nil
	}
	// Retrieve the bodies remaining after filtering
	select {
	case task := <-filter:
		return task.transactions, task.uncles
	case <-f.quit:
		return nil, nil
	}
}
```

实际过滤body的处理瞧一下，这和Header的处理是不同的。直接看不点：

1. 它要的区块，单独取出来存到`blocks`中，它不要的继续留在`task`中。
2. 判断是不是fetcher请求的方法：如果交易列表和叔块列表计算出的hash值与区块头中的一样，并且消息来自请求的Peer，则就是fetcher请求的。
3. 将`blocks`中的区块加入到`queued`，终结。

```go
case filter := <-f.bodyFilter:
	// Block bodies arrived, extract any explicitly requested blocks, return the rest
	var task *bodyFilterTask
	select {
	case task = <-filter:
	case <-f.quit:
		return
	}
	bodyFilterInMeter.Mark(int64(len(task.transactions)))

	blocks := []*types.Block{}
	// 获取的每个body的txs列表和uncle列表
	// 遍历每个区块的txs列表和uncle列表，计算hash后判断是否是当前fetcher请求的body
	for i := 0; i < len(task.transactions) && i < len(task.uncles); i++ {
		// Match up a body to any possible completion request
		matched := false

		// 遍历所有保存的请求，因为tx和uncle，不知道它是属于哪个区块的，只能去遍历所有的请求，通常量不大，所以遍历没有性能影响
		for hash, announce := range f.completing {
			if f.queued[hash] == nil {
				// 把传入的每个块的hash和unclehash和它请求出去的记录进行对比，匹配则说明是fetcher请求的区块body
				txnHash := types.DeriveSha(types.Transactions(task.transactions[i]))
				uncleHash := types.CalcUncleHash(task.uncles[i])

				if txnHash == announce.header.TxHash && uncleHash == announce.header.UncleHash && announce.origin == task.peer {
					// Mark the body matched, reassemble if still unknown
					matched = true

					// 如果当前链还没有这个区块，则收集这个区块，合并成新区块
					if f.getBlock(hash) == nil {
						block := types.NewBlockWithHeader(announce.header).WithBody(task.transactions[i], task.uncles[i])
						block.ReceivedAt = task.time

						blocks = append(blocks, block)
					} else {
						f.forgetHash(hash)
					}
				}
			}
		}
		// 从task中移除fetcher请求的数据
		if matched {
			task.transactions = append(task.transactions[:i], task.transactions[i+1:]...)
			task.uncles = append(task.uncles[:i], task.uncles[i+1:]...)
			i--
			continue
		}
	}

	// 将剩余的数据返回
	bodyFilterOutMeter.Mark(int64(len(task.transactions)))
	select {
	case filter <- task:
	case <-f.quit:
		return
	}
	// Schedule the retrieved blocks for ordered import
	// 把收集的区块加入到队列
	for _, block := range blocks {
		if announce := f.completing[block.Hash()]; announce != nil {
			f.enqueue(announce.origin, block)
		}
	}
}
```



至此，fetcher获取完整区块的流程讲完了，fetcher模块中80%的代码也都贴出来了，还有2个值得看看的函数：

1. `forgetHash(hash common.Hash) `：用于清空指定hash值的记/状态录信息。
2. `forgetBlock(hash common.Hash)`：用于从队列中移除一个区块。



最后了，再回到开始看看fetcher模块和新区块的传播流程，有没有豁然开朗。

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/08/30/ethereum-fetcher-module-and-block-propagate/](http://lessisbetter.site/2018/08/30/ethereum-fetcher-module-and-block-propagate/)