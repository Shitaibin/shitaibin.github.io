---
title: Fabric组织动态加入
date: 2019-08-01 20:33:48
tags: ['区块链', 'Fabric']
---


联盟链中动态加入组织是很正常的一件事，但联盟链不会像公链那样，可以自由加入和退出，所以，加入是要费一般功夫的。

需要做以下几件事情：

1. 生成新组织的证书和在要加入通道中的配置
1. 拉取要加入通道的配置，根据新组织通道中的配置和通道配置，最终生成更新通道配置的交易，pb格式
1. 根据通道配置更新策略，让组织节点对交易签名，然后发送更新配置交易到排序节点，并打包上链
1. 新组织利用通道创世块加入通道
1. 可选：新组织设置本组织在通道中的锚节点


## 生成org3的证书和在通道中的配置

生成新组织的证书，结果在当前目录下生成`crypto-config`。

```
cryptogen generate --config=./org3-crypto.yaml
```

当前目录下有`configtx.yaml`，里面是新组织的配置，利用configtxgen生成更新配置的json文件，放到channel的配置文件。

```
export FABRIC_CFG_PATH=$PWD
configtxgen -printOrg Org3MSP > ../channel-artifacts/org3.json
```

## 拉取最新通道配置

连接cli，修改环境变量，设置Orederer的CA以及通道名称，后续操作会使用

```
docker exec -it cli bash
export ORDERER_CA=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export CHANNEL_NAME=mychannel
```

拉取当前的配置块，它会把cahnnel的配置，保存到二进制的protobuf文件`config_block.pb`，保存在当前目录，这个命令默认会拉去最新的配置：


```
peer channel fetch config config_block.pb -o orderer.example.com:7050 -c $CHANNEL_NAME --tls --cafile $ORDERER_CA
```

`peer channel fetch config`可以确保获取最新的配置区块，`config_block.pb`实际是个区块，上述命令日志的**最后一行**，会显示出当前获取的是哪个区块：

```
2019-07-30 09:40:53.047 UTC [msp] GetDefaultSigningIdentity -> DEBU 044 Obtaining default signing identity
2019-07-30 09:40:53.047 UTC [msp] GetDefaultSigningIdentity -> DEBU 045 Obtaining default signing identity
2019-07-30 09:40:53.047 UTC [msp.identity] Sign -> DEBU 046 Sign: plaintext: 0AED060A1508051A0608A5A180EA0522...3849120C0A041A02080212041A020802
2019-07-30 09:40:53.047 UTC [msp.identity] Sign -> DEBU 047 Sign: digest: 2202E1BA573DD47D5F54FA5E022F1ABD78B1DCDBB9CA10C5843A675C031CDAD8
2019-07-30 09:40:53.049 UTC [cli.common] readBlock -> INFO 048 Received block: 2
```


在byfn中，已经做了几次更改：
1. 区块0：使用应用通道创世块创建应用通道
1. 区块1：更新org1的锚节点
1. 区块2：更新org2的锚节点

所以，通过上诉命令，得到了区块2中保持的配置。

需要把protobuf文件转换为人可读的JSON配置，configtxlator把protobuf转换为JSON，jq是一个处理JSON的工具，这里是把配置相关的数据读出来，存到config.json中，因为配置块里不仅仅包含配置：

```
configtxlator proto_decode --input config_block.pb --type common.Block | jq .data.data[0].payload.data.config > config.json
```

