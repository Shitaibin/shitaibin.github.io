---
title: 使用fabric-sdk-go操作链码
date: 2019-09-02 14:55:16
tags: ['区块链','Fabric']
---


## 前言

本文把与fabric网络交互的baas、应用程序、客户端统称成为客户端，它们可以使用sdk和fabric网络进行交互，sdk调用grpc可以与指定的peer和orderer进行通信，本文的目的是在BYFN搭建的fabric网络的基础之上，展示如何使用fabric-sdk-go操作链码。

![fabric sdk](http://img.lessisbetter.site/2019-09-fabric-sdk.png)

## fabric-sdk-go项目简介

[fabric-sdk-go](https://github.com/hyperledger/fabric-sdk-go)是Fabric官方的Go语言SDK，它的目录结构如下：

![fabric sdk go](http://img.lessisbetter.site/2019-09-fabric-sd-go.png)


有2个目录需要注意一下，internal和third_party，它们两个包含了sdk依赖的一些代码，来自于fabric、fabric-ca，当使用到fabric的一些类型时，应当使用以下的方式，而不是直接导入fabric或者fabric-ca：

```go
import "github.com/hyperledger/fabric-sdk-go/third_party/github.com/hyperledger/fabric/xxx"
```

pkg目录是sdk的主要实现，[doc 文档](https://godoc.org/github.com/hyperledger/fabric-sdk-go)介绍了不同目录所提供的功能，以及给出了接口调用样例：

- pkg/fabsdk：主package，主要用来生成fabsdk以及各种其他pkg使用的option context。
- pkg/client/channel：主要用来调用、查询链码，或者注册链码事件。
- pkg/client/resmgmt：主要用来fabric网络的管理，比如创建、加入通道，安装、实例化和升级链码。
- pkg/client/event:配合channel模块来进行链码事件注册和过滤。
- pkg/client/ledger：主要用来账本的查询，查询区块、交易、配置等。
- pkg/client/msp：主要用来管理fabric的成员关系。

> 想用好fabric-go-sdk，建议仔细看看[doc 文档](https://godoc.org/github.com/hyperledger/fabric-sdk-go)。


## 使用SDK步骤

1. 为client编写配置文件config.yaml
2. 为client创建fabric sdk实例fabsdk
3. 为client创建resource manage client，**简称RC**，RC用来进行管理操作的client，比如通道的创建，链码的安装、实例化和升级等
4. 为client创建channel client，**简称CC**，CC用来链码的调用、查询以及链码事件的注册和取消注册

## SDK配置文件config.yaml

client使用sdk与fabric网络交互，需要告诉sdk两类信息：

1. 我是谁：即当前client的信息，包含所属组织、密钥和证书文件的路径等，这是每个client专用的信息。
2. 对方是谁：即fabric网络结构的信息，channel、org、orderer和peer等的怎么组合起当前fabric网络的，这些结构信息应当与`configytx.yaml`中是一致的。这是通用配置，每个客户端都可以拿来使用。另外，这部分信息并不需要是完整fabric网络信息，如果当前client只和部分节点交互，那配置文件中只需要包含所使用到的网络信息。

![fabric sdk config](http://img.lessisbetter.site/2019-09-fabric-sdk-config.yaml.png)

这里提供一个适合[BFYN](https://github.com/hyperledger/fabric-samples/tree/release-1.4/first-network)的精简配置文件[fabric-sdk-go-sample/config.yaml](https://github.com/Shitaibin/fabric-sdk-go-sample/blob/master/config/org1sdk-config.yaml)。

## 使用go mod管理依赖

fabric-sdk-go目前本身使用go modules管理依赖，从[go.mod](https://github.com/hyperledger/fabric-sdk-go/blob/master/go.mod)可知，依赖的一些包指定了具体的版本，如果项目依赖的版本和sdk依赖的版本不同，会产生编译问题。

建议项目也使用go moudles管理依赖，然后相同的软件包可以使用相同的版本，可以这样操作：

1. go mod init初始化好项目的go.mod文件。
2. 编写代码，完成后运行go mod run，会自动下载依赖的项目，但版本可能与fabric-sdk-go中的依赖版本不同，编译存在问题。
3. 把[go.mod](https://github.com/hyperledger/fabric-sdk-go/blob/master/go.mod)中的内容复制到项目的go.mod中，然后保存，go mod会自动合并相同的依赖，运行go mod tidy，会自动添加新的依赖或删除不需要的依赖。

项目的go mod样例可以参考[securekey/fabric-examples ... /go.mod](https://github.com/securekey/fabric-examples/blob/master/fabric-cli/cmd/fabric-cli/go.mod)，[shitaibin/fabric-sdk-go-sample/go.mod](https://github.com/Shitaibin/fabric-sdk-go-sample/blob/master/go.mod)。

## 创建Client

### 利用config.yaml创建fabsdk

通过`config.FromFile`解析配置文件，然后通过`fabsdk.New`创建sdk实例。

```go
import "github.com/hyperledger/fabric-sdk-go/pkg/core/config"
import "github.com/hyperledger/fabric-sdk-go/pkg/fabsdk"

sdk, err := fabsdk.New(config.FromFile(c.ConfigPath))
if err != nil {
  log.Panicf("failed to create fabric sdk: %s", err)
}
```

### 创建RC

管理员账号才能进行fabric网络的管理操作，所以创建rc一定要使用管理员账号。

通过`fabsdk.WithOrg("Org1")`和`fabsdk.WithUser("Admin")`指定Org1的Admin账户，使用`sdk.Context`创建**clientProvider**，然后通过`resmgmt.New`创建rc。

```go
import 	"github.com/hyperledger/fabric-sdk-go/pkg/client/resmgmt"

rcp := sdk.Context(fabsdk.WithUser("Admin"), fabsdk.WithOrg("Org1"))
rc, err := resmgmt.New(rcp)
if err != nil {
  log.Panicf("failed to create resource client: %s", err)
}
```

### 创建CC

创建cc使用用户账号，进行链码的调用和查询，使用`sdk.ChannelContext`创建**channelProvider**，需要指定channelID和用户User1，然后通过`channel.New`创建cc，此cc就是调用channelID对应channel上链码的channel client。

```go
import 	"github.com/hyperledger/fabric-sdk-go/pkg/client/channel"

ccp := sdk.ChannelContext(ChannelID, fabsdk.WithUser("User1"))
cc, err := channel.New(ccp)
if err != nil {
  log.Panicf("failed to create channel client: %s", err)
}
```

## 管理操作

### 安装链码

安装链码使用`rc.InstallCC`接口，需要指定`resmgmt.InstallCCRequest`以及在哪些peers上面安装。`resmgmt.InstallCCRequest`指明了链码ID、链码路径、链码版本以及打包后的链码。

打包链码需要使用到链码路径`CCPath`和`GoPath`，`GoPath`即本机的`$GOPATH`，`CCPath`是相对于`GoPath`的**相对路径**，如果路径设置不对，会造成sdk找不到链码。

```go
// pack the chaincode
ccPkg, err := gopackager.NewCCPackage("github.com/hyperledger/fabric-samples/chaincode/chaincode_example02/go/", "/Users/shitaibin/go")
if err != nil {
  return errors.WithMessage(err, "pack chaincode error")
}

// new request of installing chaincode
req := resmgmt.InstallCCRequest{
  Name:    c.CCID,
  Path:    c.CCPath,
  Version: v,
  Package: ccPkg,
}

reqPeers := resmgmt.WithTargetEndpoints("peer0.org1.example.com")
resps, err := rc.InstallCC(req, reqPeers)
if err != nil {
  return errors.WithMessage(err, "installCC error")
}
```

### 实例化链码

实例化链码需要使用`rc.InstantiateCC`接口，需要通过ChannelID、`resmgmt.InstantiateCCRequest`和peers，指明在哪个channel上实例化链码，请求包含了链码的ID、路径、版本，以及初始化参数和背书策略，背书策略可以通过`cauthdsl.FromString`生成。

```go
// endorser policy
org1OrOrg2 := "OR('Org1MSP.member','Org2MSP.member')"
ccPolicy, err := cauthdsl.FromString(org1OrOrg2)
if err != nil {
  return errors.WithMessage(err, "gen policy from string error")
}

// new request
args := packArgs([]string{"init", "a", "100", "b", "200"})
req := resmgmt.InstantiateCCRequest{
  Name:    c.CCID,
  Path:    c.CCPath,
  Version: v,
  Args:    args,
  Policy:  ccPolicy,
}

// send request and handle response
reqPeers := resmgmt.WithTargetEndpoints("peer0.org1.example.com")
resp, err := rc.InstantiateCC(ChannelID, req, reqPeers)
if err != nil {
  return errors.WithMessage(err, "instantiate chaincode error")
}
```

### 升级链码

升级链码和实例化链码是非常相似的，不同点只在请求是`resmgmt.UpgradeCCRequest`，调用的接口是`rc.UpgradeCC`。

```go
// endorser policy
org1AndOrg2 := "AND('Org1MSP.member','Org2MSP.member')"
ccPolicy, err := c.genPolicy(org1AndOrg2)
if err != nil {
  return errors.WithMessage(err, "gen policy from string error")
}

// new request
args := packArgs([]string{"init", "a", "100", "b", "200"})
req := resmgmt.UpgradeCCRequest{
  Name:    c.CCID,
  Path:    c.CCPath,
  Version: v,
  Args:    args,
  Policy:  ccPolicy,
}

// send request and handle response
reqPeers := resmgmt.WithTargetEndpoints("peer0.org1.example.com")
resp, err := rc.UpgradeCC(ChannelID, req, reqPeers)
if err != nil {
  return errors.WithMessage(err, "instantiate chaincode error")
}
```

## 查询操作

### 调用链码

调用链码使用`cc.Execute`接口，使用入参`channel.Request`和peers指明要让哪些peer上执行链码，进行背书。`channel.Request`指明了要调用的链码，以及链码内要Invoke的函数args，args是序列化的结果，序列化是自定义的，只要链码能够按相同的规则进行反序列化即可。

```go
// new channel request for invoke
args := packArgs([]string{"a", "b", "10"})
req := channel.Request{
  ChaincodeID: c.CCID,
  Fcn:         "invoke",
  Args:        args,
}

// send request and handle response
// peers is needed
reqPeers := channel.WithTargetEndpoints("peer0.org1.example.com")
resp, err := cc.Execute(req, reqPeers)
if err != nil {
  return errors.WithMessage(err, "invoke chaincode error")
}
log.Printf("invoke chaincode tx: %s", resp.TransactionID)
```

### 查询链码

查询和调用链码是非常相似的，使用相同的`channel.Request`，指明了Invoke链码中的`query`函数，然后调用`cc.Query`进行查询操作，这样节点不会对请求进行背书。

```go
// new channel request for query
req := channel.Request{
  ChaincodeID: c.CCID,
  Fcn:         "query",
  Args:        packArgs([]string{keys}),
}

// send request and handle response
reqPeers := channel.WithTargetEndpoints(peer)
resp, err := cc.Query(req, reqPeers)
if err != nil {
  return errors.WithMessage(err, "query chaincode error")
}

log.Printf("query chaincode tx: %s", resp.TransactionID)
log.Printf("result: %v", string(resp.Payload))
```

## 示例项目

本文的基础是创建了一个结合fabric byfn的示例项目，在byfn的基础之上对链码进行安装、实例化、升级，调用和查询等操作，项目的使用可见项目[README文档](https://github.com/Shitaibin/fabric-sdk-go-sample)，项目地址：https://github.com/Shitaibin/fabric-sdk-go-sample ，项目样例执行后，可见新部署和升级成功的链码容器，操作日志可见项目。

![byfn-sdk](http://img.lessisbetter.site/2019-09-byfn-sdk.png)