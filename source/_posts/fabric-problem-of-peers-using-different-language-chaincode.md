---
title: Fabric 1.4不同peer使用不同语言链码的问题
date: 2019-09-03 11:50:31
tags: ['区块链','Fabric']
---

## 前言

社区里在讨论一个问题，是由官方的文档引发的，文档上讲不同的peer可以使用不同语言的链码，前提是2份链码功能、接口等必须一致。

![fabric chaincode error](https://lessisbetter.site/images/2019-09-fabric-chaincode-error.png)

大家的问题是：

> 一个链码可以采用不同的语言实现，不同peer上使用不同的链码真的可行吗？

经过实证，这是不可行的。

分2种情况，2种都有问题：
1. 不同peer安装不同语言链码，然后同时实例化：实例化后，只能启动发送实例化交易的peer拥有的语言的链码
2. 部分peer先实例化，另外peer再安装不同语言链码：调用链码时报指纹不匹配错误

## 不同peer安装不同语言链码，然后同时实例化

1、修改BFYN，只在peer0.org1和peer0.org2上安装Go语言链码，不进行后续操作。

```
Installing chaincode on peer0.org1...
+ peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
+ res=0
+ set +x
2019-09-03 02:08:43.813 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-09-03 02:08:43.813 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-09-03 02:08:44.108 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
===================== Chaincode is installed on peer0.org1 =====================

Install chaincode on peer0.org2...
+ peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
+ res=0
+ set +x
2019-09-03 02:08:44.260 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-09-03 02:08:44.260 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-09-03 02:08:44.529 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
===================== Chaincode is installed on peer0.org2 =====================


========= All GOOD, BYFN execution completed ===========
```

2、在peer1.org1上安装Java语言链码

```
root@6cec20eb7502:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode install -n mycc -v 1.0 -l java -p /opt/gopath/src/github.com/chaincode/chaincode_example02/java/
2019-09-03 03:19:44.710 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-09-03 03:19:44.711 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-09-03 03:19:44.754 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
```

3、在peer1.org1上发起实例化链码

```
root@6cec20eb7502:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode instantiate -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc -l golang -v 1.0 -c '{"Args":["init","a","100","b","200"]}' -P 'OR ('\''Org1MSP.peer'\'','\''Org2MSP.peer'\'')'
2019-09-03 03:22:12.430 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-09-03 03:22:12.431 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
```

4、查看链码容器，只有peer1.org1的链码容器，peer0.org1和peer0.org2的链码容器都没有起来。

```
➜  fabric-sdk-go-sample git:(master) ✗ docker ps
CONTAINER ID        IMAGE                                                                                                  COMMAND                  CREATED             STATUS              PORTS                      NAMES
f8f6aa8b5da6        dev-peer1.org1.example.com-mycc-1.0-cd123150154e6bf2df7ce682e0b1bcbea40499416f37a6da3aae14c4eb51b08d   "/root/chaincode-jav…"   37 seconds ago      Up 36 seconds                                  dev-peer1.org1.example.com-mycc-1.0
6cec20eb7502        hyperledger/fabric-tools:latest                                                                        "/bin/bash"              About an hour ago   Up About an hour                               cli
7e134fe7e8e9        hyperledger/fabric-peer:latest                                                                         "peer node start"        About an hour ago   Up About an hour    0.0.0.0:8051->8051/tcp     peer1.org1.example.com
ed6f5511d938        hyperledger/fabric-peer:latest                                                                         "peer node start"        About an hour ago   Up About an hour    0.0.0.0:10051->10051/tcp   peer1.org2.example.com
025a71178777        hyperledger/fabric-peer:latest                                                                         "peer node start"        About an hour ago   Up About an hour    0.0.0.0:7051->7051/tcp     peer0.org1.example.com
8687dfd14e7b        hyperledger/fabric-peer:latest                                                                         "peer node start"        About an hour ago   Up About an hour    0.0.0.0:9051->9051/tcp     peer0.org2.example.com
e9cc8b410d7f        hyperledger/fabric-orderer:latest                                                                      "orderer"                About an hour ago   Up About an hour    0.0.0.0:7050->7050/tcp     orderer.example.com
```

## 部分peer先实例化，另外peer再安装不同语言链码

不改造BYFN，原生启动。peer0.org1，peer0.org2，peer1.org2都已经实例化了Go语言链码。

然后在peer1.org1上安装Java语言的链码，在执行Invoke或者查询，报指纹不匹配-数据不匹配的错误。

原因分析：操作链码时，会调用LSCC的`LifeCycleSysCC.getCCCode`获取链码，一份链码是从数据库取的，即当前链码容器的，一份链码是本地存储的，会对2份进行匹配，如果不匹配就会报指纹不匹配错误。

匹配函数为`CDSPackage.ValidateCC`，匹配项为：
1. 名称、版本
2. CodeHash、元数据Hash

调用链码时报的指纹不匹配错误：

```
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode install -n mycc -v 1.0 -l java -p /opt/gopath/src/github.com/chaincode/chaincode_example02/java/
2019-09-03 01:52:15.714 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-09-03 01:52:15.714 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-09-03 01:52:15.755 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
Error: endorsement failure during query. response: status:500 message:"failed to execute transaction b8b740aab0e6dd10cfe62416240ef94bfb90a55358904233c4d60dd5a39e6fe3: [channel mychannel] failed to get chaincode container info for mycc:1.0: could not get chaincode code: chaincode fingerprint mismatch: data mismatch"
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@d0533ffe1864:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode invoke -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc --peerAddresses peer1.org1.example.com:8051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer1.org1.example.com/tls/ca.crt  -c '{"Args":["invoke","a","b","50"]}'
Error: endorsement failure during invoke. response: status:500 message:"failed to execute transaction aec5a0ccbcf86032774dc80220b90419d2816cc3f050a104c1cfcde55a2247cb: [channel mychannel] failed to get chaincode container info for mycc:1.0: could not get chaincode code: chaincode fingerprint mismatch: data mismatch"
```

## 文章

另外，社区里的hucg编写了一篇源码文章：https://blog.csdn.net/love_feng_forever/article/details/100532324
