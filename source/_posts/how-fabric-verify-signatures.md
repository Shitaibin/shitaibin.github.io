---
title: Fabric 1.4源码解读 5：Fabric是如何验证签名的？
date: 2019-11-10 21:23:36
tags: ['Fabric', '区块链']
---

## 理论知识

如果不清楚数字证书、公私钥与签名的关系，建议阅读阮一峰的[数字签名是什么？](https://www.ruanyifeng.com/blog/2011/08/what_is_a_digital_signature.html)。


## Fabric证书和密钥文件

使用Fabric CA或者 cryptogen 工具可以生成证书和私钥文件，这里取 BYFN 例子的文件做介绍，Org1 Admin 账户的文件如下：

```
➜  first-network git:(release-1.4) ✗ tree crypto-config/peerOrganizations/org1.example.com/users/Admin@org1.example.com
crypto-config/peerOrganizations/org1.example.com/users/Admin@org1.example.com
├── msp
│   ├── admincerts
│   │   └── Admin@org1.example.com-cert.pem
│   ├── cacerts
│   │   └── ca.org1.example.com-cert.pem
│   ├── keystore
│   │   └── f9f3dddb7fcc40086de6d5ae77f1481abbb99bff7a74839b950720d3dca0d8ee_sk
│   ├── signcerts
│   │   └── Admin@org1.example.com-cert.pem
│   └── tlscacerts
│       └── tlsca.org1.example.com-cert.pem
└── tls
    ├── ca.crt
    ├── client.crt
    └── client.key
```

msp目录，为Admin的身份信息：
- admincerts：组织管理员的身份验证证书。
- cacerts：组织的根证书。
- keystore：该用户的私钥，用来对消息签名。
- signcerts：该用户的身份验证证书，被组织根证书签名。
- tlscacerts：TLS通信用的身份证书，为组织的TLS证书。

tls目录，为TLS通信相关的证书：
- ca.crt：组织根证书
- client.crt：验证当前用户身份的证书，当前为验证管理员的证书
- client.key：当前用户的身份私钥，用来签名


## 整体逻辑

交易是区块链的核心，一切状态的转移都是一条交易，交易的真伪需要使用数字签名进行保证。

在Fabric中，交易涉及两个概念：
- Proposal：提案
- Transaction：交易

所以 Proposal 和 Transaction 都需要使用数字签名进行保护，它们相关的消息中，都包含了发送方的身份信息：mspid、证书（证书中实际包含了公钥）。

提案的实际消息是 SignedProposal，其中包含了：
- 数字签名：Signature
- 证书、公钥等签名者身份信息：ProposalBytes.Proposal.Header.SignatureHeader.Creator

![signed_proposal](http://img.lessisbetter.site/2019-11-signed_proposal.png)
> 图来自杨保华的[hyperledger_code_fabric](https://github.com/yeasy/hyperledger_code_fabric) 。

交易中最重要的是Envelope结构体，SDK向Orderer提交交易时，会发送Envelope消息，它包含了：
- 数字签名：Signature
- 交易发送方的身份信息：Payload.Header.SignatureHeader.Creator
- 可选背书节点的身份信息，不同的交易类型，Data包含了不同的信息，如果是需要背书的，可以包含背书的信息、签名和身份信息：Payload.Data.SignedChainccodeDeploymentSpec.OwnerEndorsements.signingidentity

![Signed transaction](http://img.lessisbetter.site/2019-11-tx_envelop.jpeg)
> 图来自《区块链原理、设计与应用》，为升级链码的交易Envelope结构。

在验证消息的签名时，会从中提取出数字签名Signature，身份信息（证书、公钥）和被签名消息体，完成以下验证：
- 使用证书验证发送方的身份，发送方是否属于它所在的组织，以及发送方的公钥没有修改和替换
- 使用公钥验证消息是否为发送方签名，并且消息没有被修改

验证的整体流程如下：

![Verify signature](http://img.lessisbetter.site/2019-11-verify-signature.png)

## 验证签名的函数

`core/common/validation/msgvalidation.go` 提供了2验证消息签名的函数，用来验证Proposal和Transaction，它们会调用相同的函数`checkSignatureFromCreator`进行数字签名的验证。


### 验证Porposal签名

```go
func ValidateProposalMessage(signedProp *pb.SignedProposal) (*pb.Proposal, *common.Header, *pb.ChaincodeHeaderExtension, error) {
  ...

	// 从SignatureHeader交易客户端的签名
	// validate the signature
	err = checkSignatureFromCreator(shdr.Creator, signedProp.Signature, signedProp.ProposalBytes, chdr.ChannelId)
	if err != nil {
		// log the exact message on the peer but return a generic error message to
		// avoid malicious users scanning for channels
		putilsLogger.Warningf("channel [%s]: %s", chdr.ChannelId, err)
		sId := &msp.SerializedIdentity{}
		err := proto.Unmarshal(shdr.Creator, sId)
		if err != nil {
			// log the error here as well but still only return the generic error
			err = errors.Wrap(err, "could not deserialize a SerializedIdentity")
			putilsLogger.Warningf("channel [%s]: %s", chdr.ChannelId, err)
		}
		return nil, nil, nil, errors.Errorf("access denied: channel [%s] creator org [%s]", chdr.ChannelId, sId.Mspid)
	}
}
```

### 验证Transaction签名

Commit阶段会对交易进行验证，会调用此函数，该函数完成了对Transaction的验证，包含发送方数字签名的验证。

交易是包含背书结果和背书签名的，背书相关的验证并不包含在此，而是专门的背书验证，具体请看[Fabric 1.4源码解读 1：背书策略是怎么使用的](http://lessisbetter.site/2019/09/06/fabric-source-endorser-policy-flow/)。

```go
// ValidateTransaction checks that the transaction envelope is properly formed
func ValidateTransaction(e *common.Envelope, c channelconfig.ApplicationCapabilities) (*common.Payload, pb.TxValidationCode) {
	putilsLogger.Debugf("ValidateTransactionEnvelope starts for envelope %p", e)

	...

	// validate the header
	chdr, shdr, err := validateCommonHeader(payload.Header)
	if err != nil {
		putilsLogger.Errorf("validateCommonHeader returns err %s", err)
		return nil, pb.TxValidationCode_BAD_COMMON_HEADER
	}

	// validate the signature in the envelope
	err = checkSignatureFromCreator(shdr.Creator, e.Signature, e.Payload, chdr.ChannelId)
	if err != nil {
		putilsLogger.Errorf("checkSignatureFromCreator returns err %s", err)
		return nil, pb.TxValidationCode_BAD_CREATOR_SIGNATURE
	}

    // continue the validation in a way that depends on the type specified in the header
	switch common.HeaderType(chdr.Type) {
	case common.HeaderType_ENDORSER_TRANSACTION:
		// Verify that the transaction ID has been computed properly.
		// This check is needed to ensure that the lookup into the ledger
		// for the same TxID catches duplicates.
		err = utils.CheckTxID(
			chdr.TxId,
			shdr.Nonce,
			shdr.Creator)

		if err != nil {
			putilsLogger.Errorf("CheckTxID returns err %s", err)
			return nil, pb.TxValidationCode_BAD_PROPOSAL_TXID
		}

		// 如果是背书交易，背书的签名不在此验证，由背书策略模块进行验证
		err = validateEndorserTransaction(payload.Data, payload.Header)
		putilsLogger.Debugf("ValidateTransactionEnvelope returns err %s", err)
```

## 验证签名


```go
// given a creator, a message and a signature,
// this function returns nil if the creator
// is a valid cert and the signature is valid
func checkSignatureFromCreator(creatorBytes []byte, sig []byte, msg []byte, ChainID string) error {
	putilsLogger.Debugf("begin")

	// check for nil argument
	if creatorBytes == nil || sig == nil || msg == nil {
		return errors.New("nil arguments")
	}

	// 每个链有各自的msp
	mspObj := mspmgmt.GetIdentityDeserializer(ChainID)
	if mspObj == nil {
		return errors.Errorf("could not get msp for channel [%s]", ChainID)
	}

	// 获取proposal创建者/发送方的Identity
	// creatorBytes 中是序列化后的mspid、证书、公钥等信息
	creator, err := mspObj.DeserializeIdentity(creatorBytes)
	if err != nil {
		return errors.WithMessage(err, "MSP error")
	}

	putilsLogger.Debugf("creator is %s", creator.GetIdentifier())

	// 验证证书是否有效
	// ensure that creator is a valid certificate
	err = creator.Validate()
	if err != nil {
		return errors.WithMessage(err, "creator certificate is not valid")
	}

	putilsLogger.Debugf("creator is valid")

	// validate the signature
	// 验证签名
	err = creator.Verify(msg, sig)
	if err != nil {
		return errors.WithMessage(err, "creator's signature over the proposal is not valid")
	}

	putilsLogger.Debugf("exits successfully")

	return nil
}
```

### 获取Identity

获取当前通道的MSP manager：

```go
// GetIdentityDeserializer returns the IdentityDeserializer for the given chain
func GetIdentityDeserializer(chainID string) msp.IdentityDeserializer {
	if chainID == "" {
		return GetLocalMSP()
	}

	return GetManagerForChain(chainID)
}

// GetManagerForChain returns the msp manager for the supplied
// chain; if no such manager exists, one is created
func GetManagerForChain(chainID string) msp.MSPManager {
	m.Lock()
	defer m.Unlock()

	// 先从缓存查找
	mspMgr, ok := mspMap[chainID]
	if !ok {
		// 找不到则新建立当前通道Msp manager
		mspLogger.Debugf("Created new msp manager for channel `%s`", chainID)
		mspMgmtMgr := &mspMgmtMgr{msp.NewMSPManager(), false}
		mspMap[chainID] = mspMgmtMgr
		mspMgr = mspMgmtMgr
	} else {
		// check for internal mspManagerImpl and mspMgmtMgr types. if a different
		// type is found, it's because a developer has added a new type that
		// implements the MSPManager interface and should add a case to the logic
		// above to handle it.
		if !(reflect.TypeOf(mspMgr).Elem().Name() == "mspManagerImpl" || reflect.TypeOf(mspMgr).Elem().Name() == "mspMgmtMgr") {
			panic("Found unexpected MSPManager type.")
		}
		mspLogger.Debugf("Returning existing manager for channel '%s'", chainID)
	}
	return mspMgr
}

// MSPManager has been setup for a channel, which indicates whether the channel
// exists or not
type mspMgmtMgr struct {
	msp.MSPManager
	// track whether this MSPManager has been setup successfully
	up bool
}
```

`msp.MSPManager`是一个接口，从上面代码可以得知，它是利用`NewMSPManager`创建的：

```go
// 创建等待Setup的MSPManager
func NewMSPManager() MSPManager {
	return &mspManagerImpl{}
}
```
疑问是，啥时候Setup的，当前调用路径上没发现这个路径，可能从系统整体流程上，已经保证了，当前调用时，已经创建好了。

获取Identity，是一个剥洋葱的过程：

```go
func (mgr *mspMgmtMgr) DeserializeIdentity(serializedIdentity []byte) (msp.Identity, error) {
	if !mgr.up {
		return nil, errors.New("channel doesn't exist")
	}
	return mgr.MSPManager.DeserializeIdentity(serializedIdentity)
}
```

实际调用`mspManagerImpl`的`DeserializeIdentity`：

```go
// DeserializeIdentity returns an identity given its serialized version supplied as argument
func (mgr *mspManagerImpl) DeserializeIdentity(serializedID []byte) (Identity, error) {
	// We first deserialize to a SerializedIdentity to get the MSP ID
	sId := &msp.SerializedIdentity{}
	err := proto.Unmarshal(serializedID, sId)
	if err != nil {
		return nil, errors.Wrap(err, "could not deserialize a SerializedIdentity")
	}

	// 获取发送方的msp实例
	// we can now attempt to obtain the MSP
	msp := mgr.mspsMap[sId.Mspid]
	if msp == nil {
		return nil, errors.Errorf("MSP %s is unknown", sId.Mspid)
	}

	switch t := msp.(type) {
	case *bccspmsp:
		return t.deserializeIdentityInternal(sId.IdBytes)
	case *idemixmsp:
		return t.deserializeIdentityInternal(sId.IdBytes)
	default:
		return t.DeserializeIdentity(serializedID)
	}
}
```

转到bccspmsp的实现：

```go
// 反序列化二进制，得到证书，然后用证书获取公钥，使用证书、公钥和msp，创建Identity
// deserializeIdentityInternal returns an identity given its byte-level representation
func (msp *bccspmsp) deserializeIdentityInternal(serializedIdentity []byte) (Identity, error) {
	// This MSP will always deserialize certs this way
	bl, _ := pem.Decode(serializedIdentity)
	if bl == nil {
		return nil, errors.New("could not decode the PEM structure")
	}
	cert, err := x509.ParseCertificate(bl.Bytes)
	if err != nil {
		return nil, errors.Wrap(err, "parseCertificate failed")
	}

	// Now we have the certificate; make sure that its fields
	// (e.g. the Issuer.OU or the Subject.OU) match with the
	// MSP id that this MSP has; otherwise it might be an attack
	// TODO!
	// We can't do it yet because there is no standardized way
	// (yet) to encode the MSP ID into the x.509 body of a cert

	// 从证书中提取公钥，封装一下，满足bccsp.Key接口
	pub, err := msp.bccsp.KeyImport(cert, &bccsp.X509PublicKeyImportOpts{Temporary: true})
	if err != nil {
		return nil, errors.WithMessage(err, "failed to import certificate's public key")
	}

	// 利用证书、公钥和msp建立角色身份
	return newIdentity(cert, pub, msp)
}
```


Identity包含了Identity标示符，证书、公钥和所在的msp，创建Identity就是计算以上几项信息的过程：

```go
type identity struct {
	// id contains the identifier (MSPID and identity identifier) for this instance
	id *IdentityIdentifier

	// cert contains the x.509 certificate that signs the public key of this instance
	cert *x509.Certificate

	// this is the public key of this instance
	pk bccsp.Key

	// reference to the MSP that "owns" this identity
	msp *bccspmsp
}

func newIdentity(cert *x509.Certificate, pk bccsp.Key, msp *bccspmsp) (Identity, error) {
	if mspIdentityLogger.IsEnabledFor(zapcore.DebugLevel) {
		mspIdentityLogger.Debugf("Creating identity instance for cert %s", certToPEM(cert))
	}

	// 检查证书
	// Sanitize first the certificate
	cert, err := msp.sanitizeCert(cert)
	if err != nil {
		return nil, err
	}

	// Compute identity identifier

	// Use the hash of the identity's certificate as id in the IdentityIdentifier
	hashOpt, err := bccsp.GetHashOpt(msp.cryptoConfig.IdentityIdentifierHashFunction)
	if err != nil {
		return nil, errors.WithMessage(err, "failed getting hash function options")
	}

	digest, err := msp.bccsp.Hash(cert.Raw, hashOpt)
	if err != nil {
		return nil, errors.WithMessage(err, "failed hashing raw certificate to compute the id of the IdentityIdentifier")
	}

	id := &IdentityIdentifier{
		Mspid: msp.name,
		Id:    hex.EncodeToString(digest)}

	return &identity{id: id, cert: cert, pk: pk, msp: msp}, nil
}
```

### 验证数字签名

```go
// Verify checks against a signature and a message
// to determine whether this identity produced the
// signature; it returns nil if so or an error otherwise
func (id *identity) Verify(msg []byte, sig []byte) error {
	// mspIdentityLogger.Infof("Verifying signature")

	// Compute Hash
	hashOpt, err := id.getHashOpt(id.msp.cryptoConfig.SignatureHashFamily)
	if err != nil {
		return errors.WithMessage(err, "failed getting hash function options")
	}

	digest, err := id.msp.bccsp.Hash(msg, hashOpt)
	if err != nil {
		return errors.WithMessage(err, "failed computing digest")
	}

	if mspIdentityLogger.IsEnabledFor(zapcore.DebugLevel) {
		mspIdentityLogger.Debugf("Verify: digest = %s", hex.Dump(digest))
		mspIdentityLogger.Debugf("Verify: sig = %s", hex.Dump(sig))
	}

	// 最终会调用bccsp的接口验证签名，SW或者国密
	valid, err := id.msp.bccsp.Verify(id.pk, sig, digest, nil)
	if err != nil {
		return errors.WithMessage(err, "could not determine the validity of the signature")
	} else if !valid {
		return errors.New("The signature is invalid")
	}

	return nil
}
```

## 解密SignatureHeader

Fabric 使用 `SignatureHeader` 保存发送方的身份信息，Creator即为序列化后的信息。

`SignatureHeaderMaker` 接口定义了创建一个 `SignatureHeader` 的方法，搜索起来实现该接口的结构体很多，本质上只有2个：`mspSigner` 和 `SignatureHeaderCreator`。

```go
// SignatureHeaderMaker creates a new SignatureHeader
type SignatureHeaderMaker interface {
	// NewSignatureHeader creates a SignatureHeader with the correct signing identity and a valid nonce
	NewSignatureHeader() (*cb.SignatureHeader, error)
}

// localmsp
func (s *mspSigner) NewSignatureHeader() (*cb.SignatureHeader, error) {}

// crypto
func (bs *SignatureHeaderCreator) NewSignatureHeader() (*cb.SignatureHeader, error){}
```

两个实现本质上是一样的，以 `mspSigner` 为例进行介绍。首先获取实现SigningIdentity接口的实例，然后调用`Serialize`得到序列化后的身份信息，再随机生成一个Nonce，创建出`SignatureHeader`。

```go
// NewSignatureHeader creates a SignatureHeader with the correct signing identity and a valid nonce
func (s *mspSigner) NewSignatureHeader() (*cb.SignatureHeader, error) {
	// 获得SigningIdentity接口实例
	signer, err := mspmgmt.GetLocalMSP().GetDefaultSigningIdentity()
	if err != nil {
		return nil, fmt.Errorf("Failed getting MSP-based signer [%s]", err)
	}

	// 序列化得到creator
	creatorIdentityRaw, err := signer.Serialize()
	if err != nil {
		return nil, fmt.Errorf("Failed serializing creator public identity [%s]", err)
	}

	// 获取一个随机nonce
	nonce, err := crypto.GetRandomNonce()
	if err != nil {
		return nil, fmt.Errorf("Failed creating nonce [%s]", err)
	}

	sh := &cb.SignatureHeader{}
	sh.Creator = creatorIdentityRaw
	sh.Nonce = nonce

	return sh, nil
}
```

`SigningIdentity`接口包含了`Identity`接口，Identity声明了跟证书相关的方法，SigningIdentity则增加了对消息签名的函数`Sign`。

```go
type SigningIdentity interface {

	// Extends Identity
	Identity

	// Sign the message
	Sign(msg []byte) ([]byte, error)

	// GetPublicVersion returns the public parts of this identity
	GetPublicVersion() Identity
}

type Identity interface {
    ...
	// Serialize converts an identity to bytes
	Serialize() ([]byte, error)
	...
}
```

`Serialize`的实现，实际只包含了证书和MSPID，说明了**消息中携带的只包含MSPID和证书作为身份信息**，而不是`signingidentity`的所有字段（signingidentity实现了SigningIdentity接口）。

```go
// Serialize returns a byte array representation of this identity
func (id *identity) Serialize() ([]byte, error) {
	// mspIdentityLogger.Infof("Serializing identity %s", id.id)

	// Raw格式证书
	pb := &pem.Block{Bytes: id.cert.Raw, Type: "CERTIFICATE"}
	pemBytes := pem.EncodeToMemory(pb)
	if pemBytes == nil {
		return nil, errors.New("encoding of identity failed")
	}

	// 使用MSPID和序列化后的证书，再次序列化得到身份信息 
	sId := &msp.SerializedIdentity{Mspid: id.id.Mspid, IdBytes: pemBytes}
	idBytes, err := proto.Marshal(sId)
	if err != nil {
		return nil, errors.Wrapf(err, "could not marshal a SerializedIdentity structure for identity %s", id.id)
	}

	return idBytes, nil
}
```

## 参考资料

1. https://github.com/yeasy/hyperledger_code_fabric
1. 《区块链原理、设计与应用》第9章、第10章