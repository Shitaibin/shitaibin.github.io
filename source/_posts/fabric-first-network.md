---
title: 详解Fabric网络搭建
date: 2019-07-25 11:37:57
tags: ['区块链', 'Fabric']
---

这篇文章介绍了如何快速的搭建一个fabric网络，然后又把搭建过程分解，针对每一步都做详细解释，希望你能熟练今后到不看文档也能搭建出fabric网络。

本文是[Building Your First Network](https://hyperledger-fabric.readthedocs.io/en/release-1.4/build_network.html)的笔记和实践记录，基于Fabric 1.4，commit id：9dce73。

前提：
1. 安装了Docker、Go等环境。
1. 已经下载了fabric仓库，完成`make all`。

## 下载fabric-samples和准备工作

有2种方式。

方式1：一键下载和编译。

```
curl -sSL http://bit.ly/2ysbOFE | bash -s
```

方式2：手动clone，放到GOPATH下，然后执行脚本，构建和拉去一些镜像，为搭建网络做准备。方式2只不过是把方式1的工作，手动做掉了。

```
git clone https://github.com/hyperledger/fabric-samples.git
cd fabric-samples
sh scripts/bootstrap.sh
```

参考资料：https://hyperledger-fabric.readthedocs.io/en/release-1.4/install.html。

## 快速启动你的第一个Fabric网络

这一节的目的是用几分钟的时间启动一个网络，并且了解启动一个网络的过程。

### 启动网络

`fabric-samples`下有多个示例，本次要使用的是`first-network`：

```
➜  fabric-samples git:(release-1.4) ll | grep ^d
drwxr-xr-x 5 centos centos  193 7月  12 08:21 balance-transfer
drwxr-xr-x 4 centos centos  273 7月  12 08:21 basic-network
drwxrwxr-x 2 centos centos  175 1月   9 2019 bin
drwxr-xr-x 8 centos centos  113 7月  12 08:21 chaincode
drwxr-xr-x 3 centos centos  139 7月  12 08:21 chaincode-docker-devmode
drwxr-xr-x 3 centos centos   44 7月  12 06:47 commercial-paper
drwxrwxr-x 2 centos centos   64 1月   9 2019 config
drwxr-xr-x 2 centos centos   59 7月  12 08:21 docs
drwxr-xr-x 5 centos centos  110 7月  12 08:21 fabcar
drwxr-xr-x 7 centos centos 4.0K 7月  17 03:14 first-network
drwxr-xr-x 4 centos centos   55 7月  12 08:21 high-throughput
drwxr-xr-x 4 centos centos   55 7月  12 08:21 interest_rate_swaps
drwxr-xr-x 4 centos centos   67 7月  17 03:46 scripts
```

进入`first-network`然后执行`./byfn.sh up`，启动操作会持续两三分钟，`byfn`是Building Your First Network的缩写。

启动过程实际做了这些事：

第一阶段：生成配置文件

1. 使用加密工具`cryptogen`生成证书
1. 使用工具`configtxgen`生成orderer节点的创世块，即得到genesis.block
1. 使用工具`configtxgen`生成配置应用通道channel的交易`channel.tx`，即得到mychannel.block
1. 使用工具`configtxgen`生成Org1的MSP的anchor peer
1. 使用工具`configtxgen`生成Org2的MSP的anchor peer

第二阶段：启动网络

这个阶段是启动容器，包含客户端(cli)、peer，每个org有2个peer，peer0和peer1，默认是solo共识算法，还会启动1个orderer。

第三阶段：创建和加入通道，部署和测试链码

1. 创建应用通道mychannel
1. peer加入mychannel
1. 在mychannel上更新Org1和Org2 MSP的anchor peer
1. 在ogr1好org2的peer0上安装chaincode
1. 在mychannel中，在peer0.org2上实例化chaincode，1个通道上只需示例化1次chaincode
1. 在mychannel中，Invoke刚实例化的chaincode
1. 在peer1.org2上安装chaincode，并查询

`byfn.sh`中的`networkUp()`函数是`./byfn.sh up`的主要执行函数，它的主要功能就是组织上面3个阶段。

```bash
# Generate the needed certificates, the genesis block and start the network.
function networkUp() {
  checkPrereqs
  # 生成配置：证书、交易、私钥
  # generate artifacts if they don't exist
  if [ ! -d "crypto-config" ]; then
    generateCerts
    replacePrivateKey
    generateChannelArtifacts
  fi
  # 启动网络/容器
  COMPOSE_FILES="-f ${COMPOSE_FILE}"
  if [ "${CERTIFICATE_AUTHORITIES}" == "true" ]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f ${COMPOSE_FILE_CA}"
    export BYFN_CA1_PRIVATE_KEY=$(cd crypto-config/peerOrganizations/org1.example.com/ca && ls *_sk)
    export BYFN_CA2_PRIVATE_KEY=$(cd crypto-config/peerOrganizations/org2.example.com/ca && ls *_sk)
  fi
  if [ "${CONSENSUS_TYPE}" == "kafka" ]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f ${COMPOSE_FILE_KAFKA}"
  elif [ "${CONSENSUS_TYPE}" == "etcdraft" ]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f ${COMPOSE_FILE_RAFT2}"
  fi
  if [ "${IF_COUCHDB}" == "couchdb" ]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f ${COMPOSE_FILE_COUCH}"
  fi
  IMAGE_TAG=$IMAGETAG docker-compose ${COMPOSE_FILES} up -d 2>&1
  # 检查容器是否启动
  docker ps -a
  if [ $? -ne 0 ]; then
    echo "ERROR !!!! Unable to start network"
    exit 1
  fi

  if [ "$CONSENSUS_TYPE" == "kafka" ]; then
    sleep 1
    echo "Sleeping 10s to allow $CONSENSUS_TYPE cluster to complete booting"
    sleep 9
  fi

  if [ "$CONSENSUS_TYPE" == "etcdraft" ]; then
    sleep 1
    echo "Sleeping 15s to allow $CONSENSUS_TYPE cluster to complete booting"
    sleep 14
  fi

  # 执行端到端脚本：创建并加入应用通道，然后测试
  # now run the end to end script
  docker exec cli scripts/script.sh $CHANNEL_NAME $CLI_DELAY $LANGUAGE $CLI_TIMEOUT $VERBOSE $NO_CHAINCODE
  if [ $? -ne 0 ]; then
    echo "ERROR !!!! Test failed"
    exit 1
  fi
}
```

启动日志，日志中标记了各阶段，建议详读一下：

```
$ cd first-network
➜  first-network git:(release-1.4) ./byfn.sh up
Starting for channel 'mychannel' with CLI timeout of '10' seconds and CLI delay of '3' seconds
Continue? [Y/n] y
proceeding ...
LOCAL_VERSION=1.4.0
DOCKER_IMAGE_VERSION=1.4.0
/home/centos/go/src/github.com/hyperledger/fabric-samples/bin/cryptogen

/**** 第1阶段：生成配置文件 ****/

##########################################################
##### Generate certificates using cryptogen tool #########
##########################################################
+ cryptogen generate --config=./crypto-config.yaml
org1.example.com
org2.example.com
+ res=0
+ set +x

/home/centos/go/src/github.com/hyperledger/fabric-samples/bin/configtxgen
##########################################################
#########  Generating Orderer Genesis block ##############
##########################################################
CONSENSUS_TYPE=solo
+ '[' solo == solo ']'
+ configtxgen -profile TwoOrgsOrdererGenesis -channelID byfn-sys-channel -outputBlock ./channel-artifacts/genesis.block
2019-07-17 06:34:26.973 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-17 06:34:27.088 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 002 orderer type: solo
2019-07-17 06:34:27.088 UTC [common.tools.configtxgen.localconfig] Load -> INFO 003 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.186 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 004 orderer type: solo
2019-07-17 06:34:27.186 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 005 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.188 UTC [common.tools.configtxgen] doOutputBlock -> INFO 006 Generating genesis block
2019-07-17 06:34:27.189 UTC [common.tools.configtxgen] doOutputBlock -> INFO 007 Writing genesis block
+ res=0
+ set +x

#################################################################
### Generating channel configuration transaction 'channel.tx' ###
#################################################################
+ configtxgen -profile TwoOrgsChannel -outputCreateChannelTx ./channel-artifacts/channel.tx -channelID mychannel
2019-07-17 06:34:27.228 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-17 06:34:27.315 UTC [common.tools.configtxgen.localconfig] Load -> INFO 002 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.422 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 orderer type: solo
2019-07-17 06:34:27.422 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.422 UTC [common.tools.configtxgen] doOutputChannelCreateTx -> INFO 005 Generating new channel configtx
2019-07-17 06:34:27.425 UTC [common.tools.configtxgen] doOutputChannelCreateTx -> INFO 006 Writing new channel tx
+ res=0
+ set +x

#################################################################
#######    Generating anchor peer update for Org1MSP   ##########
#################################################################
+ configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org1MSPanchors.tx -channelID mychannel -asOrg Org1MSP
2019-07-17 06:34:27.477 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-17 06:34:27.559 UTC [common.tools.configtxgen.localconfig] Load -> INFO 002 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.649 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 orderer type: solo
2019-07-17 06:34:27.649 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.649 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 005 Generating anchor peer update
2019-07-17 06:34:27.649 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 006 Writing anchor peer update
+ res=0
+ set +x

#################################################################
#######    Generating anchor peer update for Org2MSP   ##########
#################################################################
+ configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org2MSPanchors.tx -channelID mychannel -asOrg Org2MSP
2019-07-17 06:34:27.689 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-17 06:34:27.773 UTC [common.tools.configtxgen.localconfig] Load -> INFO 002 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.886 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 orderer type: solo
2019-07-17 06:34:27.886 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-17 06:34:27.886 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 005 Generating anchor peer update
2019-07-17 06:34:27.886 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 006 Writing anchor peer update
+ res=0
+ set +x



/**** 第2阶段：启动容器网络 ****/


Creating network "net_byfn" with the default driver
Creating volume "net_orderer.example.com" with default driver
Creating volume "net_peer0.org1.example.com" with default driver
Creating volume "net_peer1.org1.example.com" with default driver
Creating volume "net_peer0.org2.example.com" with default driver
Creating volume "net_peer1.org2.example.com" with default driver
Creating orderer.example.com    ... done
Creating peer0.org2.example.com ... done
Creating peer1.org2.example.com ... done
Creating peer0.org1.example.com ... done
Creating peer1.org1.example.com ... done
Creating cli                    ... done
CONTAINER ID        IMAGE                                                                                                          COMMAND                  CREATED                  STATUS                      PORTS                      NAMES
8c2ccb5ee443        hyperledger/fabric-tools:latest                                                                                "/bin/bash"              Less than a second ago   Up Less than a second                                  cli
5af5a3fb3bb7        hyperledger/fabric-peer:latest                                                                                 "peer node start"        2 seconds ago            Up Less than a second       0.0.0.0:8051->8051/tcp     peer1.org1.example.com
396b363bb6f5        hyperledger/fabric-peer:latest                                                                                 "peer node start"        2 seconds ago            Up Less than a second       0.0.0.0:7051->7051/tcp     peer0.org1.example.com
94be2011d20f        hyperledger/fabric-orderer:latest                                                                              "orderer"                2 seconds ago            Up Less than a second       0.0.0.0:7050->7050/tcp     orderer.example.com
da8c17df215d        hyperledger/fabric-peer:latest                                                                                 "peer node start"        2 seconds ago            Up Less than a second       0.0.0.0:9051->9051/tcp     peer0.org2.example.com
fcd30620e876        hyperledger/fabric-peer:latest                                                                                 "peer node start"        2 seconds ago            Up Less than a second       0.0.0.0:10051->10051/tcp   peer1.org2.example.com
10510312db61        dc535406-4013-4141-be9e-e472c1cf24a1-simple-5e32b897538246406863e63956e4c561246725b6fbf114a1fedff16775cf782d   "tail -f /dev/null"      22 hours ago             Exited (137) 22 hours ago                              dc535406-4013-4141-be9e-e472c1cf24a1-simple
21a3b8dc137a        hyperledger/fabric-buildenv:amd64-latest                                                                       "/bin/bash"              22 hours ago             Exited (0) 22 hours ago                                musing_swartz
48407948b7d7        hyperledger/fabric-buildenv                                                                                    "/bin/bash"              22 hours ago             Exited (130) 22 hours ago                              affectionate_curie
358f0c0de3e1        92b20cd39f98                                                                                                   "/bin/bash"              23 hours ago             Exited (130) 22 hours ago                              festive_clarke
de5938eccc11        92b20cd39f98                                                                                                   "./scripts/check_dep…"   23 hours ago             Exited (127) 23 hours ago                              quizzical_einstein
324b27de3a34        92b20cd39f98                                                                                                   "/bin/bash"              23 hours ago             Exited (0) 23 hours ago                                amazing_booth
26a53801f203        92b20cd39f98                                                                                                   "./scripts/check_dep…"   23 hours ago             Exited (127) 23 hours ago                              jolly_saha
94a33ddda70a        92b20cd39f98                                                                                                   "./scripts/golinter.…"   23 hours ago             Exited (0) 23 hours ago                                peaceful_allen
6a0c7fded448        92b20cd39f98                                                                                                   "./scripts/golinter.…"   23 hours ago             Created                                                recursing_beaver
233496b4065c        92b20cd39f98                                                                                                   "/bin/bash"              23 hours ago             Exited (0) 23 hours ago                                wizardly_shockley
f0a255a96610        92b20cd39f98                                                                                                   "/bin/bash"              23 hours ago             Exited (0) 23 hours ago                                jolly_ganguly
664416bc4fee        965663acb7cf                                                                                                   "/bin/sh -c 'apt-get…"   24 hours ago             Exited (100) 24 hours ago                              nostalgic_chaplygin
51cf784ef4e1        ba82c6de-50fb-4ffd-989d-0dcf54e14e3b-simple-9961bcae6dad48592af2e9f1c1df3c96b568f9394ec82b2f351e79fa51a4f786   "tail -f /dev/null"      47 hours ago             Exited (137) 47 hours ago                              ba82c6de-50fb-4ffd-989d-0dcf54e14e3b-simple
b7642b085ac1        14669948-7a23-4b3b-aa14-8b0622986e03-simple-f8a7b2e1352d04d884580725c2be9b642dd29df7e3e095a4a9403ac789dde2ac   "tail -f /dev/null"      2 days ago               Exited (137) 2 days ago                                14669948-7a23-4b3b-aa14-8b0622986e03-simple

/**** 第3阶段：创建并加入应用通道，然后测试 ****/

 ____    _____      _      ____    _____
/ ___|  |_   _|    / \    |  _ \  |_   _|
\___ \    | |     / _ \   | |_) |   | |
 ___) |   | |    / ___ \  |  _ <    | |
|____/    |_|   /_/   \_\ |_| \_\   |_|

Build your first network (BYFN) end-to-end test

Channel name : mychannel
Creating channel...
+ peer channel create -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/channel.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
+ res=0
+ set +x
2019-07-17 06:34:32.113 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:32.190 UTC [cli.common] readBlock -> INFO 002 Received block: 0
===================== Channel 'mychannel' created =====================

Having all peers join the channel...
+ peer channel join -b mychannel.block
+ res=0
+ set +x
2019-07-17 06:34:32.272 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:32.338 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
===================== peer0.org1 joined channel 'mychannel' =====================

+ peer channel join -b mychannel.block
+ res=0
+ set +x
2019-07-17 06:34:35.449 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:35.536 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
===================== peer1.org1 joined channel 'mychannel' =====================

+ peer channel join -b mychannel.block
+ res=0
+ set +x
2019-07-17 06:34:38.617 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:38.673 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
===================== peer0.org2 joined channel 'mychannel' =====================

+ peer channel join -b mychannel.block
+ res=0
+ set +x
2019-07-17 06:34:41.755 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:41.837 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
===================== peer1.org2 joined channel 'mychannel' =====================

Updating anchor peers for org1...
+ peer channel update -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/Org1MSPanchors.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
+ res=0
+ set +x
2019-07-17 06:34:44.930 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:44.951 UTC [channelCmd] update -> INFO 002 Successfully submitted channel update
===================== Anchor peers updated for org 'Org1MSP' on channel 'mychannel' =====================

Updating anchor peers for org2...
+ peer channel update -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/Org2MSPanchors.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
+ res=0
+ set +x
2019-07-17 06:34:48.037 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-17 06:34:48.059 UTC [channelCmd] update -> INFO 002 Successfully submitted channel update
===================== Anchor peers updated for org 'Org2MSP' on channel 'mychannel' =====================

Installing chaincode on peer0.org1...
+ peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
+ res=0
+ set +x
2019-07-17 06:34:51.167 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-17 06:34:51.167 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-07-17 06:34:51.462 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
===================== Chaincode is installed on peer0.org1 =====================

Install chaincode on peer0.org2...
+ peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
+ res=0
+ set +x
2019-07-17 06:34:51.542 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-17 06:34:51.542 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-07-17 06:34:51.817 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
===================== Chaincode is installed on peer0.org2 =====================

Instantiating chaincode on peer0.org2...
+ peer chaincode instantiate -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc -l golang -v 1.0 -c '{"Args":["init","a","100","b","200"]}' -P 'AND ('\''Org1MSP.peer'\'','\''Org2MSP.peer'\'')'
+ res=0
+ set +x
2019-07-17 06:34:51.910 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-17 06:34:51.910 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
===================== Chaincode is instantiated on peer0.org2 on channel 'mychannel' =====================

Querying chaincode on peer0.org1...
===================== Querying on peer0.org1 on channel 'mychannel'... =====================
+ peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
Attempting to Query peer0.org1 ...3 secs
+ res=0
+ set +x

100
===================== Query successful on peer0.org1 on channel 'mychannel' =====================
Sending invoke transaction on peer0.org1 peer0.org2...
+ peer chaincode invoke -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc --peerAddresses peer0.org1.example.com:7051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt --peerAddresses peer0.org2.example.com:9051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt -c '{"Args":["invoke","a","b","10"]}'
+ res=0
+ set +x
2019-07-17 06:35:27.719 UTC [chaincodeCmd] chaincodeInvokeOrQuery -> INFO 001 Chaincode invoke successful. result: status:200
===================== Invoke transaction successful on peer0.org1 peer0.org2 on channel 'mychannel' =====================

Installing chaincode on peer1.org2...
+ peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
+ res=0
+ set +x
2019-07-17 06:35:27.809 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-17 06:35:27.809 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-07-17 06:35:28.060 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
===================== Chaincode is installed on peer1.org2 =====================

Querying chaincode on peer1.org2...
===================== Querying on peer1.org2 on channel 'mychannel'... =====================
+ peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
Attempting to Query peer1.org2 ...3 secs
+ res=0
+ set +x

90
===================== Query successful on peer1.org2 on channel 'mychannel' =====================

========= All GOOD, BYFN execution completed ===========


 _____   _   _   ____
| ____| | \ | | |  _ \
|  _|   |  \| | | | | |
| |___  | |\  | | |_| |
|_____| |_| \_| |____/
```


使用docker查看起来的服务：

```
➜  first-network git:(release-1.4) docker ps
CONTAINER ID        IMAGE                                                                                                  COMMAND                  CREATED             STATUS              PORTS                      NAMES
fe690a4f3e9f        dev-peer1.org2.example.com-mycc-1.0-26c2ef32838554aac4f7ad6f100aca865e87959c9a126e86d764c8d01f8346ab   "chaincode -peer.add…"   2 hours ago         Up 2 hours                                     dev-peer1.org2.example.com-mycc-1.0
03a5f82384a0        dev-peer0.org1.example.com-mycc-1.0-384f11f484b9302df90b453200cfb25174305fce8f53f4e94d45ee3b6cab0ce9   "chaincode -peer.add…"   2 hours ago         Up 2 hours                                     dev-peer0.org1.example.com-mycc-1.0
a737b47e9de6        dev-peer0.org2.example.com-mycc-1.0-15b571b3ce849066b7ec74497da3b27e54e0df1345daff3951b94245ce09c42b   "chaincode -peer.add…"   2 hours ago         Up 2 hours                                     dev-peer0.org2.example.com-mycc-1.0
8c2ccb5ee443        hyperledger/fabric-tools:latest                                                                        "/bin/bash"              2 hours ago         Up 2 hours                                     cli
5af5a3fb3bb7        hyperledger/fabric-peer:latest                                                                         "peer node start"        2 hours ago         Up 2 hours          0.0.0.0:8051->8051/tcp     peer1.org1.example.com
396b363bb6f5        hyperledger/fabric-peer:latest                                                                         "peer node start"        2 hours ago         Up 2 hours          0.0.0.0:7051->7051/tcp     peer0.org1.example.com
94be2011d20f        hyperledger/fabric-orderer:latest                                                                      "orderer"                2 hours ago         Up 2 hours          0.0.0.0:7050->7050/tcp     orderer.example.com
da8c17df215d        hyperledger/fabric-peer:latest                                                                         "peer node start"        2 hours ago         Up 2 hours          0.0.0.0:9051->9051/tcp     peer0.org2.example.com
fcd30620e876        hyperledger/fabric-peer:latest                                                                         "peer node start"        2 hours ago         Up 2 hours          0.0.0.0:10051->10051/tcp   peer1.org2.example.com
```

上面有3个`dev-peer*.org*.example.com-mycc-1.0`容器，它们是链码容器，**每一个安装过链码的peer都会创建一个属于自己的链码容器**，在调用链码的时候，peer会通过gRPC和自己的链码容器通信。

### 关闭网络

使用`./byfn.sh down`命令，关闭`first-network`：

1. 依次停止channel、客户端、orderer、peer
2. 删除cli、orderer、peer、netowrk
3. 删除docker镜像


**当`./byfn.sh up`失败时，也需要使用此命令清理数据，以免后面启动网络时出问题。**

```
➜  first-network git:(release-1.4) ./byfn.sh down
Stopping for channel 'mychannel' with CLI timeout of '10' seconds and CLI delay of '3' seconds
Continue? [Y/n] y
proceeding ...
WARNING: The BYFN_CA1_PRIVATE_KEY variable is not set. Defaulting to a blank string.
WARNING: The BYFN_CA2_PRIVATE_KEY variable is not set. Defaulting to a blank string.
Stopping cli                    ... done
Stopping orderer.example.com    ... done
Stopping peer1.org1.example.com ... done
Stopping peer0.org1.example.com ... done
Stopping peer0.org2.example.com ... done
Stopping peer1.org2.example.com ... done
Removing cli                    ... done
Removing orderer.example.com    ... done
Removing peer1.org1.example.com ... done
Removing peer0.org1.example.com ... done
Removing peer0.org2.example.com ... done
Removing peer1.org2.example.com ... done
Removing network net_byfn
Removing volume net_orderer.example.com
Removing volume net_peer0.org1.example.com
Removing volume net_peer1.org1.example.com
Removing volume net_peer0.org2.example.com
Removing volume net_peer1.org2.example.com
Removing volume net_orderer2.example.com
WARNING: Volume net_orderer2.example.com not found.
Removing volume net_orderer3.example.com
WARNING: Volume net_orderer3.example.com not found.
Removing volume net_orderer4.example.com
WARNING: Volume net_orderer4.example.com not found.
Removing volume net_orderer5.example.com
WARNING: Volume net_orderer5.example.com not found.
Removing volume net_peer0.org3.example.com
WARNING: Volume net_peer0.org3.example.com not found.
Removing volume net_peer1.org3.example.com
WARNING: Volume net_peer1.org3.example.com not found.
05c281ff186c
f3ccbe5e2b80
7f0144ca0eae
Untagged: dev-peer1.org2.example.com-mycc-1.0-26c2ef32838554aac4f7ad6f100aca865e87959c9a126e86d764c8d01f8346ab:latest
Deleted: sha256:9425c8298cafe082ed22c5968d431a6098d53ef2318fb5d286efb96b4bc44915
Deleted: sha256:9005a0d9f52947d9256aa4766d4c26a9bab98f229aab7f2598da05789fc977ef
Deleted: sha256:98602d24729b179952f685f8f83f1effaf3733e7f93354a9d31b15f711bc0fac
Deleted: sha256:fe2b67155487d7e001c8a0b2ef100bb710b1b816897bc9d2a80029f4c7bd0b54
Untagged: dev-peer0.org1.example.com-mycc-1.0-384f11f484b9302df90b453200cfb25174305fce8f53f4e94d45ee3b6cab0ce9:latest
Deleted: sha256:0759f367d73c68e71b6077ebd46611d43a8d9c1c9ebc398b838010268b175d65
Deleted: sha256:2d56a884d5514a4467471cf06b42c0cfa492a80a239d48f79fa48273982d81b7
Deleted: sha256:614c6a2a164cc8afbb7f348fdf6d048834dc0cb2a94a22638b8d4dcd72eaeb14
Deleted: sha256:9a39bc364e8d141bdab60a80946e4af10513cb070c34e4bda1b1cbbf88f9dca3
Untagged: dev-peer0.org2.example.com-mycc-1.0-15b571b3ce849066b7ec74497da3b27e54e0df1345daff3951b94245ce09c42b:latest
Deleted: sha256:63a4ecd2677f62197f547b1cef9041e3f3ad5c929b1dcd139610b106862a92b5
Deleted: sha256:6a30b775f40f687d0ed98fe9d5fdd2da60ce22753b066db599e4308303f16c13
Deleted: sha256:d94c0213bc68b7ee8dfa942c82c07cf8d8b3e7a4d68cf5ca79d372557e5f6567
Deleted: sha256:c720d5e3b8c3b5690da0b10588517592ca11d94b3427cf75e88be0e000352ec9
```

## 部署网络步骤详解

### 准备工作

1. 以下用到的工具都在`fabric-samples/bin`目录下，手动执行记得把该目录添加到PATH。
1. 这些目录下的工具必须是跟当前`fabirc`项目是版本匹配的，最好把fabric编译生成的工具`fabric/build/bin/*`，拷贝到`fabric-samples/bin`目录。
1. 执行`./byfn.sh down`清理掉之前启动的数据，不然可能造成错误。

### 生成证书

从`byfn.sh`中能找到生成证书的命令，手动执行命令可以生成证书，生成的证书在crypto-config目录下。

`crypto-config.yaml`是证书的配置文件。`ordererOrganizations`是系统通道组织，`peerOrganizations`是应用通道组织，包含2个组织：`org1.example.com`和`org2.example.com`。

各组织的子目录是：证书、MSP、私钥、TLS证书、以及组织下的用户，用户目录会包含所有用户，以及用户的各种证书。

```bash
➜  first-network git:(release-1.4) cryptogen generate --config=./crypto-config.yaml
org1.example.com
org2.example.com
➜  first-network git:(release-1.4) tree crypto-config -L 3
crypto-config
├── ordererOrganizations
│   └── example.com
│       ├── ca
│       ├── msp
│       ├── orderers
│       ├── tlsca
│       └── users
└── peerOrganizations
    ├── org1.example.com
    │   ├── ca
    │   ├── msp
    │   ├── peers
    │   ├── tlsca
    │   └── users
    └── org2.example.com
        ├── ca
        ├── msp
        ├── peers
        ├── tlsca
        └── users

20 directories, 0 files
```

### 生成创世块

系统通道保存的链是系统链，链上的区块都是配置信息，它的第一个区块，被称为创世块`genesis.block`，用来初始化系统链。

生成创世块的工具是`configtxgen`，会自动在执行目录下寻找`configtx.yaml`文件，该文件包含了网络的初始配置，使用`-profile`指定系统链的配置`TwoOrgsOrdererGenesis`，该变量定义在`configtx.yaml`中。

使用`-outputBlock`指定输出的创世块文件。

命令：

```
configtxgen -profile TwoOrgsOrdererGenesis -channelID byfn-sys-channel -outputBlock ./channel-artifacts/genesis.block
```

记录：

```
➜  first-network git:(release-1.4) configtxgen -profile TwoOrgsOrdererGenesis -channelID byfn-sys-channel -outputBlock ./channel-artifacts/genesis.block
2019-07-29 07:17:02.140 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-29 07:17:02.229 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 002 orderer type: solo
2019-07-29 07:17:02.229 UTC [common.tools.configtxgen.localconfig] Load -> INFO 003 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:17:02.311 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 004 orderer type: solo
2019-07-29 07:17:02.311 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 005 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:17:02.313 UTC [common.tools.configtxgen] doOutputBlock -> INFO 006 Generating genesis block
2019-07-29 07:17:02.313 UTC [common.tools.configtxgen] doOutputBlock -> INFO 007 Writing genesis block
➜  first-network git:(release-1.4) ls channel-artifacts
genesis.block
```

以上命令是采用Solo共识算法创世块，如果使用**Raft**需要使用`-profile SampleMultiNodeEtcdRaft`选项：

命令：

```
configtxgen -profile SampleMultiNodeEtcdRaft -channelID byfn-sys-channel -outputBlock ./channel-artifacts/genesis.block
```

记录：

```
➜  first-network git:(release-1.4) configtxgen -profile SampleMultiNodeEtcdRaft -channelID byfn-sys-channel -outputBlock ./channel-artifacts/genesis.block
2019-07-29 08:44:18.348 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-29 08:44:18.444 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 002 orderer type: etcdraft
2019-07-29 08:44:18.444 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 Orderer.EtcdRaft.Options unset, setting to tick_interval:"500ms" election_tick:10 heartbeat_tick:1 max_inflight_blocks:5 snapshot_interval_size:20971520
2019-07-29 08:44:18.444 UTC [common.tools.configtxgen.localconfig] Load -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 08:44:18.552 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 005 orderer type: solo
2019-07-29 08:44:18.553 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 006 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 08:44:18.558 UTC [common.tools.configtxgen] doOutputBlock -> INFO 007 Generating genesis block
2019-07-29 08:44:18.559 UTC [common.tools.configtxgen] doOutputBlock -> INFO 008 Writing genesis block
```

### 生成创建应用通道的交易

网络启动后，只有1个系统通道，应用通道需要通过交易生成，这个交易（channel.tx）需要使用`configtxgen`工具创建，具体命令如下，`-outputCreateChannelTx`说明了是要生成创建应用通道的交易。

命令：

```
configtxgen -profile TwoOrgsChannel -outputCreateChannelTx ./channel-artifacts/channel.tx -channelID mychannel
```

记录：

```
➜  first-network git:(release-1.4) configtxgen -profile TwoOrgsChannel -outputCreateChannelTx ./channel-artifacts/channel.tx -channelID mychannel
2019-07-29 07:26:03.976 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-29 07:26:04.072 UTC [common.tools.configtxgen.localconfig] Load -> INFO 002 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:26:04.169 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 orderer type: solo
2019-07-29 07:26:04.169 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:26:04.169 UTC [common.tools.configtxgen] doOutputChannelCreateTx -> INFO 005 Generating new channel configtx
2019-07-29 07:26:04.172 UTC [common.tools.configtxgen] doOutputChannelCreateTx -> INFO 006 Writing new channel tx
➜  first-network git:(release-1.4)
➜  first-network git:(release-1.4) ls channel-artifacts
channel.tx  genesis.block
```

### 生成更新组织1的锚节点交易

组织节点加入到应用通道后，需要更新系统配置，把组织1的锚节点写入到配置块，这个也需要通过1笔交易完成。工具依然是`configtxgen`，`-outputAnchorPeersUpdate`表明了这是生成更新组织锚节点配置交易的操作。

命令：

```
configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org1MSPanchors.tx -channelID mychannel -asOrg Org1MSP
```

记录：

```
➜  first-network git:(release-1.4) configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org1MSPanchors.tx -channelID mychannel -asOrg Org1MSP
2019-07-29 07:30:26.456 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-29 07:30:26.557 UTC [common.tools.configtxgen.localconfig] Load -> INFO 002 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:30:26.640 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 orderer type: solo
2019-07-29 07:30:26.640 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:30:26.640 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 005 Generating anchor peer update
2019-07-29 07:30:26.641 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 006 Writing anchor peer update
➜  first-network git:(release-1.4)
➜  first-network git:(release-1.4) ls channel-artifacts
channel.tx  genesis.block  Org1MSPanchors.tx
```

### 生成更新组织2的锚节点交易

与上面类似，这是生成组织2锚节点配置的交易。

命令：

```
configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org2MSPanchors.tx -channelID mychannel -asOrg Org2MSP
```

记录：

```
➜  first-network git:(release-1.4) configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org2MSPanchors.tx -channelID mychannel -asOrg Org2MSP
2019-07-29 07:32:45.446 UTC [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-07-29 07:32:45.567 UTC [common.tools.configtxgen.localconfig] Load -> INFO 002 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:32:45.662 UTC [common.tools.configtxgen.localconfig] completeInitialization -> INFO 003 orderer type: solo
2019-07-29 07:32:45.662 UTC [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 004 Loaded configuration: /home/centos/go/src/github.com/hyperledger/fabric-samples/first-network/configtx.yaml
2019-07-29 07:32:45.662 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 005 Generating anchor peer update
2019-07-29 07:32:45.662 UTC [common.tools.configtxgen] doOutputAnchorPeersUpdate -> INFO 006 Writing anchor peer update
➜  first-network git:(release-1.4) ls ./channel-artifacts/
channel.tx  genesis.block  Org1MSPanchors.tx  Org2MSPanchors.tx
```

### 启动网络

启动网络涉及到docker容器的创建与启动，这部分不挨个手动执行，使用`byfn.sh`完成，这样可以完成fabric网络的启动，系统通道的启动也在这个阶段完成。

`byfn.sh`利用`scripts/script.sh`完成的从创建应用通道到调研合约、查询合约的过程，这部分继续手动执行，需要注释掉`byfn.sh`中的下面这行：

```
docker exec cli scripts/script.sh $CHANNEL_NAME $CLI_DELAY $LANGUAGE $CLI_TIMEOUT $VERBOSE $NO_CHAINCODE
```

然后执行：

```
./byfn.sh up
```

这样启动的是solo共识算法的网络，我启动的是raft共识的网络：

```
./byfn.sh up -o etcdraft
```

如果是solo，启动起来的容器与[快速启动你的第一个Fabric网络](#快速启动你的第一个Fabric网络)中的类似，只不过缺少3个链码容器。如果是raft应当是下面这样：

- 5个orderer节点，
- 4个peer节点
- 1个cli客户端

```
➜  first-network git:(r1.4-raft) ✗ docker ps
CONTAINER ID        IMAGE                               COMMAND             CREATED             STATUS              PORTS                      NAMES
fc0891e02afd        hyperledger/fabric-tools:latest     "/bin/bash"         26 seconds ago      Up 25 seconds                                  cli
9363a51d3f68        hyperledger/fabric-orderer:latest   "orderer"           29 seconds ago      Up 25 seconds       0.0.0.0:10050->7050/tcp    orderer4.example.com
7d9c13f964a5        hyperledger/fabric-orderer:latest   "orderer"           29 seconds ago      Up 25 seconds       0.0.0.0:7050->7050/tcp     orderer.example.com
e16a90f3f3fc        hyperledger/fabric-peer:latest      "peer node start"   29 seconds ago      Up 25 seconds       0.0.0.0:7051->7051/tcp     peer0.org1.example.com
4c7776287dc7        hyperledger/fabric-peer:latest      "peer node start"   29 seconds ago      Up 27 seconds       0.0.0.0:8051->8051/tcp     peer1.org1.example.com
aaeab5fdb418        hyperledger/fabric-orderer:latest   "orderer"           30 seconds ago      Up 27 seconds       0.0.0.0:11050->7050/tcp    orderer5.example.com
817a3ec7dd9d        hyperledger/fabric-peer:latest      "peer node start"   30 seconds ago      Up 27 seconds       0.0.0.0:10051->10051/tcp   peer1.org2.example.com
26524f34f654        hyperledger/fabric-peer:latest      "peer node start"   30 seconds ago      Up 27 seconds       0.0.0.0:9051->9051/tcp     peer0.org2.example.com
2485874c48d1        hyperledger/fabric-orderer:latest   "orderer"           30 seconds ago      Up 27 seconds       0.0.0.0:8050->7050/tcp     orderer2.example.com
5a8142d00432        hyperledger/fabric-orderer:latest   "orderer"           30 seconds ago      Up 28 seconds       0.0.0.0:9050->7050/tcp     orderer3.example.com
```

### 创建应用通道

连接cli发送创建mychannel的交易。

命令：

```
peer channel create -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/channel.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
```

记录：

```
➜  first-network git:(r1.4-raft) ✗ docker exec -it cli  /bin/bash
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls
channel-artifacts  crypto  scripts
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls channel-artifacts/
Org1MSPanchors.tx  Org2MSPanchors.tx  channel.tx  genesis.block
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel create -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/channel.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
2019-07-29 11:25:57.987 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-29 11:25:58.026 UTC [cli.common] readBlock -> INFO 002 Got status: &{NOT_FOUND}
2019-07-29 11:25:58.029 UTC [channelCmd] InitCmdFactory -> INFO 003 Endorser and orderer connections initialized
2019-07-29 11:25:58.231 UTC [cli.common] readBlock -> INFO 004 Got status: &{SERVICE_UNAVAILABLE}
2019-07-29 11:25:58.234 UTC [channelCmd] InitCmdFactory -> INFO 005 Endorser and orderer connections initialized
2019-07-29 11:25:58.436 UTC [cli.common] readBlock -> INFO 006 Got status: &{SERVICE_UNAVAILABLE}
2019-07-29 11:25:58.441 UTC [channelCmd] InitCmdFactory -> INFO 007 Endorser and orderer connections initialized
2019-07-29 11:25:58.643 UTC [cli.common] readBlock -> INFO 008 Got status: &{SERVICE_UNAVAILABLE}
2019-07-29 11:25:58.646 UTC [channelCmd] InitCmdFactory -> INFO 009 Endorser and orderer connections initialized
2019-07-29 11:25:58.848 UTC [cli.common] readBlock -> INFO 00a Got status: &{SERVICE_UNAVAILABLE}
2019-07-29 11:25:58.852 UTC [channelCmd] InitCmdFactory -> INFO 00b Endorser and orderer connections initialized
2019-07-29 11:25:59.053 UTC [cli.common] readBlock -> INFO 00c Got status: &{SERVICE_UNAVAILABLE}
2019-07-29 11:25:59.056 UTC [channelCmd] InitCmdFactory -> INFO 00d Endorser and orderer connections initialized
2019-07-29 11:25:59.260 UTC [cli.common] readBlock -> INFO 00e Received block: 0
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#
```

#### 确认应用通道创建成功

连接orderer查看mychannel是否创建，可以看到已经存在mychannel目录，证明mychannel已创建。

命令：

```
ls /var/hyperledger/production/orderer/chains/mychannel/
```

记录：

```
➜  ~ docker exec -it orderer.example.com bash
root@7d9c13f964a5:/opt/gopath/src/github.com/hyperledger/fabric# ls
root@7d9c13f964a5:/opt/gopath/src/github.com/hyperledger/fabric# ls /var/hyperledger/production/orderer/chains/mychannel/
blockfile_000000
```

### 加入应用通道

从cli上可以发起peer0.org1加入mychannel的交易请求，方法是通过让`peer channel join`读取环境变量信息，环境变量决定了当前为哪个peer进行处理。

`CORE_PEER*`相关的环境变量，代表了所有和peer相关的配置信息：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# env | grep "CORE_PEER"
CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
CORE_PEER_TLS_KEY_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/server.key
CORE_PEER_LOCALMSPID=Org1MSP
CORE_PEER_TLS_CERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/server.crt
CORE_PEER_TLS_ENABLED=true
CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
CORE_PEER_ID=cli
CORE_PEER_ADDRESS=peer0.org1.example.com:7051
```

切换peer时，只需修改以下4个环境变量，它们代表当前是哪个peer，以及peer的配置，其他环境变量通用：

- CORE_PEER_LOCALMSPID
- CORE_PEER_TLS_ROOTCERT_FILE
- CORE_PEER_MSPCONFIGPATH
- CORE_PEER_ADDRESS，最易分辨当前是在为哪个peer操作，比如默认是peer0.org1

以下为加入mychannel和列出当前peer(peer0.org1)所加入的通道：

命令：

```
peer channel join -b mychannel.block
peer channel list
```

记录：

```
➜  first-network git:(r1.4-raft) ✗ docker exec -it cli  /bin/bash
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls
channel-artifacts  crypto  mychannel.block  scripts
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel join -b mychannel.block
2019-07-29 11:38:30.638 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-29 11:38:30.719 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel list
2019-07-29 11:45:29.692 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
Channels peers has joined:
mychannel
```

也可以登录peer0.org1去查看peer加入的通道：

```
➜  ~ docker exec -it peer0.org1.example.com bash
root@e16a90f3f3fc:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel list
2019-07-29 11:59:51.415 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
Channels peers has joined:
mychannel
```


> 没有命令能够查看某个通道所有的peer。

peer0.org1重复加入会发起proposal失败：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel join -b mychannel.block
2019-07-29 11:58:25.746 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
Error: proposal failed (err: bad proposal response 500: cannot create ledger from genesis block: LedgerID already exists)
```

修改环境变量的规则见`fabric-samples/first-network/scripts/utils.sh`中的`setGloabls`函数。以下是peer1.org0加入mychanel:

```
CORE_PEER_LOCALMSPID="Org1MSP"
CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
CORE_PEER_ADDRESS=peer1.org1.example.com:8051
# 执行加入通道
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel join -b mychannel.block
2019-07-29 12:01:20.752 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-29 12:01:20.832 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
```

#### 确认peer加入的应用通道和数据

登录peer1.org1确认已经加入mychanel，以及同步到了mychannel上的链数据：

```
➜  ~ docker exec -it peer1.org1.example.com bash
root@4c7776287dc7:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel list
2019-07-29 12:02:48.662 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
Channels peers has joined:
mychannel
root@4c7776287dc7:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls /var/hyperledger/production/ledgersData/chains/chains/mychannel/blockfile_000000
/var/hyperledger/production/ledgersData/chains/chains/mychannel/blockfile_000000
```

### 更新锚节点配置

使用cli更新peer1.org1的锚节点配置：

> 因为上一步操作环境变量已经修改成peer1.org1的，所以，就直接让peer1.org1做锚节点好了。

命令：

```
peer channel update -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/Org1MSPanchors.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
```

记录：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel update -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/Org1MSPanchors.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
2019-07-29 12:05:12.585 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-29 12:05:12.609 UTC [channelCmd] update -> INFO 002 Successfully submitted channel update
```

### 安装链码

使用cli为peer1.org1安装链码，安装链码是把链码源码打包和拷贝到peer节点的文件系统上，具体见[快速入门Fabric核心概念和框架：安装链码](http://lessisbetter.site/2019/07/25/fabric-concepts-notes/#安装链码)。

安装命令为`peer channel isntall`，包含了以下参数：

- `-n mycc`：链码名称
- `-v 1.0`：链码版本
- `-l golang`：链码语言
- `-p github.com/chaincode/chaincode_example02/go/`：本地链码代码所在路径，从`$GOPATH/src`下开始搜索。

更多选项见`peer chaincode install -h`。

命令：

```
peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
```

记录：

```
# 查看链码源码
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls ../../../../github.com/chaincode/chaincode_example02/go/
chaincode_example02.go
# 安装链码
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
2019-07-30 02:09:10.516 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-30 02:09:10.516 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-07-30 02:09:10.800 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
```

#### 查看安装的链码

2种方式。

1、在cli上执行查询：

命令：

```
peer chaincode list --installed
```

记录：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode list --installed
Get installed chaincodes on peer:
Name: mycc, Version: 1.0, Path: github.com/chaincode/chaincode_example02/go/, Id: 476fca1a949274001971f1ec2836cb09321f0b71268b3762d68931c93f218134
```

2、登录到peer1.org1上查询链码文件：

命令：

```
ls /var/hyperledger/production/chaincodes
```

记录：

```
root@4c7776287dc7:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls /var/hyperledger/production/chaincodes/mycc.1.0
/var/hyperledger/production/chaincodes/mycc.1.0
```

#### 链码安装过程

也可以查看peer1.org1安装链码的日志：

```
➜  ~ docker logs peer1.org1.example.com
...省略老日志
2019-07-30 02:09:10.796 UTC [endorser] callChaincode -> INFO 04b [][876f7f14] Entry chaincode: name:"lscc"
2019-07-30 02:09:10.799 UTC [lscc] executeInstall -> INFO 04c Installed Chaincode [mycc] Version [1.0] to peer
2019-07-30 02:09:10.799 UTC [endorser] callChaincode -> INFO 04d [][876f7f14] Exit chaincode: name:"lscc"  (2ms)
2019-07-30 02:09:10.799 UTC [comm.grpc.server] 1 -> INFO 04e unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:35232 grpc.code=OK grpc.call_duration=3.276308ms
2019-07-30 02:10:51.409 UTC [endorser] callChaincode -> INFO 04f [][9db45293] Entry chaincode: name:"lscc"
2019-07-30 02:10:51.411 UTC [endorser] callChaincode -> INFO 050 [][9db45293] Exit chaincode: name:"lscc"  (2ms)
2019-07-30 02:10:51.411 UTC [comm.grpc.server] 1 -> INFO 051 unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:35240 grpc.code=OK grpc.call_duration=2.667734ms
```

### 部署链码

实例化链码也成部署链码，鉴于少1个字，下文使用部署链码。

通过cli部署链码，由于之前设置的环境变量，部署等价于由peer1.org1触发。

在一个通道上，链码只需部署1次，所以无需每个peer都去部署链码。部署链码实际是一笔部署交易，该交易的结果就是部署链码容器。

部署命令是`peer chaincode instantiate`，需要使用以下标记：

- `-o orderer.example.com:7050`：指定要连接的orderer节点
- `--tls true`：开启TLS验证
- `--cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem`：使用的CA证书文件，注意使用的是orderer的证书
- `-C mychannel`：在哪个通道上部署
- `-n mycc`：链码名称
- `-l golang`：链码语言
- `-v 1.0`：链码版本
- `-c '{"Args":["init","a","100","b","200"]}'`：链码的构建过程消息，JSON格式，调用`init`函数，设置a和b的值
- `-P 'AND ('\''Org1MSP.peer'\'','\''Org2MSP.peer'\'')'`：指定背书策略，必须由org1和org2同时背书


命令：

```
peer chaincode instantiate -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc -l golang -v 1.0 -c '{"Args":["init","a","100","b","200"]}' -P 'AND ('\''Org1MSP.peer'\'','\''Org2MSP.peer'\'')'
```


部署和快速查询如下：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode instantiate -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc -l golang -v 1.0 -c '{"Args":["init","a","100","b","200"]}' -P 'AND ('\''Org1MSP.peer'\'','\''Org2MSP.peer'\'')'
2019-07-30 02:18:57.119 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-30 02:18:57.119 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode list --instantiated -C "mychannel"
Get instantiated chaincodes on channel mychannel:
Name: mycc, Version: 1.0, Path: github.com/chaincode/chaincode_example02/go/, Escc: escc, Vscc: vscc
```

#### 查看部署的链码

链码部署后，会启动链码容器，可以查看：

```
➜  ~ docker ps
CONTAINER ID        IMAGE                                                                                                  COMMAND                  CREATED             STATUS              PORTS                      NAMES
8bab025e153e        dev-peer1.org1.example.com-mycc-1.0-cd123150154e6bf2df7ce682e0b1bcbea40499416f37a6da3aae14c4eb51b08d   "chaincode -peer.add…"   11 minutes ago      Up 11 minutes                                  dev-peer1.org1.example.com-mycc-1.0
```

查看链码容器日志：

```
➜  ~ docker logs dev-peer1.org1.example.com-mycc-1.0
ex02 Init
Aval = 100, Bval = 200
```

#### 部署链码的过程

可以通过peer1.org1的日志查看：

1. 背书
1. 生成Docker构建镜像：GenerateDockerBuild
1. 接收到区块2（前面一步必然被orderer打包了）
1. 部署链码：HandleStateUpdates
1. 提交区块2

```
2019-07-30 02:17:46.522 UTC [endorser] callChaincode -> INFO 052 [mychannel][1c8a3567] Entry chaincode: name:"lscc"
2019-07-30 02:17:46.526 UTC [endorser] callChaincode -> INFO 053 [mychannel][1c8a3567] Exit chaincode: name:"lscc"  (3ms)
2019-07-30 02:17:46.527 UTC [comm.grpc.server] 1 -> INFO 054 unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:35248 grpc.code=OK grpc.call_duration=6.246381ms
2019-07-30 02:18:57.122 UTC [endorser] callChaincode -> INFO 055 [mychannel][5059d46e] Entry chaincode: name:"lscc"
2019-07-30 02:18:57.141 UTC [chaincode.platform.golang] GenerateDockerBuild -> INFO 056 building chaincode with ldflagsOpt: '-ldflags "-linkmode external -extldflags '-static'"'
2019-07-30 02:19:12.363 UTC [endorser] callChaincode -> INFO 057 [mychannel][5059d46e] Exit chaincode: name:"lscc"  (15240ms)
2019-07-30 02:19:12.363 UTC [comm.grpc.server] 1 -> INFO 058 unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:35252 grpc.code=OK grpc.call_duration=15.242059303s
2019-07-30 02:19:14.462 UTC [gossip.privdata] StoreBlock -> INFO 059 [mychannel] Received block [2] from buffer
2019-07-30 02:19:14.464 UTC [committer.txvalidator] Validate -> INFO 05a [mychannel] Validated block [2] in 2ms
2019-07-30 02:19:14.464 UTC [cceventmgmt] HandleStateUpdates -> INFO 05b Channel [mychannel]: Handling deploy or update of chaincode [mycc]
2019-07-30 02:19:14.503 UTC [kvledger] CommitWithPvtData -> INFO 05c [mychannel] Committed block [2] with 1 transaction(s) in 38ms (state_validation=0ms block_and_pvtdata_commit=16ms state_commit=6ms)
2019-07-30 02:20:41.569 UTC [endorser] callChaincode -> INFO 05d [mychannel][3d51a2d1] Entry chaincode: name:"lscc"
2019-07-30 02:20:41.571 UTC [endorser] callChaincode -> INFO 05e [mychannel][3d51a2d1] Exit chaincode: name:"lscc"  (2ms)
2019-07-30 02:20:41.571 UTC [comm.grpc.server] 1 -> INFO 05f unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:35260 grpc.code=OK grpc.call_duration=2.998184ms
```

### 查询链码

链码查询的命令是`peer chaincode query`，需要指定通道以及链码，最后是调用参数。

如果key存在可以查询到正确的值，如果key不存在，查询结果提示Error。

命令：

```
peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
```

记录：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
100
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","b"]}'
200
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","c"]}'
Error: endorsement failure during query. response: status:500 message:"{\"Error\":\"Nil amount for c\"}"
```

1次查询操作，链码容器的日志会是这样，可以看到触发Invoke，然后是Query Response，并不是真正去Invoke：

```
ex02 Invoke
Query Response:{"Name":"a","Amount":"100"}
```

### 调用链码

调用链码是一笔调用交易，需要：

- 指定orderer节点
- 使用TLS、指定orderer的CA证书
- 指定哪个通道的，哪个链码
- 通过peerAddresses指定背书的peer，以及要使用的证书

只有当背书策略满足要求时，调用交易才会判断为有效，然后修改链码容器内的数据。


#### 不满足背书策略的调用交易

以下为无效的调用交易，因为只指定了peer1.org1进行背书，而mycc的背书策略要求org1和org2的2个peer同时背书才行。

命令：

```
peer chaincode invoke -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc --peerAddresses peer1.org1.example.com:8051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer1.org1.example.com/tls/ca.crt  -c '{"Args":["invoke","a","b","10"]}'
```

> `-c '{"Args":["invoke","a","b","10"]}'`指调用链码的invoke函数，参数为a, b和10，含义是对把a和b的值分别修改为a-10，b+10，具体操作可以见源码：
> fabric-samples/chaincode/chaincode_example02/go/chaincode_example02.go。

链码容器日志如下，可以看到触发了Invoke，值进行了变更。

```
ex02 Invoke
Aval = 90, Bval = 210
```

通过查询命令可以发现链码数据并未改变，因为交易proposal不满足背书策略，cli不会发起交易给orderer，数据不会提交。

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
100
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","b"]}'
200
```

#### 有效的调用交易

之前安装链码时，只在peer1.org1进行了安装，但背书要求org2的节点也要进行背书，背书节点需要已经安装链码，否则无法进行背书，会返回错误的背书响应：

```
Error: endorsement failure during invoke. response: status:500 message:"cannot retrieve package for chaincode mycc/1.0, error open /var/hyperledger/production/chaincodes/mycc.1.0: no such file or directory"
```

本文选择peer1.org2，先让它加入mychannel，然后安装链码，详细过程见[加入应用通道](#加入应用通道)和[安装链码](#安装链码)。

```
# 设置环境变量
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# CORE_PEER_LOCALMSPID="Org2MSP"
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org2.example.com/peers/peer1.org2.example.com/tls/ca.crt
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# CORE_PEER_ADDRESS=peer1.org2.example.com:10051
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#

# 加入mychannel
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel join -b mychannel.block
2019-07-30 03:45:39.637 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-30 03:45:39.731 UTC [channelCmd] executeJoin -> INFO 002 Successfully submitted proposal to join channel
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel list
2019-07-30 03:46:09.910 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
Channels peers has joined:
mychannel
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#

# 设置org2的锚节点
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel update -o orderer.example.com:7050 -c mychannel -f ./channel-artifacts/Org2MSPanchors.tx --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
2019-07-30 03:47:27.412 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-07-30 03:47:27.447 UTC [channelCmd] update -> INFO 002 Successfully submitted channel update
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer#

# 安装链码
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode install -n mycc -v 1.0 -l golang -p github.com/chaincode/chaincode_example02/go/
2019-07-30 03:48:18.903 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 001 Using default escc
2019-07-30 03:48:18.903 UTC [chaincodeCmd] checkChaincodeCmdParams -> INFO 002 Using default vscc
2019-07-30 03:48:19.180 UTC [chaincodeCmd] install -> INFO 003 Installed remotely response:<status:200 payload:"OK" >
```

之前已经实例化过1链码，所以无需再次实例化。

接下来重新执行调用链码，并且制定2个背书节点，分别是peer1.org1和peer1.org2。背书启用了TLS，需要在`--peerAddresses`后面，使用`--tlsRootCertFiles`指定对应peer的证书文件，使用`--cafile`指定orderer的证书文件。

命令：

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode invoke -o orderer.example.com:7050 --tls true --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n mycc --peerAddresses peer1.org1.example.com:8051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer1.org1.example.com/tls/ca.crt --peerAddresses peer1.org2.example.com:10051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org2.example.com/peers/peer1.org2.example.com/tls/ca.crt -c '{"Args":["invoke","a","b","10"]}'
2019-07-30 03:52:53.880 UTC [chaincodeCmd] chaincodeInvokeOrQuery -> INFO 001 Chaincode invoke successful. result: status:200
```


可以通过命令查询到，链码中的数据已经更新到最新，说明调用链码成功。

```
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}'
90
root@fc0891e02afd:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer chaincode query -C mychannel -n mycc -c '{"Args":["query","b"]}'
210
```

链码容器的日志可以看到Invoke的日志：

```
ex02 Invoke
Aval = 90, Bval = 210
```

### 链码FAQ

执行完上面的操作，你是否有这2个疑问：

1. 有2个背书节点，不应该2个背书节点都Invoke吗，为什么链码容器日志只看到1次Invoke？
2. 背书节点Invoke链码容器时，链码容器的数据并不会提交，链码容器里的数据是什么时候更新的？

#### 疑问1解答

> 有2个背书节点，不应该2个背书节点都Invoke吗，为什么链码容器日志只看到1次Invoke？

每个组织进行背书，都必须部署自己的链码容器，背书时通过gRPC和自己组织的链码容器交互，所以上面查看链码容器`dev-peer1.org1.example.com-mycc-1.0`日志的时候，只看到1次Invoke，另外1次，在org2的链码容器`dev-peer1.org2.example.com-mycc-1.0`日志里。

在[有效的调用交易](#有效的调用交易)这一节，我们只安装了链码，因为**在某个通道内，链码只需部署1次**，并且之前peer1.org1已经发送了**部署交易**，所以无需再发送部署交易。

```
➜  ~ docker ps
CONTAINER ID        IMAGE                                                                                                  COMMAND                  CREATED             STATUS              PORTS                      NAMES
0700ebc80246        dev-peer1.org2.example.com-mycc-1.0-26c2ef32838554aac4f7ad6f100aca865e87959c9a126e86d764c8d01f8346ab   "chaincode -peer.add…"   3 hours ago         Up 3 hours                                     dev-peer1.org2.example.com-mycc-1.0
8bab025e153e        dev-peer1.org1.example.com-mycc-1.0-cd123150154e6bf2df7ce682e0b1bcbea40499416f37a6da3aae14c4eb51b08d   "chaincode -peer.add…"   4 hours ago         Up 4 hours                                     dev-peer1.org1.example.com-mycc-1.0
```

这里有一点需要注意，当org2的背书节点进行背书时，发现没有链码容器，会自动创建，而不是安装链码后，即可主动部署链码容器，可以从peer1.org2的日志确认以上流程。


```
# 安装链码
2019-07-30 03:48:19.177 UTC [endorser] callChaincode -> INFO 063 [][353ca5ab] Entry chaincode: name:"lscc"
2019-07-30 03:48:19.179 UTC [lscc] executeInstall -> INFO 064 Installed Chaincode [mycc] Version [1.0] to peer
2019-07-30 03:48:19.179 UTC [endorser] callChaincode -> INFO 065 [][353ca5ab] Exit chaincode: name:"lscc"  (2ms)
2019-07-30 03:48:19.179 UTC [comm.grpc.server] 1 -> INFO 066 unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:38546 grpc.code=OK grpc.call_duration=2.758068ms

# 12s后才部署链码容器
2019-07-30 03:52:37.932 UTC [endorser] callChaincode -> INFO 067 [mychannel][6b87148b] Entry chaincode: name:"mycc"
2019-07-30 03:52:37.948 UTC [chaincode.platform.golang] GenerateDockerBuild -> INFO 068 building chaincode with ldflagsOpt: '-ldflags "-linkmode external -extldflags '-static'"'
2019-07-30 03:52:53.875 UTC [endorser] callChaincode -> INFO 069 [mychannel][6b87148b] Exit chaincode: name:"mycc"  (15943ms)
2019-07-30 03:52:53.876 UTC [comm.grpc.server] 1 -> INFO 06a unary call completed grpc.service=protos.Endorser grpc.method=ProcessProposal grpc.peer_address=172.28.0.11:38984 grpc.code=OK grpc.call_duration=15.945466965s
```

#### 疑问2解答

> 背书节点Invoke链码容器时，链码容器的数据并不会提交，链码容器里的数据是什么时候更新的？

链码容器只是负责执行调用，不负责存储数据，所以不存在链码容器数据何时更新的问题。

下面是调用链码的流程图，可以看到链码执行时，是通过Shim从fabric账本读取数据的，然后把执行结果返回。如果交易被peer节点验证有效，调用交易的结果会写入当fabric账本，如果无效，不会改变fabric账本，所以你现在是否理解[不满足背书策略的调用交易](#不满足背书策略的调用交易)不会改变数据，而[有效的调用交易](#有效的调用交易)会改变数据。

![](http://img.lessisbetter.site/2019-07-chaincode_swimlane.png)

## 启动自定义网络


### 利用byfn启动自定义网络

`./byfn.sh`不止`up`和`down`2个命令，还有其他命令，以及更多的参数，比如restart, generate和upgrade。

在上一节，使用了完全默认的参数，启动了网络，这是完全傻瓜式的。基于对fabric的掌握，还可以设置更多的参数，比如使用参数可以指定channel名称，而不是使用默认的`mychannel`，可以设置超时时间，使用指定docker编排文件创建各容器，指定chaincode的语言是Go还是Java等，还有更多的参数自己探索吧，设置一些参数重新启动网络。


```
➜  first-network git:(release-1.4) ./byfn.sh help
Usage:
  byfn.sh <mode> [-c <channel name>] [-t <timeout>] [-d <delay>] [-f <docker-compose-file>] [-s <dbtype>] [-l <language>] [-o <consensus-type>] [-i <imagetag>] [-a] [-n] [-v]
    <mode> - one of 'up', 'down', 'restart', 'generate' or 'upgrade'
      - 'up' - bring up the network with docker-compose up
      - 'down' - clear the network with docker-compose down
      - 'restart' - restart the network
      - 'generate' - generate required certificates and genesis block
      - 'upgrade'  - upgrade the network from version 1.3.x to 1.4.0
    -c <channel name> - channel name to use (defaults to "mychannel")
    -t <timeout> - CLI timeout duration in seconds (defaults to 10)
    -d <delay> - delay duration in seconds (defaults to 3)
    -f <docker-compose-file> - specify which docker-compose file use (defaults to docker-compose-cli.yaml)
    -s <dbtype> - the database backend to use: goleveldb (default) or couchdb
    -l <language> - the chaincode language: golang (default) or node
    -o <consensus-type> - the consensus-type of the ordering service: solo (default), kafka, or etcdraft
    -i <imagetag> - the tag to be used to launch the network (defaults to "latest")
    -a - launch certificate authorities (no certificate authorities are launched by default)
    -n - do not deploy chaincode (abstore chaincode is deployed by default)
    -v - verbose mode
  byfn.sh -h (print this message)

Typically, one would first generate the required certificates and
genesis block, then bring up the network. e.g.:

	byfn.sh generate -c mychannel
	byfn.sh up -c mychannel -s couchdb
        byfn.sh up -c mychannel -s couchdb -i 1.4.0
	byfn.sh up -l node
	byfn.sh down -c mychannel
        byfn.sh upgrade -c mychannel

Taking all defaults:
	byfn.sh generate
	byfn.sh up
	byfn.sh down
```

## 总结

通过这篇文章能够掌握部署一个Fabric网络需哪些步骤，以及各步骤需要做哪些工作。但这篇文章，缺少了关于docker配置各容器的部分，后面会单独一篇文章介绍。

