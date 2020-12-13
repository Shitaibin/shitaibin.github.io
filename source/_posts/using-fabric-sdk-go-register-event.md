---
title: 使用fabric-sdk-go订阅Fabric事件
date: 2019-11-13 20:43:13
tags: ['Fabric', '区块链']
---


[使用fabric-sdk-go操作链码](http://lessisbetter.site/2019/09/02/fabric-sdk-go-chaincode/)，介绍了使用官方Go SDK，安装、实例化和升级链码，调用和查询链码，本文介绍使用fabric-sdk-go订阅事件。

## 事件介绍

本质上就3种事件：
- BlockEvent：获取区块信息
- TransactionEvent：获取交易信息
- ChainCodeEvnet：链码中**自定义的**链码事件

但每种事件都有2 种类型：
- **Filtered**：事件订阅时默认的类型，获取的**信息“不全”**，不同的事件缺失的数据不同，比如链码事件，如果是Filtered的，其响应字段中的Payload是空的，也就是不知道链码事件携带的数据。这种方式能够降低fabric网络和SDK之间的流量，当Filtered后的字段信息就足够时，这种方式非常适合。关于Filtered的更多信息，这篇文章 [Fabric 1.4源码解读 3：Event原理解读](http://lessisbetter.site/2019/09/20/fabric-event-source/) 非常有帮助。
- **非Filtered** ：可以获取**完整的**区块、交易、链码事件**信息**，这种方式在SDK想获取更多信息时，是非常必要的。

4 个注册事件的接口1个取消注册的接口如下：

|          接口名称          |         描述          |                            参数值                            |                         返回值                          |
| :------------------------: | :-------------------: | :----------------------------------------------------------: | :-----------------------------------------------------: |
|     RegisterBlockEvent     |      注册块事件       |                  filter ...fab.BlockFilter                   |     fab.Registration, <-chan *fab.BlockEvent, error     |
| RegisterFilteredBlockEvent |    注册过滤块事件     |                              无                              | fab.Registration, <-chan *fab.FilteredBlockEvent, error |
|   RegisterTxStatusEvent    |   注册交易状态事件    |                         txID string                          |   fab.Registration, <-chan *fab.TxStatusEvent, error    |
|   RegisterChaincodeEvent   |     注册链码事件      |                   ccID, eventFilter string                   |      fab.Registration, <-chan *fab.CCEvent, error       |
|   Unregister               | 取消事件订阅          |               fab.Registration                               | 无                                                      |

注册会得到管理可以管理订阅的Registration、接收事件的通道，以及可能注册时发生的错误，关于每个接口的具体介绍、使用，可以参考官方的[Event文档](https://godoc.org/github.com/hyperledger/fabric-sdk-go/pkg/client/event)，其中包含了样例代码，如果想看真实的样例代码，可以参考[示例项目](#示例项目)。

## Option介绍

注册事件需要使用`EventClient`，创建EventClient时可以指定一些选项，这些选项其实就是事件订阅的选项。

有3个Option:
- func WithBlockEvents() ClientOption
    
    指定了此选项，事件就是**非“filtered”**，fabric会向调用SDK客户端发送完整的区块，可以获得订阅事件完整的信息。

- func WithSeekType(seek seek.Type) ClientOption

    使用此选项可以**指定从哪个区块高度获取事件**。`seek.Type`有`Oldest`、`Newest`和`FromBlock` 3种取值，分别代表从第1个区块、最后一个区块和指定区块号开始获取事件，`FromBlock`需要结合`WithBlockNum`使用。So，可以通过这个选项**获取历史事件**。

- func WithBlockNum(from uint64) ClientOption

    指定区块高度，只有`WithSeekType(FromBlock)`时才生效。

## 链码事件多说几句

### 链码如何发链码事件

`ChaincodeStubInterface`有`SetEvent`的方法，入参分别为事件名称和事件锁携带的信息payload。

```go
// ChaincodeStubInterface is used by deployable chaincode apps to access and
// modify their ledgers
type ChaincodeStubInterface interface {
    // SetEvent allows the chaincode to set an event on the response to the
    // proposal to be included as part of a transaction. The event will be
    // available within the transaction in the committed block regardless of the
    // validity of the transaction.
    SetEvent(name string, payload []byte) error
}
```
### 通过ChannelClient订阅链码事件介绍

SDK的channel client也有订阅链码事件的接口：[channel.Client.RegisterChaincodeEvent()](https://godoc.org/github.com/hyperledger/fabric-sdk-go/pkg/client/channel#Client.RegisterChaincodeEvent)，它的定义和event client提供的接口完全一样，但功能上有所差别。

channel client没有指定 `WithBlockEvents`，所以这是**Filtered的事件链码**，获取的事件链码中，其Payload为空。

## 示例项目

示例项目[fabric-sdk-go-sample](https://github.com/Shitaibin/fabric-sdk-go-sample/tree/master/samples/event)是结合Fabric的BYFN展示如何使用fabric-sdk-go的项目，它的Event样例部分，介绍了如何使用以上接口订阅Fabric事件，具体请参加该部分[README](https://github.com/Shitaibin/fabric-sdk-go-sample/blob/master/samples/event/README.md)。