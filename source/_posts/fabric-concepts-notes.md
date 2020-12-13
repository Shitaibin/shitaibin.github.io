---
title: 快速入门Fabric核心概念和框架
date: 2019-07-17 18:54:56
tags: ['Fabric', '区块链']
---

## 声明

这是一篇信息整合的文章，80%的内容来自Fabric官方文档和网络文章，在此基础上整理和修改，剩下20%为操作记录。

### 官方文档资料链接

- https://hyperledger-fabric.readthedocs.io/en/release-1.4/glossary.html
  Fabric术语表，所有概念都能在这找到，建议详读几遍，有疑问时也可以随时来查，会有新的理解。

- https://hyperledger-fabric.readthedocs.io/en/release-1.4/Fabric-FAQ.html

  这篇FAQ，也会解决很多疑问。

**剩下的官方文档链接都加入到了下面的笔记中**。


### 网络文章

[天山老妖S：HyperLeger Fabric SDK开发系列文章](https://blog.51cto.com/9291927/category29.html)

[陶辉：区块链开源实现hyperledger fabric架构详解](<http://www.taohui.pub/2018/05/26/%e5%8c%ba%e5%9d%97%e9%93%be%e5%bc%80%e6%ba%90%e5%ae%9e%e7%8e%b0hyperledger-fabric%e6%9e%b6%e6%9e%84%e8%af%a6%e8%a7%a3/>)

[Hyperledger Fabric 开发系列文章](https://shanma.pro/tutorial/hyperledger/16632.html)


## 笔记摘录

### 架构

![HyperLeger Fabric架构](https://lessisbetter.site/images/2019-07-fabric-arch.png)

 Fabric网络是通过组织（organization）来划分的，每个组织内都包含承担不同功能的Peer 节点，每个Peer节点又可以担任多种角色。**所有的组织共用一个统一的Orderer排序服务集群**。基于Hyperledger Fabric区块链网络的设计时需要考虑组织之间的业务关系以及内部每个模块之间的联系，统一进行规划。

![](https://lessisbetter.site/images/2019-07-fabric-network.png)

每个组织通常拥有自己的客户端、Peer节点和CA节点，并且可以根据需要创建一个或多个不同的类型节点。Orderer节点不属于某个组织的实体，属于组织共同维护的节点。

![](https://lessisbetter.site/images/2019-07-fabirc-org.png)


### 排序节点

orderer负责排序和打包区块。排序服务节点只是决定交易处理的顺序，并不对交易的合法性进行校验，也无需去管之前的交易是否合法，也不负责维护账本信息，只有记账节点才有账本写入权限。peer验证交易后会给交易打上交易是否合法。

排序服务节点接收包含背书签名的交易，对未打包的交易进行排序生成区块，广播给Peer节点中的主节点。排序服务提供的是原子广播，保证同一个链上的节点接收到相同的消息，并且有相同的逻辑顺序。排序服务独立于Peer进程存在并且以先来先服务的方式对Fabric网络上的所有通道进行排序交易。

Tx排序的依据是什么？根据每个通道按时间顺序调用，创建每个通道的交易区块。

出块的依据是什么？交易数、时间？都可以，具体见[orderer排序交易](#orderer排序交易)。

### peer节点角色

peer文档：https://hyperledger-fabric.readthedocs.io/en/release-1.4/peers/peers.html

peer节点负责背书和验证交易，以及Org之间的通信。

每个Org可以有多个Peer，每个Peer节点都是记账节点，并且可担任多种角色：

- Endorser Peer（背书节点）
- Leading Peer（主节点）
- Committer Peer（记账节点）
- Anchor Peer（锚节点）

#### 背书节点(Endorser Peer)

部分Peer节点会执行交易并对结果进行签名背书。背书节点是动态的角色，是与具体链码绑定的，由链码的背书策略指定。

只有在应用程序向节点发起交易背书请求时才成为背书节点，其它时候是普通的记账节点，只负责验证交易并记账。

#### 主节点（Leading Peer）

主节点负责和Orderer排序服务节点通信，从排序服务节点处获取最新的区块，并把区块分发到本channel内同组织的其他节点。可以使用配置文件强制设置，也可以选举产生。

> 注意：主节点不是指Raft中的leader，是指org中的主节点(leading peer)。

#### 记账节点（Committer Peer）

负责验证区块里的交易，然后将区块提交（写入/追加）到其通道账本的副本。记账节点还将每个块中的每个交易标记为**有效或无效**，通过验证的为有效，否则为无效。

#### 锚节点（Anchor Peer）

在一个通道上可以被所有其它Peer节点发现的Peer节点，通道上的每个组织都有一个或多个锚节点，多个锚节点可以用来防止单点故障，通过锚节点实现不同组织的Peer节点发现通道上的所有组织的锚节点。

举个例子，peer0.org1是org1的锚节点，它连接peer0.org2时，如果peer0.org2知道org3的锚节点peer0.org3，那么会告诉peer0.org1，org3的锚节点是peer0.org3，以后peer0.org1就可以直接和peer0.org3通信了。

### 客户端

2种：1. CLI，2. SDK.

#### SDK

Fabric提供了三种语言版本的SDK，分别如下：
1. Fabric Nodejs SDK
1. Fabric Java SDK
1. Fabric Go SDK

Fabric区块链应用可以通过SDK访问Fabric区块链网络中的多种资源，包括账本、交易、链码、事件、权限管理等。应用程序代表用户与Fabric区块链网络进行交互，Fabric SDK API提供了如下功能：
1. 创建通道
1. 将peer节点加入通道
1. 在peer节点安装链码
1. 在通道实例化链码
1. 通过链码调用交易
1. 查询交易或区块的账本


### 链码

链码即智能合约，链码分系统链码和用户链码，在没有特殊强调的时候，链码就是指用户链码。

链码操作包含3个基本操作：安装（install）、实例化（instantiation）和调用（Invoke），以及其他操作比如打包、签名。

用户链码被编译成一个独立的应用程序，运行于隔离的Docker容器中，在链码部署的时候会自动生成链码的Docker镜像，链码容器通过gRPC协议与相应的Peer节点进行交互，以操作分布式账本中的数据。

一个channel内链码只需实例化1次，所有运行链码的节点都需要安装该链码，如果只需要验证交易，并不需要安装链码，因为实例化后，可以通过gRPC通信与链码容器交互验证链码。

#### 背书策略（Endorser Policy）

**背书策略是背书节点如何决策交易是否合法的条件**。链码实例化时可指定背书策略，当记账节点接收到交易时，会获知相关链码信息，然后检查链码的背书策略，判断交易是否满足背书策略，若满足则标注交易为合法。

背书策略可分为主体Principal(P)和阈值Threshold(T)两部分，具体如下：
- Principal指定由哪些成员进行背书。
- Threshold接受两个输入，分别为阈值t和若干个P的集合n，只要交易中包含了n中t个成员的背书则认为交易合法。

背书策略可以指定某几个组织内的任意成员身份进行背书，或者要求至少有一个管理员身份进行背书等等。
- T(1, ‘A’, ‘B’) 则需要A，B中任意成员背书。
- T(1, ‘A’, T(2, ‘B’, ‘C’))则需要A成员背书或B，C成员同时背书。

目前客户端已经实现对背书策略的支持，可以通过-P来指定背书策略，结合AND、OR来组合成员，完成成员身份（admin、member）的集合。

`-P OR ( 'Org1.admin' , AND ('Org2.member' , 'Org3.member') )`

> 可以把OR、AND理解为函数，函数内为参数。

上述背书策略指定要么Org1的admin进行背书，或者Org2和Org3的成员同时进行背书，才满足背书策略。

链接：https://hyperledger-fabric.readthedocs.io/en/release-1.4/glossary.html#endorsement-policy

#### 系统链码

系统链码与用户链码有相同的编程模型，但**系统链码运行在Peer节点，用户链码则在隔离的容器中运行。因此，系统链码内置为Peer节点的可执行文件中，不遵循用户链码的生命周期，安装、实例化、升级不适用于系统链码**。

系统链码用于减少Peer节点与用户链码进行gRPC通信的开销，同时权衡管理的灵活性。系统链码只能通过Peer节点的二进制文件升级，必须通过一组固定的参数进行注册，但**不具有背书策略**。

Hyperledger Fabric系统链码实现了一系列系统功能，以便系统集成人员能够根据需求对其进行修改与替换。

常见系统链码如下：
- 生命周期系统链码（LSCC ）：负责对用户链码的生命周期进行管理。
- 配置系统链码（CSCC）：处理在Peer节点上的通道配置。
- 查询系统链码（QSCC）：提供账本的查询API，例如获取区块以及交易。
- 背书系统链码（ESCC）：背书过程的管理和配置。
- 验证系统链码（VSCC）：处理交易验证，包括检查背书策略以及多进程并发控制。

**这样容易记：一共5个SCC，前2个与配置相关，后3个与操作相关，配置有生命周期和配置，操作有背书、验证和查询**。

在修改或者替换系统链码（LSCC、ESCC、VSCC）时必须注意，因为系统链码在主交易执行的路径中。VSCC在将区块提交至账本前，所有在通道的Peer节点会计算相同的验证以避免账本分歧（不确定性）。如果VSCC被改变或者替换，需要特别小心。

#### 生命周期

通过install安装链码，通过instantiate实例化链码，然后可以通过invoke、query调用链码和查询链码。
如果需要升级链码，则需要先install安装新版本的链码，通过upgrade升级链码。在install安装链码前，可以通过package打包并签名生成打包文件，然后再通过install安装。

![](https://lessisbetter.site/images/2019-07-fabric-chaincode-lifecycle.png)

#### 链码管理

`peer chaincode -h`可以列出链码的几种操作：

```
install     Package the specified chaincode into a deployment spec and save it on the peer's path.
instantiate Deploy the specified chaincode to the network.
invoke      Invoke the specified chaincode.
list        Get the instantiated chaincodes on a channel or installed chaincodes on a peer.
package     Package the specified chaincode into a deployment spec.
query       Query using the specified chaincode.
signpackage Sign the specified chaincode package
upgrade     Upgrade chaincode.
```

- 安装：把chaincode打包成部署规格，并且保存到peer的某个路径。

- 实例化：部署chaincode到网络。
- 调用：调用chaincode。
- list：列出某个通道上已经实例化的chaincode或已安装到peer上的chaincode。
- 打包：把chaincode打包成部署规格。
- 查询：使用chaincode查询，即查询该查询该chaincode上的信息。
- signpackage：对打包的chaincode签名。
- 升级：升级已实例化的chaincode。

可以看到安装chaincode实际已经包含了打包的过程。

#### 打包链码

链码包由三个部分组成：

1. **由ChaincodeDeploymentSpec（CDS）格式定义的链码**。CDS根据代码及其它属性（如名称与版本）定义链码包；
1. **一个可选的实例化策略，能够被用作背书的策略进行描述**；
1. 拥有链码的实体的一组签名。

其中，链码的签名主要目的如下：

1. 建立链码的所有权；
1. 允许验证链码包中的内容；
1. 允许检测链码包是否被篡改。

通道上的链码的实例化交易的创建者能够被链码的实例化策略验证。

链码打包的方法由两种，一种是打包被多个所有者所拥有的链码，需要初始化创建一个被签名的链码包（SignedCDS），然后将其按顺序的传递给其它所有者进行签名；一种是打包单个所有者持有的链码。

创建一个被签名的链码包的命令如下：

```
peer chaincode package -n sacc -p chaincodedev/chaincode/sacc -v 0 -s -S -i "AND('OrgA.admin')" ccpack.out
```

- `-s`选项创建一个能被多个所有者签名的链码包，而不是简单的创建一个原始的CDS。一旦-s被指定，如果其它所有者想要签名CDS，则-S选项必须被指定。否则，将会创建一个SignedCDS，除CDS外仅仅包括实例化策略。
- `-S`选项使用被在core.yaml文件中定义的localMspid属性的值标识的MSP对链码包进行签名。
- `-S`选项是可选的。如果创建了一个没有签名的链码包，不能被其它所有者使用signpackage命令进行签名。
- `-i`选项是可选的，允许为链码指定实例化策略。实例化策略与背书策略有相同的格式，指定哪些身份能够实例化链码。本例中仅OrgA的admin能够实例化链码。如果没有实例化策略被指定，将会使用默认的策略，仅允许拥有Peer的MSP的管理员身份实例化链码。

#### 签名链码

在创建阶段就被签名的链码包能够交给其它所有者进行检查与签名，支持带外对链码进行签名。
 ChaincodeDeploymentSpec可以选择由所有者集合进行签名，从而创建一个SignedChaincodeDeploymentSpec(SignedCDS)。SignedCDS包括3个部分：

1. CDS包括源代码，链码的名称与版本号；

1. 链码的实例化策略，表示为背书策略；

1. 链码所有者的列表，由背书策略定义。


**当在某些通道上实例化链码时，背书策略是在带外确定的**，用于提供合适的MSP主体。如果没指定实例化策略，则默认的策略就是通道的任何MSP管理员。

每一个链码的所有者通过将SignedCDS与链码所有者的身份（例如证书）组合并签署组合结果来背书ChaincodeDeploymentSpec。

一个链码的所有者能够对自己所创建的签名过的链码包进行签名，需要使用如下命令：

```
peer chaincode signpackage ccpack.out signedccpack.out
```

ccpack.out、signedccpack.out分别是输入与输出包。signedccpack.out包括一个对链码包附加的签名（通过local msp进行的签名）。

#### 安装链码

将链码的源代码打包成ChaincodeDeploymentSpec（CDS）的规定的格式，然后**安装到通道中的背书节点上**。

当安装的链码包只包含一个ChaincodeDeploymentSpec时，将使用默认初始化策略并包括一个空的所有者列表。
链码应该仅仅被安装在链码所有者成员的背书节点上，用于实现链码对于网络中其它成员在逻辑上是隔离的。

安装链码会发送一个**SignedProposal到生命周期系统链码(LSCC)** ，也就是说会发送调用系统链码的交易。

使用CLI安装sacc链码的命令如下：

```
peer chaincode install -n sacc -v 1.0 -p sacc
```

- -n选项指定链码实例名称
- -v选项指定链码的版本
- -p选项指定链码所在路径，必须在GOPATH路径下

CLI内部创建**sacc**的SignedChaincodeDeploymentSpec，然后将其发送给本地Peer节点，Peer节点会**调用**LSCC上的安装方法。**为了在Peer节点上安装链码，SignedProposal的签名必须来自于Peer节点的本地MSP管理员之一**。

**未安装 chaincode 的节点不能执行 chaincode，但仍可以验证交易并提交到账本中。所以背书节点必须按照链码，记账节点并非必须安装链码。**

#### 实例化链码

**链码和通道是低耦合的：实例化调用生命周期系统链码(LSCC)用于创建及初始化通道上的链码。链码能够被绑定到任意数量的通道，以及在每个通道上单独的操作。无论链码安装及实例化到多少个通道上，每个通道的状态都是隔离的。**

实例化的创建者必须满足包含在SignedCDS内链码的**实例化策略**，而且还必须是通道的写入器（作为通道创建的一部分被配置）。可以防止部署链码的流氓实体或者欺骗者在未被绑定的通道上执行链码。

**默认的实例化策略是任意的通道MSP的管理员，因此链码实例化交易的创建者必须是通道管理员之一**。当交易提案到达背书节点后，背书节点会根据实例化策略验证创建者的签名。在提交实例化交易到账本前，在交易验证时再一次完成该操作。

**实例化交易同样设置了通道上的链码的背书策略** 。背书策略描述了交易被通道上成员接受的认证要求。
使用CLI去实例化sacc的链码并初始化状态为user1与0，命令如下：

```
peer chaincode instantiate -n sacc -v 1.0 -c '{"Args":["user1","0"]}' -P "OR ('Org1.member','Org2.member')"
```

- **-n选项指定链码实例名称**
- -v选项指定链码的版本
- -c 选项指定链码的调用参数
- -P选项指定链码的背书策略

链码的背书策略表示，org1.member或者org2.member必须对调用使用sacc(这名字起的让我以为是某种SCC)的交易进行签名，以保障交易是有效的。在成功实例化后，通道的链码进入激活状态，可以处理任意的交易提案。交易到达背书节点时，会同时被处理。

实例化选项：

```
root@5af5a3fb3bb7:/var/hyperledger/production# peer chaincode instantiate -h
Deploy the specified chaincode to the network.

Usage:
  peer chaincode instantiate [flags]

Flags:
  -C, --channelID string               The channel on which this command should be executed
      --collections-config string      The fully qualified path to the collection JSON file including the file name
      --connectionProfile string       Connection profile that provides the necessary connection information for the network. Note: currently only supported for providing peer connection information
  -c, --ctor string                    Constructor message for the chaincode in JSON format (default "{}")
  -E, --escc string                    The name of the endorsement system chaincode to be used for this chaincode
  -h, --help                           help for instantiate
  -l, --lang string                    Language the chaincode is written in (default "golang")
  -n, --name string                    Name of the chaincode
      --peerAddresses stringArray      The addresses of the peers to connect to
  -P, --policy string                  The endorsement policy associated to this chaincode
      --tlsRootCertFiles stringArray   If TLS is enabled, the paths to the TLS root cert files of the peers to connect to. The order and number of certs specified should match the --peerAddresses flag
  -v, --version string                 Version of the chaincode specified in install/instantiate/upgrade commands
  -V, --vscc string                    The name of the verification system chaincode to be used for this chaincode

Global Flags:
      --cafile string                       Path to file containing PEM-encoded trusted certificate(s) for the ordering endpoint
      --certfile string                     Path to file containing PEM-encoded X509 public key to use for mutual TLS communication with the orderer endpoint
      --clientauth                          Use mutual TLS when communicating with the orderer endpoint
      --connTimeout duration                Timeout for client to connect (default 3s)
      --keyfile string                      Path to file containing PEM-encoded private key to use for mutual TLS communication with the orderer endpoint
  -o, --orderer string                      Ordering service endpoint
      --ordererTLSHostnameOverride string   The hostname override to use when validating the TLS connection to the orderer.
      --tls                                 Use TLS when communicating with the orderer endpoint
      --transient string                    Transient map of arguments in JSON encoding
```



#### 调用链码

调用链码：

```
peer chaincode invoke -o orderer.example.com:7050 --tls $CORE_PEER_TLS_ENABLED --cafile $ORDERER_CA -C mychannel -n sacc -c '{"Args":["invoke","user1","user2","10"]}'
```

查询链码

```
peer chaincode query -C mychannel -n sacc -c '{"Args":["query","user1"]}'
```

**调用链码的前提是链码已经实例化。**

链码实例化之后存在了运行了一个容器，这个容器一直在运行，所以调用1个链码，实际是peer容器和链码容器交互的过程。

链码与Peer节点的交互过程如下：

1. 链码通过gRPC与Peer节点交互，当Peer节点收到客户端的交易提案请求后，会发送一个链码消息对象（包含交易提案信息、调用者信息）给对应的链码。
2. 链码调用Invoke方法，通过发送获取数据（GetState）和写入数据（PutState）消息，向Peer节点获取账本状态信息和发送预提交状态。
3. 链码发送模拟执行结果给Peer节点，Peer节点对交易提案和模拟执行结果进行背书签名。

![](https://lessisbetter.site/images/2019-07-fabric-invoke-chaincode.png)

![](https://lessisbetter.site/images/2019-07-chaincode_swimlane.png)

#### 升级链码

链码的升级通过改变其版本号（作为SignedCDS的一部分）。SignedCDS另外的部分，如所有者及实例化策略都是可选的。然而，**链码的名称必须是一致的，否则会被当做另外一个新的链码**。
在升级前，必须将新版本的链码安装到有需求的背书节点上。升级也是一种交易，会把新版本的链码绑定到通道中。**升级只能在一个时间点对一个通道产生影响，其它通道仍然运行旧版本的链码**。
由于可能存在多个版本的链码同时存在，**升级过程不会自动删除老版本链码，用户必须手动操作删除过程**。
升级与实例化transaction有一点不同的是：通过现有的chaincode实例化策略检查升级transaction，而不是用新的策略检查。这是为了确保只有当前实例化策略中指定的成员能够升级chaincode。
在升级期间，链码的Init函数也会被调用，执行有关升级的数据或者使用数据重新进行初始化，在升级链码的期间避免对状态进行重置。
安装新版本的链码
`peer chaincode install -n sacc -v 1 -p path/to/my/chaincode/v1`
upgrade升级链码
`peer chaincode upgrade -n sacc -v 1 -c '{"Args":["d", "e", "f"]}' -C mychannel`

#### 都是交易

安装、实例化、调用、升级链码，都是创建一笔交易，通过交易实现。

#### 链码开发


`github.com/hyperledger/fabric/core/chaincode/shim`包是开发Go语言链码的API。shim 包提供了链码与账本交互的中间层。链码通过 shim.ChaincodeStub 提供的方法来读取和修改账本的状态。

链码启动必须通过调用 shim 包中的 Start 函数，而 Start 函数被调用时需要传递一个类型为 Chaincode 的参数，这个参数 Chaincode 是一个接口类型，该接口中有两个重要的函数 Init 与 Invoke 。

Chaincode 接口定义如下：

```go
type Chaincode interface{
    Init(stub ChaincodeStubInterface) peer.Response
    Invoke(stub ChaincodeStubInterface) peer.Response
}
```

**Init 与 Invoke 方法**

编写链码，关键是实现 Init 与 Invoke 两个方法，必须由所有链码实现。Fabric 通过调用指定的函数来运行事务。

- **Init：**在链码实例化或升级时被调用, 完成初始化数据的工作。
- **invoke：**更新或查询提案事务中的分类帐本数据状态时，Invoke 方法被调用， 因此响应调用或查询的业务实现逻辑都需要在此方法中编写实现。

示例：https://blog.51cto.com/9291927/2318364


### 通道

**通道由排序服务管理**，排序服务节点还负责对通道中的交易进行排序。。

目前通道分为**系统通道（System Channel）和应用通道**（Application Channel）。排序服务通过系统通道来管理应用通道，用户的交易信息通过应用通道传递。

**每个组织可以有多个节点加入同一个通道**，组织内的节点中可以指定一个锚节点或多个锚节点（增强系统可靠性，避免单点故障）。另外，同一组织的节点会选举或指定主导节点（leading peer），主导节点负责接收从排序服务发来的区块，然后转发给本组织的其它节点。主导节点可以通过特定的算法选出，可以保证在节点数量不断变动的情况下仍能维持整个网络的稳定性。

在Fabric网络中，**可能同时存在多条彼此隔离的通道，每条通道包含一条私有的区块链和一个私有账本，通道中可以实例化一个或多个链码，以操作区块链上的数据**。

**通道是共识服务提供的一种通讯机制**，基于发布-订阅关系，将Peer节点和排序节点根据某个Topic连接在一起，形成一个具有保密性的通讯链路（虚拟），实现业务隔离的要求。

**排序服务提供了供Peer节点订阅的主题**（如发布-订阅消息队列），每个主题是一个通道。Peer节点可以订阅多个通道，并且只能访问自己所订阅通道上的交易，因此一个Peer节点可以通过接入多个通道参与到多条链中。

**排序服务支持多通道，提供了通向客户端和Peer节点的共享通信通道**，提供了包含交易的消息广播服务（broadcast和deliver）。客户端可以通过通道向连接到通道的所有节点广播（broadcast）消息，向连接到通道的所有节点投递(deliver)消息。多通道使得Peer节点可以基于应用访问控制策略来订阅任意数量的通道，应用程序根据业务逻辑决定将交易发送到1个或多个通道。

文档：https://hyperledger-fabric.readthedocs.io/en/release-1.4/channels.html

#### 创建

在创建通道的时候，需要定义通道的成员和组织、锚节点（anchor peer）和排序服务节点，一条与通道对应的区块链会同时生成，用于记录账本的交易，通道的初始配置信息记录在区块链的创世区块中，可以通过增加一个新的配置区块来更改通道的配置信息。

创建通道的时候定义了成员，只有通过成员MSP验证的实体，才能够加入到通道并访问通道的数据。在通道中一般包含有若干成员（组织），若两个网络实体的×××书能够追溯到同一个根CA，则认为这两个实体属于同一组织。

#### 配置

通道的配置信息都被打包到一个区块中，并存放在通道的共享账本中，成为通道的配置区块，配置区块除了配置信息外不包含其它交易信息。通道可以使用配置区块来更新配置，因此在账本中每新添加一个配置区块，通道就按照最新配置区块的定义来修改配置。通道账本的首个区块一定是配置区块，也称为**创世区块**（Genesis Block）。

### 交易

交易的过程，实际是共识的3步：背书、排序和校验。

#### 类型

Fabric区块链的交易分两种，**部署交易和调用交易**。

**部署交易把链码部署到Peer节点上并准备好被调用，当一个部署交易成功执行时，链码就被部署到各个背书节点上。（部署指实例化）**

调用交易是客户端应用程序通过Fabric提供的API调用先前已部署好的某个链码的某个函数执行交易，并相应地读取和写入KV数据库，返回是否成功或者失败。

#### 流程

详读这篇文档：https://hyperledger-fabric.readthedocs.io/en/release-1.4/txflow.html

背书节点校验客户端的签名，然后执行智能合约代码模拟交易。交易处理完成后，对交易信息签名，返回给客户端。客户端收到签名后的交易信息后，发给排序服务节点排序。排序服务节点将交易信息排序打包成区块后，广播发给确认节点，写入区块链中。

![](https://lessisbetter.site/images/2019-07-tx-flow.png)


##### 客户端提案

客户端应用程序利用SDK（Node.js，Java，Python）构造交易提案（Proposal），提案有2种：

1. 实例化chaincode。
2. 调用chaincode。

客户端把交易提案（**Proposal**）根据背书策略发送给一个或多个背书节点，**交易提案中包含本次交易要调用的合约标识、合约方法和参数信息以及客户端签名**等。
SDK将交易提案打包为可识别的格式（如gRPC上的protobuf），并使用用户的加密凭证为该交易提案生成唯一的签名。

背书策略定义需要哪些节点背书交易才有效，例如需要5个成员的背书节点中至少3个同意；或者某个特殊身份的成员支持等。客户端只有在收集足够多的背书节点的交易提案签名，交易才能被视为有效。

![](https://lessisbetter.site/images/2019-07-txflow-step1.png)

##### 背书节点为提案背书

背书节点（endorser）收到交易提案后，**验证签名**并确定提交者是否有权执行操作。背书节点将交易提案的参数作为输入，在当前状态KV数据库上执行交易，生成响应返回给客户端，响应包**含执行返回值、读写集的交易结果（此时不会更新账本），交易结果集、背书节点的签名和背书结果（YES/NO）作为提案的结果**，客户端SDK解析信息判断是否应用于后续的交易。

![](https://lessisbetter.site/images/2019-07-txflow-step2.png)

在所有合法性校验通过后，背书节点按照交易提案调用链码模拟执行交易。链码执行时，读取的数据（键值对）是背书节点中本地的状态数据库，链码读取过的数据回被归总到读集（Read Set）；链码对状态数据库的写操作并不会对账本做改变，所有的写操作将归总到一个写入集（Write Set）中记录下来。读集和写集将在确认节点中用于确定交易是否最终写入账本。

资料：https://hyperledger-fabric.readthedocs.io/en/release-1.4/glossary.html#endorsement

##### 客户端收集提案背书

客户端验证背书节点签名，并比较各节点返回的提案结果，判断提案结果是否一致以及是否参照指定的背书策略执行。

![](https://lessisbetter.site/images/2019-07-txflow-step3.png)

当背书结果都通过验证，并且满足背书策略时，客户端生成一笔交易发送给排序节点。**交易包含交易签名、proposal、读写集、背书结果和通道ID。**

![](https://lessisbetter.site/images/2019-07-txflow-step4.png)

##### orderer排序交易

排序服务节点对接收到的交易进行共识排序，然后按照区块生成策略，将一批交易打包到一起，生成新的区块，调用deliver API投递消息，发送给确认节点。

![](https://lessisbetter.site/images/2019-07-txflow-step5.png)

**区块的广播有两种触发条件**，一种是当通道的交易数量达到某个预设的阈值，另一种是在交易数量没有超过阈值但距离上次广播的时间超过某个特定阈值，也可触发广播数据块。两种方式相结合，使得经过排序的交易及时生成区块并广播给通道的Leader节点（记账节点），Leader节点验证后，再发送给同channel同组织的其他记账节点。

##### peer验证区块

peer需要对区块内的所有交易进行验证，验证交易是否按背书策略执行以及根据读写集把交易打上有效或者无效的标签。最后把区块追加到本地的区块链，修改世界状态。

记账节点收到排序服务节点发来的区块后，逐笔检查区块中的交易：

1. 先检查交易的合法性以及该交易是否曾经出现过。
2. 然后调用校验系统链码（VSCC，Validation System Chaincode）检验交易的签名背书是否合法，
3. 以及背书的数量是否满足背书策略的要求。
4. 记账节点对交易进行**多版本并发控制（MVCC）**检查，即校验交易的读集（Read Set）是否和当前账本中的版本一致（即没有变化）。如果没有改变，说明交易写集（Write Set）中对数据的修改有效，把该交易标注为有效，交易的写集更新到状态数据库中。如果当前账本的数据和读集版本不一致，则该交易被标注为无效，不更新状态数据库。

交易流程中，采用**MVCC的乐观锁模型，提高了系统的并发能力。但MVCC也带来了一些局限性。例如，在同一个区块中若有两个交易先后对某个数据项做更新，顺序在后的交易将失败，因为后序交易的读集版本和当前数据项版本已经不一致。**

![](https://lessisbetter.site/images/2019-07-blocks-3.png)

##### 区块写入账本

每个peer都把区块追加到对应channel的账本上，每个有效交易的write set会被提交到状态数据库。

![](https://lessisbetter.site/images/2019-07-txflow-step6.png)

##### 客户端获取交易结果

客户端可以通过事件订阅交易的结果：是否添加到数据库，是否有效。

#### 结构

![](https://lessisbetter.site/images/2019-07-fabric-storage.png)

### 账本

**账本由区块链和状态数据库两部分组成**。

1. 区块链是一组不可更改的有序的区块（数据块），记录着全部交易的日志。
2. 状态数据库记录了账本中所有键值对的当前值（世界状态），相当于对当前账本的交易日志做了索引。链码执行交易的时候需要读取账本的当前状态，从状态数据库可以迅速获取键值的最新状态。

![](https://lessisbetter.site/images/2019-07-fabric-storage.png)


![](https://lessisbetter.site/images/2019-07-fabric-storage-flow.png)


#### 数据库

Fabric区块链网络中，每个通道都有其账本，每个Peer节点都保存着其所加入通道的账本，Peer节点的账本包含如下数据：
1. 账本编号，用于快速查询存在哪些账本
1. 账本数据，用于区块数据存储
1. 区块索引，用于快速查询区块／交易
1. 状态数据，用于最新的**世界状态**数据
1. 历史数据，用于跟踪键的历史

Fabric的Peer节点账本中有四种数据库，idStore（ledgerID数据库）、blkstorage（block文件存储）、statedb（状态数据库）、historydb（历史数据库）。

**账本数据库**基于文件系统，将区块存储在文件块中，然后在区块索引LevelDB中存储区块交易对应的文件块及其偏移，即将区块索引LevelDB作为账本数据库的索引。目前**支持的区块索引有：区块编号、区块哈希、交易ID、区块交易编号**。

**状态数据库**存储的是所有曾经在交易中出现的键值对的最新值（世界状态）。调用链码执行交易可以改变状态数据，为了高效的执行链码调用，所有数据的最新值都被存放在状态数据库中；状态数据库是有序交易日志的快照，任何时候都可以根据交易日志重新生成状态数据库；状态数据库会在Peer节点启动的时候自动恢复或重构，未完备前，本Peer节点不会接受新的交易；状态数据库可以使用LevelDB或者CouchDB，CouchDB能够存储任意的二进制数据，支持富文本查询。链接：https://hyperledger-fabric.readthedocs.io/en/release-1.4/glossary.html#world-state 。

**历史状态数据库**用于查询某个key的历史修改记录，历史状态数据库并不存储key具体的值，而只记录在某个区块的某个交易里，某key变动了一次。后续需要查询的时候，根据变动历史去查询实际变动的值。

**ledgerID数据库**存储chainID，用于快速查询节点存在哪些账本。

![](https://lessisbetter.site/images/2019-07-fabric-storage-file.png)

ledgersData是Peer节点账本的根目录，Peer节点的账本存储在Peer节点容器的`/var/hyperledger/production/ledgersData`目录下，通过命令行可以进入Peer节点容器进行查看，命令如下：

```
docker exec -it peer0.org1.example.com bash
```



```
root@5af5a3fb3bb7:/var/hyperledger/production# ls -R chaincodes
chaincodes:
root@5af5a3fb3bb7:/var/hyperledger/production# ls -R transientStore/
transientStore/:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000




root@5af5a3fb3bb7:/var/hyperledger/production# ls -R ledgersData/
ledgersData/:
bookkeeper  chains  configHistory  historyLeveldb  ledgerProvider  pvtdataStore  stateLeveldb

ledgersData/bookkeeper:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000

ledgersData/chains:
chains  index

ledgersData/chains/chains:
mychannel

ledgersData/chains/chains/mychannel:
blockfile_000000

ledgersData/chains/index:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000

ledgersData/configHistory:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000

ledgersData/historyLeveldb:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000

ledgersData/ledgerProvider:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000

ledgersData/pvtdataStore:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000

ledgersData/stateLeveldb:
000001.log  CURRENT  LOCK  LOG  MANIFEST-000000
```

- chains/chains目录下的mychannel目录channel的名称，Fabric支持多通道的机制，而通道之间的账本是隔离的，每个通道都有自己的账本空间。
- chains/index目录包含levelDB数据库文件，存储区块索引数据库，使用leveldb实现。
- historyLeveldb目录存储智能合约中写入的key的历史记录的索引地址，使用leveldb实现。
- ledgerProvider目录存储当前节点所包含channel的信息（已经创建的channel id 和正在创建中的channel id），使用leveldb实现。
- stateLeveldb目录存储智能合约写入的数据，可选择使用leveldb或couchDB，即状态数据库。

#### 索引

区块索引用于快速定位区块。**索引键可以是区块高度、区块哈希、交易哈希。索引值为区块文件编号+文件内偏移量+区块数据长度。**

Hyperledger Fabric提供了多种区块索引的方式，以便能快速找到区块。索引的内容是文件位置指针（File Location Pointer）。文件位置指针由三个部分组成：所在文件的编号（fileSuffixNum）、文件内的偏移量（offset）、区块占用的字节数（bytesLength）。

#### 链

整个网络有一条系统链，保存有网络的配置信息，比如MSP、各种策略、各种配置项，系统链在排序服务中（即，peer上没有？），保存在ordering节点的系统channel中，任何改变整个网络配置的，都会产生一个新的配置块添加到系统链上去。

链接：https://hyperledger-fabric.readthedocs.io/en/release-1.4/glossary.html#system-chain

### 共识/排序服务

文档：https://hyperledger-fabric.readthedocs.io/en/release-1.4/orderer/ordering_service.html

#### kafka

共识集群由多个排序服务节点（OSN）和一个Kafka集群组成。排序节点之间不直接通信，仅仅与Kafka集群通信。

在排序节点的实现里，通道(Channel)在Kafka中是以主题topic的形式隔离。

**每个排序节点内部，针对每个通道都会建立与Kafka集群对应topic的生产者及消费者**。生产者将排序节点收到的交易发送到Kafka集群进行排序，在生产的同时，消费者也同步消费排序后的交易。

![](https://lessisbetter.site/images/2019-07-fabric-kafka.png)



#### Raft

fabric的raft基于etcd的raft，raft是CFT，是leader-follower模型。

需要注意的一点是，所有channel共用排序集群，但每个channel都有各自的Raft实例，所以每个channel可以选举自己的leader。

虽然所有的 Raft 节点都必须包含在系统通道中，但他们并不需要都包含在应用通道中。通道创建者(和通道管理员)拥有选择可用排序节点子集的能力并且可以根据需要增加或移除排序节点(只要每次只增加会移除一个节点)。

> where a leader node is elected (per channel) and its decisions are replicated by the followers.

链接：https://hyperledger-fabric.readthedocs.io/en/release-1.4/glossary.html#raft

### 通信

#### Gossip

gossip是数据扩散协议，有3个功能：

1. 管理节点发现和channel的成员关系
2. 同channel上的所有peer扩散账本数据
3. 同channel上的所有peer间同步账本状态

更多信息：https://hyperledger-fabric.readthedocs.io/en/release-1.4/gossip.html

**Gossip 协议最终的目的是将数据分发到网络中的每一个节点**，Gossip数据分发协议实现了两种数据传输方式。

##### 推送数据

1. 网络中的某个节点**随机选择N个节点**作为数据接收对象，N配置在配置文件中
1. 该节点向其选中的N个节点传输相应的信息
1. 接收到信息的节点处理它接收到的数据
1. 接收到数据的节点再从第一步开始重复执行

![](https://lessisbetter.site/images/2019-07-fabric-gossip-push.png)

##### 拉去数据

1. 某个节点**周期性**地选择随机N个节点询问有没有最新的信息
1. 收到请求的节点回复请求节点其最近未收到的信息

![](https://lessisbetter.site/images/2019-07-fabric-gossip-pull.png)

#### 数据同步

节点之间使用数据同步保证账本数据和状态数据的即使更新，数据同步主要有2类：

1. 主动广播，比如广播新打包的区块，排序节点把区块发送给主节点，它基于Gossip的推送数据
2. 主动请求，比如新加入的节点，向已存在的其他组织锚节点请求数据，锚节点给他响应，它基于Gossip的拉去数据

![](https://lessisbetter.site/images/2019-07-fabric-deliver-data.png)

![](https://lessisbetter.site/images/2019-07-fabric-request-data.png)

### 应用开发

文档：https://hyperledger-fabric.readthedocs.io/en/release-1.4/developapps/developing_applications.html

### Fabric网络

文档：https://hyperledger-fabric.readthedocs.io/en/release-1.4/network/network.html

文档里介绍了以上各种概念在网络中的位置。

