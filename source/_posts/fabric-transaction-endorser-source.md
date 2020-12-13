---
title: Fabric 1.4源码解读 4：交易背书流程解读
date: 2019-10-29 18:05:43
tags: ['Fabric', '区块链']
---

## 流程

在 [快速入门Fabric核心概念和框架](http://lessisbetter.site/2019/07/17/fabric-concepts-notes/) 这篇文章中，介绍了 Fabric 的很多概念，其中也包含了交易、提案（Proposal）和链码。同时也介绍了，交易的执行流程，链码的调用流程等。

本文聚焦介绍交易流程的一个环节：交易背书，以下的3幅图，在[快速入门Fabric核心概念和框架](http://lessisbetter.site/2019/07/17/fabric-concepts-notes/) 中都有介绍，有必要的话，去读一下上下文信息。

### 交易宏观流程

![](http://img.lessisbetter.site/2019-07-tx-flow.png)

交易的详细流程请阅读 [交易流程](http://lessisbetter.site/2019/07/17/fabric-concepts-notes/#%E4%BA%A4%E6%98%93)，了解交易流程的几大环节。

### 链码调用流程

![](http://img.lessisbetter.site/2019-07-fabric-invoke-chaincode.png)

上图，展示了客户端、Peer，以及链码容器 3大主体在交易流程中的背书过程，请关注一下Peer中的 Handler，它负责和链码容器交互。


### 提案背书流程

![](http://img.lessisbetter.site/2019-07-chaincode_swimlane.png)

上图，从接近源码的层面，展示了交易背书过程。其中Fabric、Shim 是 Peer 中的模块，ChainCode 代表链码容器，Endorser Chaincode 代表 Peer 对交易提案和模拟执行结果进行背书。

如果了解过Chaincode，你会知道 Shim 是链码容器和 Peer 交互所依赖的模块。

最后推荐一份保华大佬整理的 [Peer 提案背书过程](https://github.com/yeasy/hyperledger_code_fabric/blob/master/process/peer_endorse.md)，是读源码前，必读的资料。虽然精简，但把重要的核心流程都串联起来了。

## 源码分析

### Proposal定义

客户端发送被背书节点的是 `SignedProposal` ，它包含了签名和Proposal，这是它在`proposal.proto`中的组成简介，：

```
SignedProposal
|\_ Signature                                    (signature on the Proposal message by the creator specified in the header)
 \_ Proposal
    |\_ Header                                   (the header for this proposal)
     \_ Payload                                  (the payload for this proposal)
```

`proposal.proto`这个文件还简要介绍了Client和背书节点之间通信的消息类型和过程。

#### Proposal

```go
type SignedProposal struct {
	// The bytes of Proposal
	ProposalBytes []byte `protobuf:"bytes,1,opt,name=proposal_bytes,json=proposalBytes,proto3" json:"proposal_bytes,omitempty"`
	// Signaure over proposalBytes; this signature is to be verified against
	// the creator identity contained in the header of the Proposal message
	// marshaled as proposalBytes
	Signature            []byte   `protobuf:"bytes,2,opt,name=signature,proto3" json:"signature,omitempty"`
}
```



```go
type Proposal struct {
	// The header of the proposal. It is the bytes of the Header
	Header []byte `protobuf:"bytes,1,opt,name=header,proto3" json:"header,omitempty"`
	// The payload of the proposal as defined by the type in the proposal
	// header.
	Payload []byte `protobuf:"bytes,2,opt,name=payload,proto3" json:"payload,omitempty"`
	// Optional extensions to the proposal. Its content depends on the Header's
	// type field.  For the type CHAINCODE, it might be the bytes of a
	// ChaincodeAction message.
	Extension            []byte   `protobuf:"bytes,3,opt,name=extension,proto3" json:"extension,omitempty"`
	XXX_NoUnkeyedLiteral struct{} `json:"-"`
	XXX_unrecognized     []byte   `json:"-"`
	XXX_sizecache        int32    `json:"-"`
}
```

#### Header

```go
type Header struct {
	ChannelHeader        []byte   `protobuf:"bytes,1,opt,name=channel_header,json=channelHeader,proto3" json:"channel_header,omitempty"`
	SignatureHeader      []byte   `protobuf:"bytes,2,opt,name=signature_header,json=signatureHeader,proto3" json:"signature_header,omitempty"`
	XXX_NoUnkeyedLiteral struct{} `json:"-"`
	XXX_unrecognized     []byte   `json:"-"`
	XXX_sizecache        int32    `json:"-"`
}


// Header is a generic replay prevention and identity message to include in a signed payload
type ChannelHeader struct {
	Type int32 `protobuf:"varint,1,opt,name=type,proto3" json:"type,omitempty"`
	// Version indicates message protocol version
	Version int32 `protobuf:"varint,2,opt,name=version,proto3" json:"version,omitempty"`
	// Timestamp is the local time when the message was created
	// by the sender
	Timestamp *timestamp.Timestamp `protobuf:"bytes,3,opt,name=timestamp,proto3" json:"timestamp,omitempty"`
	// Identifier of the channel this message is bound for
	ChannelId string `protobuf:"bytes,4,opt,name=channel_id,json=channelId,proto3" json:"channel_id,omitempty"`
	// An unique identifier that is used end-to-end.
	//  -  set by higher layers such as end user or SDK
	//  -  passed to the endorser (which will check for uniqueness)
	//  -  as the header is passed along unchanged, it will be
	//     be retrieved by the committer (uniqueness check here as well)
	//  -  to be stored in the ledger
	TxId string `protobuf:"bytes,5,opt,name=tx_id,json=txId,proto3" json:"tx_id,omitempty"`
	// The epoch in which this header was generated, where epoch is defined based on block height
	// Epoch in which the response has been generated. This field identifies a
	// logical window of time. A proposal response is accepted by a peer only if
	// two conditions hold:
	// 1. the epoch specified in the message is the current epoch
	// 2. this message has been only seen once during this epoch (i.e. it hasn't
	//    been replayed)
	Epoch uint64 `protobuf:"varint,6,opt,name=epoch,proto3" json:"epoch,omitempty"`
	// Extension that may be attached based on the header type
	Extension []byte `protobuf:"bytes,7,opt,name=extension,proto3" json:"extension,omitempty"`
	// If mutual TLS is employed, this represents
	// the hash of the client's TLS certificate
	TlsCertHash          []byte   `protobuf:"bytes,8,opt,name=tls_cert_hash,json=tlsCertHash,proto3" json:"tls_cert_hash,omitempty"`
	XXX_NoUnkeyedLiteral struct{} `json:"-"`
	XXX_unrecognized     []byte   `json:"-"`
	XXX_sizecache        int32    `json:"-"`
}

type SignatureHeader struct {
	// Creator of the message, a marshaled msp.SerializedIdentity
	Creator []byte `protobuf:"bytes,1,opt,name=creator,proto3" json:"creator,omitempty"`
	// Arbitrary number that may only be used once. Can be used to detect replay attacks.
	Nonce                []byte   `protobuf:"bytes,2,opt,name=nonce,proto3" json:"nonce,omitempty"`
	XXX_NoUnkeyedLiteral struct{} `json:"-"`
	XXX_unrecognized     []byte   `json:"-"`
	XXX_sizecache        int32    `json:"-"`
}
```

### gRPC定义


```go
// EndorserClient is the client API for Endorser service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://godoc.org/google.golang.org/grpc#ClientConn.NewStream.
type EndorserClient interface {
	ProcessProposal(ctx context.Context, in *SignedProposal, opts ...grpc.CallOption) (*ProposalResponse, error)
}

// EndorserServer is the server API for Endorser service.
type EndorserServer interface {
	ProcessProposal(context.Context, *SignedProposal) (*ProposalResponse, error)
}
```

### SDK发送Proposal



### Peer接收Proposal



### Peer处理Proposal主流程

主要是把背书节点的背书工作聚合一下：
1. Proposal预处理
1. 获取交易执行模拟器，模拟执行Proposal
1. 如果模拟执行成功，调用ESCC对Proposal和结果进行背书，如果模拟执行失败直接返回背书失败的响应

```go
func (e *Endorser) ProcessProposal(ctx context.Context, signedProp *pb.SignedProposal) (*pb.ProposalResponse, error) {
	...
	// 0 -- check and validate
	// 这里有相当多的工作量
	vr, err := e.preProcess(signedProp)
	if err != nil {
		resp := vr.resp
		return resp, err
	}

	prop, hdrExt, chainID, txid := vr.prop, vr.hdrExt, vr.chainID, vr.txid

	// 获取指定账本模拟器
	// obtaining once the tx simulator for this proposal. This will be nil
	// for chainless proposals
	// Also obtain a history query executor for history queries, since tx simulator does not cover history
	var txsim ledger.TxSimulator
	var historyQueryExecutor ledger.HistoryQueryExecutor
	if acquireTxSimulator(chainID, vr.hdrExt.ChaincodeId) {
		if txsim, err = e.s.GetTxSimulator(chainID, txid); err != nil {
			return &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}, nil
		}
		...
		defer txsim.Done()

		if historyQueryExecutor, err = e.s.GetHistoryQueryExecutor(chainID); err != nil {
			return &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}, nil
		}
	}

	txParams := &ccprovider.TransactionParams{
		ChannelID:            chainID,
		TxID:                 txid,
		SignedProp:           signedProp,
		Proposal:             prop,
		TXSimulator:          txsim,
		HistoryQueryExecutor: historyQueryExecutor,
	}
	// this could be a request to a chainless SysCC

	// 模拟执行交易，失败则返回背书失败的响应
	// 1 -- simulate
	cd, res, simulationResult, ccevent, err := e.SimulateProposal(txParams, hdrExt.ChaincodeId)
	if err != nil {
		return &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}, nil
	}
	if res != nil {
		if res.Status >= shim.ERROR {
			endorserLogger.Errorf("[%s][%s] simulateProposal() resulted in chaincode %s response status %d for txid: %s", chainID, shorttxid(txid), hdrExt.ChaincodeId, res.Status, txid)
			var cceventBytes []byte
			if ccevent != nil {
				cceventBytes, err = putils.GetBytesChaincodeEvent(ccevent)
				if err != nil {
					return nil, errors.Wrap(err, "failed to marshal event bytes")
				}
			}
			pResp, err := putils.CreateProposalResponseFailure(prop.Header, prop.Payload, res, simulationResult, cceventBytes, hdrExt.ChaincodeId, hdrExt.PayloadVisibility)
			if err != nil {
				return &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}, nil
			}

			return pResp, nil
		}
	}

	// 对模拟执行的结果进行签名背书
	// 2 -- endorse and get a marshalled ProposalResponse message
	var pResp *pb.ProposalResponse

	// TODO till we implement global ESCC, CSCC for system chaincodes
	// chainless proposals (such as CSCC) don't have to be endorsed
	if chainID == "" {
		pResp = &pb.ProposalResponse{Response: res}
	} else {
		// Note: To endorseProposal(), we pass the released txsim. Hence, an error would occur if we try to use this txsim
		pResp, err = e.endorseProposal(ctx, chainID, txid, signedProp, prop, res, simulationResult, ccevent, hdrExt.PayloadVisibility, hdrExt.ChaincodeId, txsim, cd)

		...
	}

	// Set the proposal response payload - it
	// contains the "return value" from the
	// chaincode invocation
	pResp.Response = res

	// total failed proposals = ProposalsReceived-SuccessfulProposals
	e.Metrics.SuccessfulProposals.Add(1)
	success = true

	return pResp, nil
}
```

### preProcess 检查和获取信息

```go
// preProcess checks the tx proposal headers, uniqueness and ACL
// 检查proposal、ACL
func (e *Endorser) preProcess(signedProp *pb.SignedProposal) (*validateResult, error) {
	// 包含proposal、header、chainID、txid等信息
	vr := &validateResult{}
	// at first, we check whether the message is valid
	// 检查proposal，并获取各种需要的信息
	prop, hdr, hdrExt, err := validation.ValidateProposalMessage(signedProp)

	if err != nil {
		e.Metrics.ProposalValidationFailed.Add(1)
		vr.resp = &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}
		return vr, err
	}

	// 获取Header中的2个Header
	chdr, err := putils.UnmarshalChannelHeader(hdr.ChannelHeader)
	if err != nil {
		vr.resp = &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}
		return vr, err
	}

	shdr, err := putils.GetSignatureHeader(hdr.SignatureHeader)
	if err != nil {
		vr.resp = &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}
		return vr, err
	}

	// 检查是否调用了不可外部（用户）的系统链码
	// 先找到链码实例，然后调用链码的方法判断本身是否可调用
	// block invocations to security-sensitive system chaincodes
	if e.s.IsSysCCAndNotInvokableExternal(hdrExt.ChaincodeId.Name) {
		endorserLogger.Errorf("Error: an attempt was made by %#v to invoke system chaincode %s", shdr.Creator, hdrExt.ChaincodeId.Name)
		err = errors.Errorf("chaincode %s cannot be invoked through a proposal", hdrExt.ChaincodeId.Name)
		vr.resp = &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}
		return vr, err
	}

	chainID := chdr.ChannelId
	txid := chdr.TxId
	endorserLogger.Debugf("[%s][%s] processing txid: %s", chainID, shorttxid(txid), txid)

	if chainID != "" {
		// labels that provide context for failure metrics
		meterLabels := []string{
			"channel", chainID,
			"chaincode", hdrExt.ChaincodeId.Name + ":" + hdrExt.ChaincodeId.Version,
		}

		// 检查交易是否已上链
		// Here we handle uniqueness check and ACLs for proposals targeting a chain
		// Notice that ValidateProposalMessage has already verified that TxID is computed properly
		if _, err = e.s.GetTransactionByID(chainID, txid); err == nil {
			// increment failure due to duplicate transactions. Useful for catching replay attacks in
			// addition to benign retries
			e.Metrics.DuplicateTxsFailure.With(meterLabels...).Add(1)
			err = errors.Errorf("duplicate transaction found [%s]. Creator [%x]", txid, shdr.Creator)
			vr.resp = &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}
			return vr, err
		}

		// 用户链码检查ACL
		// check ACL only for application chaincodes; ACLs
		// for system chaincodes are checked elsewhere
		if !e.s.IsSysCC(hdrExt.ChaincodeId.Name) {
			// check that the proposal complies with the Channel's writers
			if err = e.s.CheckACL(signedProp, chdr, shdr, hdrExt); err != nil {
				e.Metrics.ProposalACLCheckFailed.With(meterLabels...).Add(1)
				vr.resp = &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}
				return vr, err
			}
		}
	} else {
		// chainless proposals do not/cannot affect ledger and cannot be submitted as transactions
		// ignore uniqueness checks; also, chainless proposals are not validated using the policies
		// of the chain since by definition there is no chain; they are validated against the local
		// MSP of the peer instead by the call to ValidateProposalMessage above
	}

	// 保存提取的各信息
	vr.prop, vr.hdrExt, vr.chainID, vr.txid = prop, hdrExt, chainID, txid
	return vr, nil
}

// ValidateProposalMessage checks the validity of a SignedProposal message
// this function returns Header and ChaincodeHeaderExtension messages since they
// have been unmarshalled and validated
func ValidateProposalMessage(signedProp *pb.SignedProposal) (*pb.Proposal, *common.Header, *pb.ChaincodeHeaderExtension, error) {
	if signedProp == nil {
		return nil, nil, nil, errors.New("nil arguments")
	}

	putilsLogger.Debugf("ValidateProposalMessage starts for signed proposal %p", signedProp)

	// extract the Proposal message from signedProp
	prop, err := utils.GetProposal(signedProp.ProposalBytes)
	if err != nil {
		return nil, nil, nil, err
	}

	// 1) look at the ProposalHeader
	hdr, err := utils.GetHeader(prop.Header)
	if err != nil {
		return nil, nil, nil, err
	}

	// validate the header
	chdr, shdr, err := validateCommonHeader(hdr)
	if err != nil {
		return nil, nil, nil, err
	}

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

	// 检查txid的计算是否符合规则
	// Verify that the transaction ID has been computed properly.
	// This check is needed to ensure that the lookup into the ledger
	// for the same TxID catches duplicates.
	err = utils.CheckTxID(
		chdr.TxId,
		shdr.Nonce,
		shdr.Creator)
	if err != nil {
		return nil, nil, nil, err
	}

	// 依据不同的proposal类型对proposal分别进行检查
	// continue the validation in a way that depends on the type specified in the header
	switch common.HeaderType(chdr.Type) {
	case common.HeaderType_CONFIG:
		//which the types are different the validation is the same
		//viz, validate a proposal to a chaincode. If we need other
		//special validation for confguration, we would have to implement
		//special validation
		fallthrough
	case common.HeaderType_ENDORSER_TRANSACTION:
		// 主要是提取ChaincodeHeaderExtension
		// validation of the proposal message knowing it's of type CHAINCODE
		chaincodeHdrExt, err := validateChaincodeProposalMessage(prop, hdr)
		if err != nil {
			return nil, nil, nil, err
		}

		return prop, hdr, chaincodeHdrExt, err
	default:
		//NOTE : we proably need a case
		return nil, nil, nil, errors.Errorf("unsupported proposal type %d", common.HeaderType(chdr.Type))
	}
}
```


### 背书节点模拟执行交易

#### 获取模拟器

```go
// Support contains functions that the endorser requires to execute its tasks
type Support interface {
	crypto.SignerSupport
	// IsSysCCAndNotInvokableExternal returns true if the supplied chaincode is
	// ia system chaincode and it NOT invokable
	IsSysCCAndNotInvokableExternal(name string) bool

	// GetTxSimulator returns the transaction simulator for the specified ledger
	// a client may obtain more than one such simulator; they are made unique
	// by way of the supplied txid
	GetTxSimulator(ledgername string, txid string) (ledger.TxSimulator, error)

}

// GetTxSimulator returns the transaction simulator for the specified ledger
// a client may obtain more than one such simulator; they are made unique
// by way of the supplied txid
func (s *SupportImpl) GetTxSimulator(ledgername string, txid string) (ledger.TxSimulator, error) {
	// 使用账本和txid创建模拟器，每个交易有单独的模拟器
	lgr := s.Peer.GetLedger(ledgername)
	if lgr == nil {
		return nil, errors.Errorf("Channel does not exist: %s", ledgername)
	}
	return lgr.NewTxSimulator(txid)
}

// NewTxSimulator returns new `ledger.TxSimulator`
func (l *kvLedger) NewTxSimulator(txid string) (ledger.TxSimulator, error) {
	return l.txtmgmt.NewTxSimulator(txid)
}

// NewTxSimulator implements method in interface `txmgmt.TxMgr`
func (txmgr *LockBasedTxMgr) NewTxSimulator(txid string) (ledger.TxSimulator, error) {
	logger.Debugf("constructing new tx simulator")
	s, err := newLockBasedTxSimulator(txmgr, txid)
	if err != nil {
		return nil, err
	}
	txmgr.commitRWLock.RLock()
	return s, nil
}

// 就2项重要的：查询执行器、读写集构建器
// LockBasedTxSimulator is a transaction simulator used in `LockBasedTxMgr`
type lockBasedTxSimulator struct {
	lockBasedQueryExecutor
	rwsetBuilder              *rwsetutil.RWSetBuilder
	writePerformed            bool
	pvtdataQueriesPerformed   bool
	simulationResultsComputed bool
	paginatedQueriesPerformed bool
}

func newLockBasedTxSimulator(txmgr *LockBasedTxMgr, txid string) (*lockBasedTxSimulator, error) {
	// 创建读写集构建器，能帮助构建读写集
	rwsetBuilder := rwsetutil.NewRWSetBuilder()
	helper := newQueryHelper(txmgr, rwsetBuilder)
	logger.Debugf("constructing new tx simulator txid = [%s]", txid)
	return &lockBasedTxSimulator{lockBasedQueryExecutor{helper, txid}, rwsetBuilder, false, false, false, false}, nil
}

// LockBasedQueryExecutor is a query executor used in `LockBasedTxMgr`
// "只读"，不包含写相关的操作
type lockBasedQueryExecutor struct {
	helper *queryHelper
	txid   string
}
```

#### 模拟执行

##### endorser部分

```go
	if acquireTxSimulator(chainID, vr.hdrExt.ChaincodeId) {
		if txsim, err = e.s.GetTxSimulator(chainID, txid); err != nil {
			return &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}, nil
		}
		defer txsim.Done()

		// 历史查询器
		if historyQueryExecutor, err = e.s.GetHistoryQueryExecutor(chainID); err != nil {
			return &pb.ProposalResponse{Response: &pb.Response{Status: 500, Message: err.Error()}}, nil
		}
	}

	txParams := &ccprovider.TransactionParams{
		ChannelID:            chainID,
		TxID:                 txid,
		SignedProp:           signedProp,
		Proposal:             prop,
		TXSimulator:          txsim,	// 模拟器在此
		HistoryQueryExecutor: historyQueryExecutor,
	}
	// this could be a request to a chainless SysCC

	// TODO: if the proposal has an extension, it will be of type ChaincodeAction;
	//       if it's present it means that no simulation is to be performed because
	//       we're trying to emulate a submitting peer. On the other hand, we need
	//       to validate the supplied action before endorsing it

	// 模拟执行交易，失败则返回背书失败的响应
	// 1 -- simulate
	cd, res, simulationResult, ccevent, err := e.SimulateProposal(txParams, hdrExt.ChaincodeId)
```

调用chaincode模块模拟执行交易，获取交易执行的公开和私密数据读写集，以及交易执行产生的事件，并把结果返回给上层进行背书。

其中还包含了私密数据的处理，会把它取出来，然后通过Gossip传播给在私密数据中的Peer节点。

```go
// SimulateProposal simulates the proposal by calling the chaincode
func (e *Endorser) SimulateProposal(txParams *ccprovider.TransactionParams, cid *pb.ChaincodeID) (ccprovider.ChaincodeDefinition, *pb.Response, []byte, *pb.ChaincodeEvent, error) {
	endorserLogger.Debugf("[%s][%s] Entry chaincode: %s", txParams.ChannelID, shorttxid(txParams.TxID), cid)
	defer endorserLogger.Debugf("[%s][%s] Exit", txParams.ChannelID, shorttxid(txParams.TxID))
	// we do expect the payload to be a ChaincodeInvocationSpec
	// if we are supporting other payloads in future, this be glaringly point
	// as something that should change
	// 根据Proposal生成Invoke需要的信息
	cis, err := putils.GetChaincodeInvocationSpec(txParams.Proposal)
	if err != nil {
		return nil, nil, nil, nil, err
	}

	// 链码的元数据
	var cdLedger ccprovider.ChaincodeDefinition
	var version string

	// 设置version
	if !e.s.IsSysCC(cid.Name) {
		// 根据要调用的链码名称，从lscc获取链码的元数据
		cdLedger, err = e.s.GetChaincodeDefinition(cid.Name, txParams.TXSimulator)
		if err != nil {
			return nil, nil, nil, nil, errors.WithMessage(err, fmt.Sprintf("make sure the chaincode %s has been successfully instantiated and try again", cid.Name))
		}
		version = cdLedger.CCVersion()

		// 实际被打桩了，无实现
		err = e.s.CheckInstantiationPolicy(cid.Name, version, cdLedger)
		if err != nil {
			return nil, nil, nil, nil, err
		}
	} else {
		// scc版本是固定的"latest"
		version = util.GetSysCCVersion()
	}

	// ---3. execute the proposal and get simulation results
	var simResult *ledger.TxSimulationResults
	var pubSimResBytes []byte
	var res *pb.Response
	var ccevent *pb.ChaincodeEvent
	// 模拟执行，执行结果保存在模拟器
	res, ccevent, err = e.callChaincode(txParams, version, cis.ChaincodeSpec.Input, cid)
	if err != nil {
		endorserLogger.Errorf("[%s][%s] failed to invoke chaincode %s, error: %+v", txParams.ChannelID, shorttxid(txParams.TxID), cid, err)
		return nil, nil, nil, nil, err
	}

	if txParams.TXSimulator != nil {
		// 通过模拟器获取模拟执行结果，包含公开和私密数据2份读写集
		if simResult, err = txParams.TXSimulator.GetTxSimulationResults(); err != nil {
			txParams.TXSimulator.Done()
			return nil, nil, nil, nil, err
		}

		// 存在私密数据
		if simResult.PvtSimulationResults != nil {
			if cid.Name == "lscc" {
				// TODO: remove once we can store collection configuration outside of LSCC
				txParams.TXSimulator.Done()
				return nil, nil, nil, nil, errors.New("Private data is forbidden to be used in instantiate")
			}
			// 获取要通过Gossip传播的私密数据
			pvtDataWithConfig, err := e.AssemblePvtRWSet(simResult.PvtSimulationResults, txParams.TXSimulator)
			// To read collection config need to read collection updates before
			// releasing the lock, hence txParams.TXSimulator.Done()  moved down here
			txParams.TXSimulator.Done()

			if err != nil {
				return nil, nil, nil, nil, errors.WithMessage(err, "failed to obtain collections config")
			}
			endorsedAt, err := e.s.GetLedgerHeight(txParams.ChannelID)
			if err != nil {
				return nil, nil, nil, nil, errors.WithMessage(err, fmt.Sprint("failed to obtain ledger height for channel", txParams.ChannelID))
			}
			// Add ledger height at which transaction was endorsed,
			// `endorsedAt` is obtained from the block storage and at times this could be 'endorsement Height + 1'.
			// However, since we use this height only to select the configuration (3rd parameter in distributePrivateData) and
			// manage transient store purge for orphaned private writesets (4th parameter in distributePrivateData), this works for now.
			// Ideally, ledger should add support in the simulator as a first class function `GetHeight()`.
			pvtDataWithConfig.EndorsedAt = endorsedAt
			// 把私密数据同通道id、交易id和区块高度发出去，代表私密数据所属的区块和交易
			if err := e.distributePrivateData(txParams.ChannelID, txParams.TxID, pvtDataWithConfig, endorsedAt); err != nil {
				return nil, nil, nil, nil, err
			}
		}

		// 交易模拟完成，释放模拟器占用的资源
		txParams.TXSimulator.Done()
		// 获取模拟执行的公开结果
		if pubSimResBytes, err = simResult.GetPubSimulationBytes(); err != nil {
			return nil, nil, nil, nil, err
		}
	}
	
	// 返回链码元数据、模拟执行结果、交易执行产生的事件
	return cdLedger, res, pubSimResBytes, ccevent, nil
}
```

`callChaincode` 调用chaincode模块执行链码。在前面的流程中，还没有区分系统链码SCC和用户链码UCC，SCC和UCC都会通过`Execute`函数被传递给chaincode模块而执行。

如果是调用`lscc`部署或升级UCC，会调用`ExecuteLegacyInit`执行链码容器的初始化。

最后返回链码模拟执行结果和事件。

```go
// call specified chaincode (system or user)
func (e *Endorser) callChaincode(txParams *ccprovider.TransactionParams, version string, input *pb.ChaincodeInput, cid *pb.ChaincodeID) (*pb.Response, *pb.ChaincodeEvent, error) {
	...
	// scc也在这执行
	// is this a system chaincode
	res, ccevent, err = e.s.Execute(txParams, txParams.ChannelID, cid.Name, version, txParams.TxID, txParams.SignedProp, txParams.Proposal, input)
	if err != nil {
		return nil, nil, err
	}
	...

	// 如果是调用lscc部署或升级链码，会走这段流程
	if cid.Name == "lscc" && len(input.Args) >= 3 && (string(input.Args[0]) == "deploy" || string(input.Args[0]) == "upgrade") {
		userCDS, err := putils.GetChaincodeDeploymentSpec(input.Args[2], e.PlatformRegistry)
		...
		// 进行链码容器初始化，最后会调用链码的Init的函数
		_, _, err = e.s.ExecuteLegacyInit(txParams, txParams.ChannelID, cds.ChaincodeSpec.ChaincodeId.Name, cds.ChaincodeSpec.ChaincodeId.Version, txParams.TxID, txParams.SignedProp, txParams.Proposal, cds)
		...
	}
	// ----- END -------

	return res, ccevent, err
}
```

`Support` 接口实际集合了众多背书节点需要的外部模块功能，比如链码、系统链码、ACL等。

```go
// Support contains functions that the endorser requires to execute its tasks
type Support interface 

// SupportImpl provides an implementation of the endorser.Support interface
// issuing calls to various static methods of the peer
type SupportImpl struct {
	*PluginEndorser
	crypto.SignerSupport
	Peer             peer.Operations
	PeerSupport      peer.Support
	ChaincodeSupport *chaincode.ChaincodeSupport
	SysCCProvider    *scc.Provider
	ACLProvider      aclmgmt.ACLProvider
}
```

`Execute`就是调用`ChaincodeSupport.Execute`实现的。

```go
// Execute a proposal and return the chaincode response
func (s *SupportImpl) Execute(txParams *ccprovider.TransactionParams, cid, name, version, txid string, signedProp *pb.SignedProposal, prop *pb.Proposal, input *pb.ChaincodeInput) (*pb.Response, *pb.ChaincodeEvent, error) {
	cccid := &ccprovider.CCContext{
		Name:    name,
		Version: version,
	}

	// decorate the chaincode input
	decorators := library.InitRegistry(library.Config{}).Lookup(library.Decoration).([]decoration.Decorator)
	input.Decorations = make(map[string][]byte)
	input = decoration.Apply(prop, input, decorators...)
	txParams.ProposalDecorations = input.Decorations

	return s.ChaincodeSupport.Execute(txParams, cccid, input)
}
```

##### chaincode部分

通过上面的接口，跨入chaincode模块的大门。

```go
func (cs *ChaincodeSupport) Execute(txParams *ccprovider.TransactionParams, cccid *ccprovider.CCContext, input *pb.ChaincodeInput) (*pb.Response, *pb.ChaincodeEvent, error) {
	// Invoke得到ChaincodeMessage
	resp, err := cs.Invoke(txParams, cccid, input)
	// 根据ChaincodeMessage得到Response和事件
	return processChaincodeExecutionResult(txParams.TxID, cccid.Name, resp, err)
}

func (cs *ChaincodeSupport) Invoke(txParams *ccprovider.TransactionParams, cccid *ccprovider.CCContext, input *pb.ChaincodeInput) (*pb.ChaincodeMessage, error) {
	h, err := cs.Launch(txParams.ChannelID, cccid.Name, cccid.Version, txParams.TXSimulator)
	if err != nil {
		return nil, err
	}

	// 执行调用链码的交易（和链码之间的消息为ChaincodeMessage_TRANSACTION）
	cctype := pb.ChaincodeMessage_TRANSACTION
	return cs.execute(cctype, txParams, cccid, input, h)
}
```


##### 获取链码执行环境

`Launch` 可以获取链码执行环境，即用户链码容器，如果已实例化的链码，在当前背书节点上，链码容器未启动，则启动链码容器，`Launch`会返回一个跟链码容器交互Handler。

某个 Peer 上可以部署多个链码容器，Peer 为了和这些链码容器交互/通信，给每个链码容器都创建了一个 Handler，Handler 携带了 Peer 和链码容器交互的资源。

![](http://img.lessisbetter.site/2019-10-peer-cc-handler.png)

```go
// Launch starts executing chaincode if it is not already running. This method
// blocks until the peer side handler gets into ready state or encounters a fatal
// error. If the chaincode is already running, it simply returns.
func (cs *ChaincodeSupport) Launch(chainID, chaincodeName, chaincodeVersion string, qe ledger.QueryExecutor) (*Handler, error) {
	cname := chaincodeName + ":" + chaincodeVersion
	if h := cs.HandlerRegistry.Handler(cname); h != nil {
		return h, nil
	}

	// 启动链码容器 ...

	h := cs.HandlerRegistry.Handler(cname)
	if h == nil {
		return nil, errors.Wrapf(err, "[channel %s] claimed to start chaincode container for %s but could not find handler", chainID, cname)
	}

	return h, nil
}
```

链码容器的启动过程，不是本文的重点，所以不继续深入Launch的调用细节。

##### 模拟执行交易

`execute`封装出执行交易的消息，然后使用 Handler 执行交易。

```go
// execute executes a transaction and waits for it to complete until a timeout value.
func (cs *ChaincodeSupport) execute(cctyp pb.ChaincodeMessage_Type, txParams *ccprovider.TransactionParams, cccid *ccprovider.CCContext, input *pb.ChaincodeInput, h *Handler) (*pb.ChaincodeMessage, error) {
	input.Decorations = txParams.ProposalDecorations
	// 创建消息
	ccMsg, err := createCCMessage(cctyp, txParams.ChannelID, txParams.TxID, input)
	if err != nil {
		return nil, errors.WithMessage(err, "failed to create chaincode message")
	}

	// 执行交易
	ccresp, err := h.Execute(txParams, cccid, ccMsg, cs.ExecuteTimeout)
	if err != nil {
		return nil, errors.WithMessage(err, fmt.Sprintf("error sending"))
	}

	return ccresp, nil
}
```

注意以下这个参数 `txParams *ccprovider.TransactionParams` 其类型定义如下，它包含了一条交易执行过程中的信息和资源，所以交易传递的过程中，一直有这个参数。

```go
// TransactionParams are parameters which are tied to a particular transaction
// and which are required for invoking chaincode.
type TransactionParams struct {
	TxID                 string
	ChannelID            string
	SignedProp           *pb.SignedProposal
	Proposal             *pb.Proposal
	TXSimulator          ledger.TxSimulator
	HistoryQueryExecutor ledger.HistoryQueryExecutor
	CollectionStore      privdata.CollectionStore
	IsInitTransaction    bool

	// this is additional data passed to the chaincode
	ProposalDecorations map[string][]byte
}
```

Handler 执行交易的过程如下，创建交易执行的上下文 Context，因为链码容器在执行交易的时候，会和 Peer 之间进行多次通信，进行数据的读写，上下文可以让数据读写获取到正确的信息。

之后 Handler 把消息发送给链码容器，并等待链码容器发来包含执行结果的消息，或者执行超时，默认执行时间是 30s。

```go
func (h *Handler) Execute(txParams *ccprovider.TransactionParams, cccid *ccprovider.CCContext, msg *pb.ChaincodeMessage, timeout time.Duration) (*pb.ChaincodeMessage, error) {
	chaincodeLogger.Debugf("Entry")
	defer chaincodeLogger.Debugf("Exit")

	// 私密数据
	txParams.CollectionStore = h.getCollectionStore(msg.ChannelId)
	// 是否是执行链码初始化
	txParams.IsInitTransaction = (msg.Type == pb.ChaincodeMessage_INIT)

	// 创建交易context
	txctx, err := h.TXContexts.Create(txParams)
	if err != nil {
		return nil, err
	}
	// 退出时（执行交易完毕），释放交易上下文资源
	defer h.TXContexts.Delete(msg.ChannelId, msg.Txid)

	// proposal保存到msg
	if err := h.setChaincodeProposal(txParams.SignedProp, txParams.Proposal, msg); err != nil {
		return nil, err
	}

	// 向链码容器发送msg
	h.serialSendAsync(msg)

	// 等待链码容器响应，或者超时
	var ccresp *pb.ChaincodeMessage
	select {
	case ccresp = <-txctx.ResponseNotifier:
		// response is sent to user or calling chaincode. ChaincodeMessage_ERROR
		// are typically treated as error
	case <-time.After(timeout):
		err = errors.New("timeout expired while executing transaction")
		ccName := cccid.Name + ":" + cccid.Version
		h.Metrics.ExecuteTimeouts.With(
			"chaincode", ccName,
		).Add(1)
	}

	return ccresp, err
}
```

##### 处理链码容器模拟响应

链码容器执行的响应会向上传递，直到 `ChaincodeSupport.Execute`，它调用 `processChaincodeExecutionResult` 把链码容器返回的响应，转化为交易模拟执行的 Response，而 Response 最终会返回给Endorser，大家可去调用流程上翻。

```go
func processChaincodeExecutionResult(txid, ccName string, resp *pb.ChaincodeMessage, err error) (*pb.Response, *pb.ChaincodeEvent, error) {
	if err != nil {
		return nil, nil, errors.Wrapf(err, "failed to execute transaction %s", txid)
	}
	if resp == nil {
		return nil, nil, errors.Errorf("nil response from transaction %s", txid)
	}

	if resp.ChaincodeEvent != nil {
		resp.ChaincodeEvent.ChaincodeId = ccName
		resp.ChaincodeEvent.TxId = txid
	}

	switch resp.Type {
	// 交易执行成功则提取Payload中保存的Response
	case pb.ChaincodeMessage_COMPLETED:
		res := &pb.Response{}
		err := proto.Unmarshal(resp.Payload, res)
		if err != nil {
			return nil, nil, errors.Wrapf(err, "failed to unmarshal response for transaction %s", txid)
		}
		return res, resp.ChaincodeEvent, nil

	// 	失败，则提取Payload中保存的错误信息
	case pb.ChaincodeMessage_ERROR:
		return nil, resp.ChaincodeEvent, errors.Errorf("transaction returned with failure: %s", resp.Payload)

	default:
		return nil, nil, errors.Errorf("unexpected response type %d for transaction %s", resp.Type, txid)
	}
}
```

#### 释放模拟器资源

回想一下，在 `Endorser.SimulateProposal` 中，它获取了 交易模拟执行器 `TXSimulator`，这里面可是有很多资源的，如果不及时释放，在高 TPS 下，Peer压力上大，资源泄露，性能低下等问题会爆发出来。

`txParams.TXSimulator.Done()` 用来释放资源，上文提到 `TxSimulator` 包含了 `QueryExecutor`, `lockBasedQueryExecutor` 实现了 `QueryExecutor`，也就是说，主要是释放查询操作相关的资源。

从源码可以看到会释放读写锁以及迭代器资源，如果不及时释放，后果果然不堪。

```go
// Done implements method in interface `ledger.QueryExecutor`
func (q *lockBasedQueryExecutor) Done() {
	logger.Debugf("Done with transaction simulation / query execution [%s]", q.txid)
	q.helper.done()
}

func (h *queryHelper) done() {
	if h.doneInvoked {
		return
	}

	defer func() {
		// 释放锁
		h.txmgr.commitRWLock.RUnlock()
		h.doneInvoked = true
		// 释放迭代器
		for _, itr := range h.itrs {
			itr.Close()
		}
	}()
}
```

### ESCC处理模拟执行结果

上文提到，模拟执行的 Response 会最终回到 Endorser，Endorser 会调用 ESCC 对结果进行背书，最终生成 `ProposalResponse`，我们看一下这个过程。

```go
func (e *Endorser) ProcessProposal(ctx context.Context, signedProp *pb.SignedProposal) (*pb.ProposalResponse, error) {
	// Pre-process, simulate

	if chainID == "" {
		pResp = &pb.ProposalResponse{Response: res}
	} else {
		// Note: To endorseProposal(), we pass the released txsim. Hence, an error would occur if we try to use this txsim
		pResp, err = e.endorseProposal(ctx, chainID, txid, signedProp, prop, res, simulationResult, ccevent, hdrExt.PayloadVisibility, hdrExt.ChaincodeId, txsim, cd)
		// ...
	}
	// ...
}
```

##### Endorser.endorseProposal

背书链码实现了可插拔，可以使用不同的ESCC，系统链码和用户链码的背书过程是不同的。

```go
// endorse the proposal by calling the ESCC
func (e *Endorser) endorseProposal(_ context.Context, chainID string, txid string, signedProp *pb.SignedProposal, proposal *pb.Proposal, response *pb.Response, simRes []byte, event *pb.ChaincodeEvent, visibility []byte, ccid *pb.ChaincodeID, txsim ledger.TxSimulator, cd ccprovider.ChaincodeDefinition) (*pb.ProposalResponse, error) {
	endorserLogger.Debugf("[%s][%s] Entry chaincode: %s", chainID, shorttxid(txid), ccid)
	defer endorserLogger.Debugf("[%s][%s] Exit", chainID, shorttxid(txid))

	// 系统链码和用户链码使用不同的ESCC
	isSysCC := cd == nil
	// 1) extract the name of the escc that is requested to endorse this chaincode
	var escc string
	// ie, "lscc" or system chaincodes
	if isSysCC {
		escc = "escc"
	} else {
		escc = cd.Endorsement()
	}

	endorserLogger.Debugf("[%s][%s] escc for chaincode %s is %s", chainID, shorttxid(txid), ccid, escc)

	// marshalling event bytes
	var err error
	var eventBytes []byte
	if event != nil {
		eventBytes, err = putils.GetBytesChaincodeEvent(event)
		if err != nil {
			return nil, errors.Wrap(err, "failed to marshal event bytes")
		}
	}

	// set version of executing chaincode
	if isSysCC {
		// if we want to allow mixed fabric levels we should
		// set syscc version to ""
		ccid.Version = util.GetSysCCVersion()
	} else {
		ccid.Version = cd.CCVersion()
	}

	// 创建背书上下文信息
	ctx := Context{
		PluginName:     escc, // 插件名称
		Channel:        chainID,
		SignedProposal: signedProp,
		ChaincodeID:    ccid,
		Event:          eventBytes,
		SimRes:         simRes,
		Response:       response,
		Visibility:     visibility,
		Proposal:       proposal,
		TxID:           txid,
	}

	// 调用插件背书
	return e.s.EndorseWithPlugin(ctx)
}
```


背书插件实现下面的接口即可。


```go
// Plugin endorses a proposal response
type Plugin interface {
	// Endorse signs the given payload(ProposalResponsePayload bytes), and optionally mutates it.
	// Returns:
	// The Endorsement: A signature over the payload, and an identity that is used to verify the signature
	// The payload that was given as input (could be modified within this function)
	// Or error on failure
	Endorse(payload []byte, sp *peer.SignedProposal) (*peer.Endorsement, []byte, error)

	// Init injects dependencies into the instance of the Plugin
	Init(dependencies ...Dependency) error
}
```

使用插件背书，需获取插件实例，然后组装响应Payload，它包含了交易执行的多种结果，然后对Payload以及签名的Proposal背书。

```go
// EndorseWithPlugin endorses the response with a plugin
func (pe *PluginEndorser) EndorseWithPlugin(ctx Context) (*pb.ProposalResponse, error) {
	endorserLogger.Debug("Entering endorsement for", ctx)

	if ctx.Response == nil {
		return nil, errors.New("response is nil")
	}

	if ctx.Response.Status >= shim.ERRORTHRESHOLD {
		return &pb.ProposalResponse{Response: ctx.Response}, nil
	}

	// 获取插件
	plugin, err := pe.getOrCreatePlugin(PluginName(ctx.PluginName), ctx.Channel)
	if err != nil {
		endorserLogger.Warning("Endorsement with plugin for", ctx, " failed:", err)
		return nil, errors.Errorf("plugin with name %s could not be used: %v", ctx.PluginName, err)
	}

	// 把模拟执行的信息组成生成背书响应Payload
	prpBytes, err := proposalResponsePayloadFromContext(ctx)
	if err != nil {
		endorserLogger.Warning("Endorsement with plugin for", ctx, " failed:", err)
		return nil, errors.Wrap(err, "failed assembling proposal response payload")
	}

	// 对Payload和签名的Proposal进行背书
	endorsement, prpBytes, err := plugin.Endorse(prpBytes, ctx.SignedProposal)
	if err != nil {
		endorserLogger.Warning("Endorsement with plugin for", ctx, " failed:", err)
		return nil, errors.WithStack(err)
	}

	resp := &pb.ProposalResponse{
		Version:     1,
		Endorsement: endorsement,
		Payload:     prpBytes,
		Response:    ctx.Response,
	}
	endorserLogger.Debug("Exiting", ctx)
	return resp, nil
}
```

系统提供的默认背书插件如下，**本质是对交易执行结果和Proposal签名人信息进行签名。**

```go
// Endorse signs the given payload(ProposalResponsePayload bytes), and optionally mutates it.
// Returns:
// The Endorsement: A signature over the payload, and an identity that is used to verify the signature
// The payload that was given as input (could be modified within this function)
// Or error on failure
func (e *DefaultEndorsement) Endorse(prpBytes []byte, sp *peer.SignedProposal) (*peer.Endorsement, []byte, error) {
	// 提取Proposal的签名人
	signer, err := e.SigningIdentityForRequest(sp)
	if err != nil {
		return nil, nil, errors.New(fmt.Sprintf("failed fetching signing identity: %v", err))
	}
	
	// 得到签名人身份
	// serialize the signing identity
	identityBytes, err := signer.Serialize()
	if err != nil {
		return nil, nil, errors.New(fmt.Sprintf("could not serialize the signing identity: %v", err))
	}

	// 对Payload和身份进行签名
	// sign the concatenation of the proposal response and the serialized endorser identity with this endorser's key
	signature, err := signer.Sign(append(prpBytes, identityBytes...))
	if err != nil {
		return nil, nil, errors.New(fmt.Sprintf("could not sign the proposal response payload: %v", err))
	}
	endorsement := &peer.Endorsement{Signature: signature, Endorser: identityBytes}
	return endorsement, prpBytes, nil
}
```

### 发送Response

`ProcessProposal` 会把 ProposalResponse 作为返回值，剩下的就交给 gRPC，发送给请求方了。



## 总结

本文从宏观和源码层面，解读了交易提案背书涉及的数据结构，以及其主要背书流程，核心可以主要包含以下几步：
1. 检查Proposal
1. 为交易创建模拟器，并调用模拟器模拟执行交易，生成执行结果
1. 背书模块对执行结果和Proposal身份信息背书（签名），然后生成背书响应发送给客户端

关于背书流程，本文未涉及的环节有：
1. Proposal中各字段，层层递进的含义
1. 模拟执行交易，是链码执行函数，并和Peer交互的过程，以及模拟执行的各种资源
1. 2种插件化ESCC的实现

后面的章节，会对相关源码实现做进一步分析。