配置文件内容700+行，此处省略，具体可看这[利用工具解析fabric区块：应用通道创世块](http://lessisbetter.site/2019/08/01/fabric-parse-block/#%E5%BA%94%E7%94%A8%E9%80%9A%E9%81%93%E5%88%9B%E4%B8%96%E5%9D%97)。



## 利用通道配置和org3配置生成更新通道的配置

config.json中包含了各组织的信息，已经包含了org1和org2的，现在要把org3.json加入到config.json中：

```
jq -s '.[0] * {"channel_group":{"groups":{"Application":{"groups": {"Org3MSP":.[1]}}}}}' config.json ./channel-artifacts/org3.json > modified_config.json
```

上面的命令类似格式化输出，`-s`指定了格式，`.[0]，.[1]`代表了第1个参数和第2个参数，效果就是增加了更org1、org2平级的org3的配置，然后保存到新的配置文件`modified_config.json`，可以使用diff对比。

```
diff config.json modified_config.json
>           },
>           "Org3MSP": {
>             "groups": {},
>             "mod_policy": "Admins",
...
>               }
>             },
>             "version": "0"
```

接下来要做3件事：

1. config.json -> config.pb
1. modified_config.json -> modified_config.pb
1. modified_config.pb - config.pb -> org3_update.pb

目的是利用pb类型的配置文件的差集，生成升级配置的配置文件`org3_update.pb`。

```
configtxlator proto_encode --input config.json --type common.Config --output config.pb
configtxlator proto_encode --input modified_config.json --type common.Config --output modified_config.pb
configtxlator compute_update --channel_id $CHANNEL_NAME --original config.pb --updated modified_config.pb --output org3_update.pb
```

然而，`org3_update.pb`也不是能直接用来升级的，但是距离升级又进了一步，再在它外面封装一层，就可以用来升级了。但是，封装这一层，需要使用json来处理，所以需要把`org3_update.pb`转为json格式，封装完成，再转为pb格式。

```
configtxlator proto_decode --input org3_update.pb --type common.ConfigUpdate | jq . > org3_update.json
echo '{"payload":{"header":{"channel_header":{"channel_id":"mychannel", "type":2}},"data":{"config_update":'$(cat org3_update.json)'}}}' | jq . > org3_update_in_envelope.json
configtxlator proto_encode --input org3_update_in_envelope.json --type common.Envelope --output org3_update_in_envelope.pb
```

`org3_update_in_envelope.pb`就是用来升级的。

> 搞了这么一大圈，怎么不用modified_config.json和config.json直接来生成org3_update.json？

## 对更新配置进行签名

通道的默认修改策略是MAJORITY，即需要多数的org的Admin账号进行签名。

因为cli中的环境变量就是设置的org1 admin的，所以可以直接签名：

```
peer channel signconfigtx -f org3_update_in_envelope.pb
```

导出org2的环境变量设置，然后重新执行签名命令：

```
export CORE_PEER_LOCALMSPID="Org2MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
export CORE_PEER_ADDRESS=peer0.org2.example.com:9051
```

> 签名的结果在哪？就在pb文件里。


## 发送更新通道配置的交易


```
peer channel update -f org3_update_in_envelope.pb -c $CHANNEL_NAME -o orderer.example.com:7050 --tls --cafile $ORDERER_CA
```

交易提交成功：

```
2019-07-31 06:17:58.376 UTC [channelCmd] update -> INFO 04d Successfully submitted channel update
```

## 配置选举以接收区块

新加入的组织节点只能使用genesis区块启动，创世块不包含他们已经加入到通道的配置，所以它们无法利用gossip验证它们从本组织其他peer发来的区块，直到他们接收到了它们加入通道的配置交易。所以新加入的节点必须，配置它们从哪接收区块的排序服务。

如果利用的静态leader模式，使用如下配置：

```
CORE_PEER_GOSSIP_USELEADERELECTION=false
CORE_PEER_GOSSIP_ORGLEADER=true
```

否则如果是动态leader，使用如下配置：

```
CORE_PEER_GOSSIP_USELEADERELECTION=true
CORE_PEER_GOSSIP_ORGLEADER=false
```

这样新组织的peer都宣称自己是leader，加速了获取区块，等他们接收到它们自己的配置交易，就会只有1个leader peer代表本组织。

## 启动新组织节点

### 启动容器

指定组织的compose文件，启动组织的容器。这会创建3个容器，peer1.org3, peer2.org3和org3cli，其中org3cli是为org3特制的cli，里面已经设置好了org3的环境变量。

```
docker-compose -f docker-compose-org3.yaml up -d
```

后续都是连接到org3cli进行操作。

设置orderer的信息。

```
export ORDERER_CA=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem && export CHANNEL_NAME=mychannel
```

### 拉取mychannel的创世块

`peer channel fetch 0`指拉去0号区块，也就是mychannel的创世区块，保存到mychannel.block。

```
peer channel fetch 0 mychannel.block -o orderer.example.com:7050 -c $CHANNEL_NAME --tls --cafile $ORDERER_CA
```

### 加入通道

```
peer channel join -b mychannel.block
```

### 设置新组织锚节点

设置锚节点也需要更新通道配置，但流程与初始的锚节点不太一致，因为新组织的配置不在`configtx.yanml`中，设置新组织锚节点跟添加新组织的流程一样，具体见：
[Updating the Channel Config to include an Org3 Anchor Peer (Optional)](https://hyperledger-fabric.readthedocs.io/en/release-1.4/channel_update_tutorial.html?highlight=eyfn#updating-the-channel-config-to-include-an-org3-anchor-peer-optional)。

## 参考资料

1. [官方文档](https://hyperledger-fabric.readthedocs.io/en/release-1.4/channel_update_tutorial.html?highlight=eyfn)
1. [first network项目中的eyfn](https://github.com/hyperledger/fabric-samples/blob/release-1.4/first-network/eyfn.sh)，运行脚本可以看到具体流程。