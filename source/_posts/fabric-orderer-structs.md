---
title: Fabric 1.4源码解读 6：Orderer核心数据结构
date: 2019-11-18 20:45:23
tags: ['区块链', 'Fabric']
---


## 前言

许多Orderer的文章，都是从Orderer的启动过程讲起，今天换一种“乐高”角度，先看看有哪些“零件”，再看这些零件怎么配合。

Orderer负责接收交易，把交易打包成区块，然后区块在所有Orderer节点之间达成一致，再分发给Peer的功能，这涉及了：
- 网络：gRPC接收交易，向Peer发送区块
- 切块：把交易打包成区块
- 共识：所有Orderer节点达成一致

这些功能是由Orderer核心数据结构组织起来。

> 在Fabric中，通道和链在概念上都是一条区块链，所以本文中也会可能会混用链和通道。

## 核心数据结构

### Registrar

![Registrar](http://img.lessisbetter.site/2019-11-orderer-registrar.png)

代码中，这样描述Registrar：

> Registrar serves as a point of access and control for the individual channel resources.

可见它负责了每个channel资源的访问和控制点，也就说，要对某个通道怎么样，得从这入手。

```go
type Registrar struct {
	lock sync.RWMutex
	// 保存了多条链
	chains map[string]*ChainSupport

	// 共识插件
	consenters         map[string]consensus.Consenter
	ledgerFactory      blockledger.Factory
	signer             crypto.LocalSigner
    
	systemChannelID    string
	systemChannel      *ChainSupport
	...
}
```

- `chains`保存了每一条链，每一条链在Orderer中都以[ChainSupport](#ChainSupport)代表。
- `consenters`保存了所有的共识插件，每个共识插件都是一个[Consenter](#Consenter)，Fabric 1.4中共识插件有Solo、Kafka、EtcdRaft。
- `ledgerFactory`用来读取和创建链的账本。
- `signer`用来对Orderer中的数据进行签名，以及创建[SignatureHeader](http://lessisbetter.site/2019/11/10/how-fabric-verify-signatures/#解密SignatureHeader)。
- `systemChannelID`和`systemChannel`分别是系统链ID、系统链实例。



### ChainSupport

![chainsupport](http://img.lessisbetter.site/2019-11-orderer-chainsupport.png)

ChainSupport汇集了一条通道所需要的所有资源，所以说一个ChainSupport代表了一条链。

```go
type ChainSupport struct {
	*ledgerResources
	msgprocessor.Processor
	*BlockWriter
	consensus.Chain
	cutter blockcutter.Receiver
	crypto.LocalSigner
}
```

ChainSupport 是一堆接口的集合，这些接口构成一条链所有的操作，接口可以分为4类：
- 账本：`ledgerResources`、`BlockWriter`分别是账本读写和把区块写入到账本。
- 消息：`msgprocessor.Processor`、`cutter`分别是处理交易和把交易切块。
- 共识：`consensus.Chain`是Orderer的共识实例，比如每条链都有自己的Raft共识实例，它们互不干扰。
- 签名：`crypto.LocalSigner`，同Registrar中的介绍。

### Chain

![Chain](http://img.lessisbetter.site/2019-11-orderer-chain.png)

Chain是接口，它的实现并不一条链，而是一条链的共识实例，可以是Solo、Kafka和EtcdRaft，它运行在单独的协程，使用Channel和ChainSupport通信，它调用其它接口完成切块，以及让所有的Orderer节点对交易达成一致。

```go
// Chain defines a way to inject messages for ordering.
// Note, that in order to allow flexibility in the implementation, it is the responsibility of the implementer
// to take the ordered messages, send them through the blockcutter.Receiver supplied via HandleChain to cut blocks,
// and ultimately write the ledger also supplied via HandleChain.  This design allows for two primary flows
// 1. Messages are ordered into a stream, the stream is cut into blocks, the blocks are committed (solo, kafka)
// 2. Messages are cut into blocks, the blocks are ordered, then the blocks are committed (sbft)
type Chain interface {
	// 普通消息/交易排序
	// Order accepts a message which has been processed at a given configSeq.
	// If the configSeq advances, it is the responsibility of the consenter
	// to revalidate and potentially discard the message
	// The consenter may return an error, indicating the message was not accepted
	Order(env *cb.Envelope, configSeq uint64) error

	// 配置消息/交易排序
	// Configure accepts a message which reconfigures the channel and will
	// trigger an update to the configSeq if committed.  The configuration must have
	// been triggered by a ConfigUpdate message. If the config sequence advances,
	// it is the responsibility of the consenter to recompute the resulting config,
	// discarding the message if the reconfiguration is no longer valid.
	// The consenter may return an error, indicating the message was not accepted
	Configure(config *cb.Envelope, configSeq uint64) error

	// 等待排序集群可用
	// WaitReady blocks waiting for consenter to be ready for accepting new messages.
	// This is useful when consenter needs to temporarily block ingress messages so
	// that in-flight messages can be consumed. It could return error if consenter is
	// in erroneous states. If this blocking behavior is not desired, consenter could
	// simply return nil.
	WaitReady() error

	// 当排序集群发送错误时，会关闭返回的通道
	// Errored returns a channel which will close when an error has occurred.
	// This is especially useful for the Deliver client, who must terminate waiting
	// clients when the consenter is not up to date.
	Errored() <-chan struct{}

	// 启动当前链
	// Start should allocate whatever resources are needed for staying up to date with the chain.
	// Typically, this involves creating a thread which reads from the ordering source, passes those
	// messages to a block cutter, and writes the resulting blocks to the ledger.
	Start()

	// 停止当前链，并释放资源
	// Halt frees the resources which were allocated for this Chain.
	Halt()
}
```

### Consenter

![Consenter](http://img.lessisbetter.site/2019-11-orderer-consenter.png)


```go
type Consenter interface {
	HandleChain(support ConsenterSupport, metadata *cb.Metadata) (Chain, error)
}
```

Consenter也是接口，它只有1个功能用来创建`Chain`。每种共识插件，都有自己单独的**consenter实现**，分别用来创建solo实例、kafka实例或etcdraft实例。

### ConsenterSupport

![ConsenterSupport](http://img.lessisbetter.site/2019-11-orderer-consentersupport.png)

ConsenterSupport为**consenter实现**提供所需的资源，其实就是共识用来访问外部数据的接口。

```go
// ConsenterSupport provides the resources available to a Consenter implementation.
type ConsenterSupport interface {
	crypto.LocalSigner
	msgprocessor.Processor

	// VerifyBlockSignature verifies a signature of a block with a given optional
	// configuration (can be nil).
	VerifyBlockSignature([]*cb.SignedData, *cb.ConfigEnvelope) error

	// 提供把消息切成块的接口
	// BlockCutter returns the block cutting helper for this channel.
	BlockCutter() blockcutter.Receiver

	// 当前链的orderer配置
	// SharedConfig provides the shared config from the channel's current config block.
	SharedConfig() channelconfig.Orderer

	// 当前链的通道配置
	// ChannelConfig provides the channel config from the channel's current config block.
	ChannelConfig() channelconfig.Channel

	// 生成区块
	// CreateNextBlock takes a list of messages and creates the next block based on the block with highest block number committed to the ledger
	// Note that either WriteBlock or WriteConfigBlock must be called before invoking this method a second time.
	CreateNextBlock(messages []*cb.Envelope) *cb.Block

	// 读区块
	// Block returns a block with the given number,
	// or nil if such a block doesn't exist.
	Block(number uint64) *cb.Block

	// 写区块
	// WriteBlock commits a block to the ledger.
	WriteBlock(block *cb.Block, encodedMetadataValue []byte)

	// 写配置区块并更新配置
	// WriteConfigBlock commits a block to the ledger, and applies the config update inside.
	WriteConfigBlock(block *cb.Block, encodedMetadataValue []byte)

	// Sequence returns the current config squence.
	Sequence() uint64

	// ChainID returns the channel ID this support is associated with.
	ChainID() string

	// Height returns the number of blocks in the chain this channel is associated with.
	Height() uint64

	// 以原始数据的格式追加区块，不像WriteBlock那样会修改元数据
	// Append appends a new block to the ledger in its raw form,
	// unlike WriteBlock that also mutates its metadata.
	Append(block *cb.Block) error
}
```

## 宏观视角

把上面介绍的各项，融合在一幅图中：
- Registrar 包容万象，主要是ChainSupport和Consenter，Consenter是可插拔的
- ChainSupport 代表了一条链，能够指向属于本条链的共识实例，该共识实例由对应共识类型的Consenter创建
- 共识实例使用ConsenterSupport访问共识外部资源

![](http://img.lessisbetter.site/2019-11-core-struct-of-orderer.png)

