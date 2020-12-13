---
title: Fabric 1.4源码解读 3：事件(Event)原理解读
date: 2019-09-20 19:46:41
tags: ['Fabric', '区块链']
---


## 前言

Event是应用和Fabric网络交互的一种方式，应用可以通过**SDK**向**Peer**订阅某种类型的事件，当Peer发现事件发生时，可以把Event发送给应用，应用获取到通知信息。


## Event功能介绍

Event从来源上可以分为2类：
1. 链码容器发出的Event
1. Peer上账本变更发出的Event

![fabric event](http://img.lessisbetter.site/2019-09-sdk-event.png)

*图源自[Tutorial Chaincode Event Listener on Hyperledger Fabric Java SDK](https://medium.com/coinmonks/tutorial-chaincode-event-listener-on-hyperledger-fabric-java-sdk-557304f1fe28)*

翻阅Node SDK和Go SDK的文档，发现SDK提供了4类事件：

1. BlockEvent，可以用来监控被添加到账本上的区块。客户端需要Admin权限，这样才能读取完整的区块，每产生一个区块，它都会接收到通知。区块中有交易，交易中有chaincode event，所以可以通过BlockEvent获取其他事件。
1. FilteredBlockEvent，可以用来监控简要的区块信息，当不只关心区块包含了哪些交易，交易是否成功时，它非常实用，还可以降低网络负载。它包含区块的部分信息，所以被称为filtered，信息有channel ID，区块号，交易的validation code。
1. TransactionStatusEvent，可以用来监控某个交易在当前组织的peer何时完成。可以得到交易的validation code和交易所在区块。
1. ChaincodeEvent，用来监听Chaincode发出的事件，不同的链码可以自定义自己的事件，所以这个更具有个性化。包含了交易id、区块号、链码id、事件名称，事件内容。如果想要查看事件内容，客户端所使用的账号，必须是Admin权限。

另外，订阅事件时可以指定开启和结束的区块号范围，如果开始的区块号已经产生，即区块已经写入账本，可以重放事件，更多信息可以看下面的文档。

关于Event的2篇重要文档，深深感觉Node SDK的文档，比Go SDK的文档丰富。

- [Hyperledger Fabric SDK for node.js Tutorial: How to use the channel-based event service](https://fabric-sdk-node.github.io/tutorial-channel-events.html)
- [Peer channel-based event services — hyperledger-fabricdocs master 文档](https://hyperledger-fabric-cn.readthedocs.io/zh/latest/peer_event_services.html)

## 架构

上一节的介绍能够知道有哪些Event，各有什么作用，这一节介绍SDK和Peer是如何进行事件交互的。

SDK和Peer之间是通过gRPC通信的，gRPC的[protos的定义文件](https://github.com/hyperledger/fabric/blob/release-1.4/protos/peer/events.proto)4种message：

```proto3
FilteredBlock，给FilteredBlockEvent使用
FilteredTransaction，结合下一个，给FilteredTransactionEvent使用
FilteredTransactionActions
FilteredChaincodeAction，给ChaincodeEvent使用
```

和1个Response，其中使用了oneof。

- status，指http status，成功的时候无需使用，错误的时候可以使用指明错误。
- block，给BlockEvent使用
- FilteredBlock，给另外3种事件使用

```proto3
// DeliverResponse
message DeliverResponse {
    oneof Type {
        common.Status status = 1;
        common.Block block = 2;
        FilteredBlock filtered_block = 3;
    }
}
```

以及2个gRPC通信接口:

```proto3
service Deliver {
    // deliver first requires an Envelope of type ab.DELIVER_SEEK_INFO with
    // Payload data as a marshaled orderer.SeekInfo message,
    // then a stream of block replies is received
    rpc Deliver (stream common.Envelope) returns (stream DeliverResponse) {
    }
    // deliver first requires an Envelope of type ab.DELIVER_SEEK_INFO with
    // Payload data as a marshaled orderer.SeekInfo message,
    // then a stream of **filtered** block replies is received
    rpc DeliverFiltered (stream common.Envelope) returns (stream DeliverResponse) {
    }
}
```

咦，4个Event，怎么只有2个接口？

配合下图，我们做一番讲解。


![fabric sdk go event](http://img.lessisbetter.site/2019-11-fabric-events.png)

对于Peer而言，只有2中类型的订阅：
1. BlockEvent，即完整的区块
1. FilteredBlockEvent，即不完整的区块，可以根据FilteredBlockEvent中的信息，生成FilteredTransactionEvent信息和ChainCodeEvent信息

图中深蓝色和绿色的线分别代表BlockEvent和FilteredBlockEvent相关的数据流，BlockEvent使用的是Deliver函数，FilteredBlockEvent使用的是DeliverFiltered函数。

每一个事件订阅，都是一个gRPC连接，Peer会不断的从账本读区块，然后根据区块生成事件，发送给客户端。

Go SDK中实现了一个Dispatcher，就是提供这么一个中转的功能，对上层应用提供4中类型的事件，把4种事件注册请求转换为2种，调用DeliverClient把事件订阅请求发送给Peer，又把Peer发来的2种事件，转换为应用订阅的事件响应。

Peer启动时，启动gRPC服务后，会注册好DeliverServer接收事件订阅，然后调用deliverBlocks进入循环，在新区块产生后，会生成订阅的BlockEvent或FilteredBlockEvent，利用ResponseSender把事件发送给SDK。

## event.pb.go源码

这就是根据`events.proto`生成的Go文件，负责创建gRPC通信的客户端和服务端，以及两边的消息发送。

主要关注下2个接口：

`deliverClient`实现了`DeliverClient`，已经在该源文件实现。

```go
// DeliverClient is the client API for Deliver service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://godoc.org/google.golang.org/grpc#ClientConn.NewStream.
type DeliverClient interface {
	// deliver first requires an Envelope of type ab.DELIVER_SEEK_INFO with
	// Payload data as a marshaled orderer.SeekInfo message,
	// then a stream of block replies is received
	Deliver(ctx context.Context, opts ...grpc.CallOption) (Deliver_DeliverClient, error)
	// deliver first requires an Envelope of type ab.DELIVER_SEEK_INFO with
	// Payload data as a marshaled orderer.SeekInfo message,
	// then a stream of **filtered** block replies is received
	DeliverFiltered(ctx context.Context, opts ...grpc.CallOption) (Deliver_DeliverFilteredClient, error)
}
```

`DeliverServer`是服务端的接口，需要Peer实现。

```go
// DeliverServer is the server API for Deliver service.
type DeliverServer interface {
	// deliver first requires an Envelope of type ab.DELIVER_SEEK_INFO with
	// Payload data as a marshaled orderer.SeekInfo message,
	// then a stream of block replies is received
	Deliver(Deliver_DeliverServer) error
	// deliver first requires an Envelope of type ab.DELIVER_SEEK_INFO with
	// Payload data as a marshaled orderer.SeekInfo message,
	// then a stream of **filtered** block replies is received
	DeliverFiltered(Deliver_DeliverFilteredServer) error
}
```


## Peer event源码


Peer干了这么几件事：
1. 注册gRPC服务，即注册接受客户端发来的事件订阅的函数
1. gRPC收到消息，订阅相应事件注册处理函数
1. 处理函数持续向客户端发送区块事件，直到结束

### 添加Deliver服务


`serve`是Peer启动后的运行的主函数，它会创建gRPC server，以及创建DeliverEvent server，并把它绑定到gRPC server上。



```go
// peer/node/start.go
func serve(args []string) error {
    ...
    // 创建peer的gRPC server
    peerServer, err := peer.NewPeerServer(listenAddr, serverConfig)
    if err != nil {
        logger.Fatalf("Failed to create peer server (%s)", err)
    }
    ...
    // 创建和启动基于gRPC的event deliver server
    abServer := peer.NewDeliverEventsServer(mutualTLS, policyCheckerProvider, &peer.DeliverChainManager{}, metricsProvider)
    pb.RegisterDeliverServer(peerServer.Server(), abServer)
    ...
}
```

创建DeliverEventsServer，实际是创建好处理事件订阅的handler。

```go
// core/peer/deliverevents.go
// NewDeliverEventsServer creates a peer.Deliver server to deliver block and
// filtered block events
func NewDeliverEventsServer(mutualTLS bool, policyCheckerProvider PolicyCheckerProvider, chainManager deliver.ChainManager, metricsProvider metrics.Provider) peer.DeliverServer {
	timeWindow := viper.GetDuration("peer.authentication.timewindow")
	if timeWindow == 0 {
		defaultTimeWindow := 15 * time.Minute
		logger.Warningf("`peer.authentication.timewindow` not set; defaulting to %s", defaultTimeWindow)
		timeWindow = defaultTimeWindow
	}
	metrics := deliver.NewMetrics(metricsProvider)
	return &server{
		// 创建handler
		dh:                    deliver.NewHandler(chainManager, timeWindow, mutualTLS, metrics),
		policyCheckerProvider: policyCheckerProvider,
	}
}

// NewHandler creates an implementation of the Handler interface.
func NewHandler(cm ChainManager, timeWindow time.Duration, mutualTLS bool, metrics *Metrics) *Handler {
	return &Handler{
		ChainManager:     cm,
		TimeWindow:       timeWindow,
		BindingInspector: InspectorFunc(comm.NewBindingInspector(mutualTLS, ExtractChannelHeaderCertHash)),
		Metrics:          metrics,
	}
}
```

`server`实现了`DeliverServer`接口，当gRPC接收到事件注册时，就可以调用Deliver或者FilteredDeliver被调用时，就调用server的`DeliverFiltered`或者`Deliver`函数。

```
// server holds the dependencies necessary to create a deliver server
type server struct {
	dh                    *deliver.Handler
	policyCheckerProvider PolicyCheckerProvider
}
```

### 接收事件订阅


BlockEvent的注册和事件处理主要流程如下：

```
server.Deliver -> Handler.Handle ->
deliverBlocks -> SendBlockResponse -> blockResponseSender.SendBlockResponse -> gRPC生成的server Send函数
```

FilteredBlockEvent的注册和事件处理主要流程如下：

```
server.DeliverFiltered -> Handler.Handle ->
deliverBlocks -> SendBlockResponse -> filteredBlockResponseSender.SendBlockResponseg -> RPC生成的server Send函数
```

它们2个流程是类似的，下面就以BlockEvent的流程介绍。

```go
// Deliver sends a stream of blocks to a client after commitment
func (s *server) Deliver(srv peer.Deliver_DeliverServer) (err error) {
	logger.Debugf("Starting new Deliver handler")
	defer dumpStacktraceOnPanic()
	// getting policy checker based on resources.Event_Block resource name
	deliverServer := &deliver.Server{
		PolicyChecker: s.policyCheckerProvider(resources.Event_Block),
		Receiver:      srv,
		// 创建了sender
		ResponseSender: &blockResponseSender{
			Deliver_DeliverServer: srv,
		},
	}
	return s.dh.Handle(srv.Context(), deliverServer)
}

// Handle receives incoming deliver requests.
func (h *Handler) Handle(ctx context.Context, srv *Server) error {
	addr := util.ExtractRemoteAddress(ctx)
	logger.Debugf("Starting new deliver loop for %s", addr)
	h.Metrics.StreamsOpened.Add(1)
	defer h.Metrics.StreamsClosed.Add(1)
	for {
		logger.Debugf("Attempting to read seek info message from %s", addr)
		envelope, err := srv.Recv()
		if err == io.EOF {
			logger.Debugf("Received EOF from %s, hangup", addr)
			return nil
		}
		if err != nil {
			logger.Warningf("Error reading from %s: %s", addr, err)
			return err
		}

		// 主体
		status, err := h.deliverBlocks(ctx, srv, envelope)
		if err != nil {
			return err
		}

		err = srv.SendStatusResponse(status)
		if status != cb.Status_SUCCESS {
			return err
		}
		if err != nil {
			logger.Warningf("Error sending to %s: %s", addr, err)
			return err
		}

		logger.Debugf("Waiting for new SeekInfo from %s", addr)
	}
}
```

`deliverBlocks`的主要作用就是不停的获取区块，然后调用sender发送事件，其中还包含了事件订阅信息的获取，错误处理等。

```go
func (h *Handler) deliverBlocks(ctx context.Context, srv *Server, envelope *cb.Envelope) (status cb.Status, err error) {
    ...
    for {
		...
		var block *cb.Block
		var status cb.Status

		iterCh := make(chan struct{})
		go func() {
			// 获取下一个区块，当账本Append Block时，就可以拿到要写入到账本的区块
			block, status = cursor.Next()
			close(iterCh)
		}()
		...
		// 发送区块
		if err := srv.SendBlockResponse(block); err != nil {
			logger.Warningf("[channel: %s] Error sending to %s: %s", chdr.ChannelId, addr, err)
			return cb.Status_INTERNAL_SERVER_ERROR, err
		}

		h.Metrics.BlocksSent.With(labels...).Add(1)

		// 停止判断
		if stopNum == block.Header.Number {
			break
		}
    }
    ...
}
```

`Iterator`接口用来获取区块.

```go
// Iterator is useful for a chain Reader to stream blocks as they are created
type Iterator interface {
	// Next blocks until there is a new block available, or returns an error if
	// the next block is no longer retrievable
	Next() (*cb.Block, cb.Status)
	// Close releases resources acquired by the Iterator
	Close()
}
```

Fabric有3种类型的账本：ram、json和file，它们都实现了这个接口，这里主要是为了辅助解释事件机制，我们看一个最简单的：ram的实现。

`Next()`拿到的区块是从`simpleList.SetNext()`存进去的。

```go
// Next blocks until there is a new block available, or returns an error if the
// next block is no longer retrievable
func (cu *cursor) Next() (*cb.Block, cb.Status) {
	// This only loops once, as signal reading indicates non-nil next
	// 实际只执行1次
	for {
		// 拿到区块
		next := cu.list.getNext()
		if next != nil {
			cu.list = next
			return cu.list.block, cb.Status_SUCCESS
		}
		<-cu.list.signal
	}
}

func (s *simpleList) getNext() *simpleList {
	s.lock.RLock()
	defer s.lock.RUnlock()
	return s.next
}

// 设置
func (s *simpleList) setNext(n *simpleList) {
	s.lock.Lock()
	defer s.lock.Unlock()
	s.next = n
}
```

`Append()`是账本对外提供的接口，当要把区块追加到账本时，会调用此函数，该函数会调用`setNext()`设置待追加的区块。

```go
// Append appends a new block to the ledger
func (rl *ramLedger) Append(block *cb.Block) error {
	rl.lock.Lock()
	defer rl.lock.Unlock()
	// ...
	rl.appendBlock(block)
	return nil
}

func (rl *ramLedger) appendBlock(block *cb.Block) {
	next := &simpleList{
		signal: make(chan struct{}),
		block:  block,
	}
	// 设置最新的区块
	rl.newest.setNext(next)
	// ...
}
```

### 发送事件消息


`blockResponseSender.SendBlockResponse`是BlockEvent的事件发送函数，实际就是调用gRPC生成的函数。

`blockResponseSender`是在`server.Deliver`中创建的，它实际就是`peer.Deliver_DeliverServer`。

```go
// blockResponseSender structure used to send block responses
type blockResponseSender struct {
	peer.Deliver_DeliverServer
}

// SendBlockResponse generates deliver response with block message
func (brs *blockResponseSender) SendBlockResponse(block *common.Block) error {
	response := &peer.DeliverResponse{
		Type: &peer.DeliverResponse_Block{Block: block},
	}
	return brs.Send(response)
}
```


## Go SDK源码

社区正在重构fabric-sdk-go，所以这里不着重介绍sdk的源码了，提醒几个重要的点，可能以后还有。

`Deliver`和`DeliverFiltered`被封装成了2个全局函数：


```
var (
	// Deliver creates a Deliver stream
	Deliver = func(client pb.DeliverClient) (deliverStream, error) {
		return client.Deliver(context.Background())
	}

	// DeliverFiltered creates a DeliverFiltered stream
	DeliverFiltered = func(client pb.DeliverClient) (deliverStream, error) {
		return client.DeliverFiltered(context.Background())
	}
)
```

它们会被调用，进一步封装成provider，provider会为dispatch服务：

```go
// deliverProvider is the connection provider used for connecting to the Deliver service
var deliverProvider = func(context fabcontext.Client, chConfig fab.ChannelCfg, peer fab.Peer) (api.Connection, error) {
	if peer == nil {
		return nil, errors.New("Peer is nil")
	}

	eventEndpoint, ok := peer.(api.EventEndpoint)
	if !ok {
		panic("peer is not an EventEndpoint")
	}
	return deliverconn.New(context, chConfig, deliverconn.Deliver, peer.URL(), eventEndpoint.Opts()...)
}
```


### Dispatcher

`Dispatcher`会保存BlockEvent和FilteredBlockEvent的注册，以及用2个map`txRegistrations`和`ccRegistrations`保存交易和Chaincode Event的注册，`handlers`是各种注册事件的处理函数。

```go
// Dispatcher is responsible for handling all events, including connection and registration events originating from the client,
// and events originating from the channel event service. All events are processed in a single Go routine
// in order to avoid any race conditions and to ensure that events are processed in the order in which they are received.
// This also avoids the need for synchronization.
// The lastBlockNum member MUST be first to ensure it stays 64-bit aligned on 32-bit machines.
type Dispatcher struct {
	lastBlockNum uint64 // Must be first, do not move
	params
	updateLastBlockInfoOnly    bool
	state                      int32
	eventch                    chan interface{}
	blockRegistrations         []*BlockReg
	filteredBlockRegistrations []*FilteredBlockReg
	handlers                   map[reflect.Type]Handler
	txRegistrations            map[string]*TxStatusReg
	ccRegistrations            map[string]*ChaincodeReg
}
```

### 注册事件

这是Dispatcher的事件注册函数，在它眼里，不止有4个事件：

```go
// RegisterHandler registers an event handler
func (ed *Dispatcher) RegisterHandler(t interface{}, h Handler) {
	htype := reflect.TypeOf(t)
	if _, ok := ed.handlers[htype]; !ok {
		logger.Debugf("Registering handler for %s on dispatcher %T", htype, ed)
		ed.handlers[htype] = h
	} else {
		logger.Debugf("Cannot register handler %s on dispatcher %T since it's already registered", htype, ed)
	}
}
```

注册各注册事件的处理函数：

```go
// RegisterHandlers registers all of the handlers by event type
func (ed *Dispatcher) RegisterHandlers() {
	ed.RegisterHandler(&RegisterChaincodeEvent{}, ed.handleRegisterCCEvent)
	ed.RegisterHandler(&RegisterTxStatusEvent{}, ed.handleRegisterTxStatusEvent)
	ed.RegisterHandler(&RegisterBlockEvent{}, ed.handleRegisterBlockEvent)
	ed.RegisterHandler(&RegisterFilteredBlockEvent{}, ed.handleRegisterFilteredBlockEvent)
	ed.RegisterHandler(&UnregisterEvent{}, ed.handleUnregisterEvent)
	ed.RegisterHandler(&StopEvent{}, ed.HandleStopEvent)
	ed.RegisterHandler(&TransferEvent{}, ed.HandleTransferEvent)
	ed.RegisterHandler(&StopAndTransferEvent{}, ed.HandleStopAndTransferEvent)
	ed.RegisterHandler(&RegistrationInfoEvent{}, ed.handleRegistrationInfoEvent)

	// The following events are used for testing only
	ed.RegisterHandler(&fab.BlockEvent{}, ed.handleBlockEvent)
	ed.RegisterHandler(&fab.FilteredBlockEvent{}, ed.handleFilteredBlockEvent)
}
```


### 接收Peer事件

`handleEvent`用来处理来自Peer的事件，不同的类型调用不同的handler。

```go
func (ed *Dispatcher) handleEvent(e esdispatcher.Event) {
	delevent := e.(*connection.Event)
	evt := delevent.Event.(*pb.DeliverResponse)
	switch response := evt.Type.(type) {
	case *pb.DeliverResponse_Status:
		ed.handleDeliverResponseStatus(response)
	case *pb.DeliverResponse_Block:
		ed.HandleBlock(response.Block, delevent.SourceURL)
	case *pb.DeliverResponse_FilteredBlock:
		ed.HandleFilteredBlock(response.FilteredBlock, delevent.SourceURL)
	default:
		logger.Errorf("handler not found for deliver response type %T", response)
	}
}
```


`HandleBlock`把Event封装是BlockEvent退给应用。可以看到BlockEvent也会发布FilteredBlockEvent。

```go
// HandleBlock handles a block event
func (ed *Dispatcher) HandleBlock(block *cb.Block, sourceURL string) {
	logger.Debugf("Handling block event - Block #%d", block.Header.Number)

	if err := ed.updateLastBlockNum(block.Header.Number); err != nil {
		logger.Error(err.Error())
		return
	}

	if ed.updateLastBlockInfoOnly {
		ed.updateLastBlockInfoOnly = false
		return
	}

	logger.Debug("Publishing block event...")
	ed.publishBlockEvents(block, sourceURL)
	ed.publishFilteredBlockEvents(toFilteredBlock(block), sourceURL)
}

func (ed *Dispatcher) publishBlockEvents(block *cb.Block, sourceURL string) {
	for _, reg := range ed.blockRegistrations {
		if !reg.Filter(block) {
			logger.Debugf("Not sending block event for block #%d since it was filtered out.", block.Header.Number)
			continue
		}

		if ed.eventConsumerTimeout < 0 {
			select {
			case reg.Eventch <- NewBlockEvent(block, sourceURL):
			default:
				logger.Warn("Unable to send to block event channel.")
			}
		} else if ed.eventConsumerTimeout == 0 {
			reg.Eventch <- NewBlockEvent(block, sourceURL)
		} else {
			select {
			case reg.Eventch <- NewBlockEvent(block, sourceURL):
			case <-time.After(ed.eventConsumerTimeout):
				logger.Warn("Timed out sending block event.")
			}
		}
	}
}
```

FilteredBlockEvent能解析出TransactionEvent和ChaincodeEvent：

```go
func (ed *Dispatcher) publishFilteredBlockEvents(fblock *pb.FilteredBlock, sourceURL string) {
	if fblock == nil {
		logger.Warn("Filtered block is nil. Event will not be published")
		return
	}

	logger.Debugf("Publishing filtered block event: %#v", fblock)

	checkFilteredBlockRegistrations(ed, fblock, sourceURL)

	for _, tx := range fblock.FilteredTransactions {
		// 发布交易订阅
		ed.publishTxStatusEvents(tx, fblock.Number, sourceURL)

		// Only send a chaincode event if the transaction has committed
		if tx.TxValidationCode == pb.TxValidationCode_VALID {
			txActions := tx.GetTransactionActions()
			if txActions == nil {
				continue
			}
			if len(txActions.ChaincodeActions) == 0 {
				logger.Debugf("No chaincode action found for TxID[%s], block[%d], source URL[%s]", tx.Txid, fblock.Number, sourceURL)
			}
			for _, action := range txActions.ChaincodeActions {
				if action.ChaincodeEvent != nil {
					// 发布chaincode event订阅
					ed.publishCCEvents(action.ChaincodeEvent, fblock.Number, sourceURL)
				}
			}
		} else {
			logger.Debugf("Cannot publish CCEvents for block[%d] and source URL[%s] since Tx Validation Code[%d] is not valid", fblock.Number, sourceURL, tx.TxValidationCode)
		}
	}
}

func (ed *Dispatcher) publishTxStatusEvents(tx *pb.FilteredTransaction, blockNum uint64, sourceURL string) {
	logger.Debugf("Publishing Tx Status event for TxID [%s]...", tx.Txid)
	if reg, ok := ed.txRegistrations[tx.Txid]; ok {
		logger.Debugf("Sending Tx Status event for TxID [%s] to registrant...", tx.Txid)

		if ed.eventConsumerTimeout < 0 {
			select {
			case reg.Eventch <- NewTxStatusEvent(tx.Txid, tx.TxValidationCode, blockNum, sourceURL):
			default:
				logger.Warn("Unable to send to Tx Status event channel.")
			}
		} else if ed.eventConsumerTimeout == 0 {
			reg.Eventch <- NewTxStatusEvent(tx.Txid, tx.TxValidationCode, blockNum, sourceURL)
		} else {
			select {
			case reg.Eventch <- NewTxStatusEvent(tx.Txid, tx.TxValidationCode, blockNum, sourceURL):
			case <-time.After(ed.eventConsumerTimeout):
				logger.Warn("Timed out sending Tx Status event.")
			}
		}
	}
}

func (ed *Dispatcher) publishCCEvents(ccEvent *pb.ChaincodeEvent, blockNum uint64, sourceURL string) {
	for _, reg := range ed.ccRegistrations {
		logger.Debugf("Matching CCEvent[%s,%s] against Reg[%s,%s] ...", ccEvent.ChaincodeId, ccEvent.EventName, reg.ChaincodeID, reg.EventFilter)
		if reg.ChaincodeID == ccEvent.ChaincodeId && reg.EventRegExp.MatchString(ccEvent.EventName) {
			logger.Debugf("... matched CCEvent[%s,%s] against Reg[%s,%s]", ccEvent.ChaincodeId, ccEvent.EventName, reg.ChaincodeID, reg.EventFilter)

			if ed.eventConsumerTimeout < 0 {
				select {
				case reg.Eventch <- NewChaincodeEvent(ccEvent.ChaincodeId, ccEvent.EventName, ccEvent.TxId, ccEvent.Payload, blockNum, sourceURL):
				default:
					logger.Warn("Unable to send to CC event channel.")
				}
			} else if ed.eventConsumerTimeout == 0 {
				reg.Eventch <- NewChaincodeEvent(ccEvent.ChaincodeId, ccEvent.EventName, ccEvent.TxId, ccEvent.Payload, blockNum, sourceURL)
			} else {
				select {
				case reg.Eventch <- NewChaincodeEvent(ccEvent.ChaincodeId, ccEvent.EventName, ccEvent.TxId, ccEvent.Payload, blockNum, sourceURL):
				case <-time.After(ed.eventConsumerTimeout):
					logger.Warn("Timed out sending CC event.")
				}
			}
		}
	}
}
```


## 总结

本文介绍了：
1. Peer支持的2类Even，
1. Peer是如何支持事件订阅，和发送事件的，
1. SDK支持的4类Event，这4类Event和Peer的2类Event的关系
1. SDK和Peer之间的gRPC通信

更多SDK事件的使用，请参考[文档](https://godoc.org/github.com/hyperledger/fabric-sdk-go/pkg/client/event#New)。

Fabric事件介绍的[官方文档(https://stone-fabric.readthedocs.io/zh/latest/peer_event_services.html)。

Fabric在examples中还提供了一个[eventclient](https://github.com/hyperledger/fabric/tree/release-1.4/examples/events/eventsclient)样例，看这个样例更有助于理解Fabric event的原理，以及是如何交互的。
