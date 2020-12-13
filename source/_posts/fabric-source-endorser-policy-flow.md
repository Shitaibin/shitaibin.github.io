---
title: Fabric 1.4源码解读 1：背书策略是怎么使用的
date: 2019-09-06 16:39:45
tags: ['Fabric', '区块链']
---


![endorser policy](http://img.lessisbetter.site/2019-09-endorser-policy.png)

背书策略是Fabric中的一个重要一环，想梳理一下背书策略的上链和使用流程。

背书策略是部署和升级链码时使用的，需要发送配置交易，所以尝试了从背书节点收到交易，然后处理交易的流程入手，找到背书策略的入口，结果毫无头绪。

换一种思路，从使用入手，向上追溯，这种就非常顺利了。

## 从背书策略的使用入手

VSCC会利用背书策略，并且背书策略不满足时会返回一个：背书策略不满足的错误，每一个上链的交易详细中都有这么一个Validation字段，为0代表有效交易，否则是无效交易，并用数字表示原因，背书策略不满足的序号就是10。

```go
type TxValidationCode int32

const (
	...
	TxValidationCode_ENDORSEMENT_POLICY_FAILURE   TxValidationCode = 10
	...
)
```

`TxValidationCode_ENDORSEMENT_POLICY_FAILURE`被`VSCCValidateTx`使用，系统链码和普通链码都有背书策略需要满足，下面代码片是普通链码部分，可以发现调用`VSCCValidateTxForCC`验证交易。

```go
// VSCCValidateTx executes vscc validation for transaction
func (v *VsccValidatorImpl) VSCCValidateTx(seq int, payload *common.Payload, envBytes []byte, block *common.Block) (error, peer.TxValidationCode) {
  ...
  if err = v.VSCCValidateTxForCC(ctx); err != nil {
    switch err.(type) {
    case *commonerrors.VSCCEndorsementPolicyError:
      return err, peer.TxValidationCode_ENDORSEMENT_POLICY_FAILURE
    default:
      return err, peer.TxValidationCode_INVALID_OTHER_REASON
    }
  }
  ...
}
```

每个chaincode都会提供escc和vscc，现在都是默认的，也就是说escc和vscc都可以是具备可插拔的。

```
peer chaincode list -C mychannel --instantiated
Get instantiated chaincodes on channel mychannel:
Name: mycc, Version: 1.1, Path: github.com/chaincode/chaincode_example02/go/, Escc: escc, Vscc: vscc
```

`VSCCValidateTxForCC`会从交易的context中获取验证插件，然后利用插件验证交易。

```go
func (v *VsccValidatorImpl) VSCCValidateTxForCC(ctx *Context) error {
	logger.Debug("Validating", ctx, "with plugin")
  // 使用插件验证交易
	err := v.pluginValidator.ValidateWithPlugin(ctx)
	if err == nil {
		return nil
	}
	// If the error is a pluggable validation execution error, cast it to the common errors ExecutionFailureError.
	if e, isExecutionError := err.(*validation.ExecutionFailureError); isExecutionError {
		return &commonerrors.VSCCExecutionFailureError{Err: e}
	}
	// Else, treat it as an endorsement error.
	return &commonerrors.VSCCEndorsementPolicyError{Err: err}
}

func (pv *PluginValidator) ValidateWithPlugin(ctx *Context) error {
	// 获取vscc插件
	plugin, err := pv.getOrCreatePlugin(ctx)
	if err != nil {
		return &validation.ExecutionFailureError{
			Reason: fmt.Sprintf("plugin with name %s couldn't be used: %v", ctx.VSCCName, err),
		}
	}
  // 利用插件验证
	err = plugin.Validate(ctx.Block, ctx.Namespace, ctx.Seq, 0, SerializedPolicy(ctx.Policy))
	validityStatus := "valid"
	if err != nil {
		validityStatus = fmt.Sprintf("invalid: %v", err)
	}
	logger.Debug("Transaction", ctx.TxID, "appears to be", validityStatus)
	return err
}

// Plugin validates transactions
type Plugin interface {
	// Validate returns nil if the action at the given position inside the transaction
	// at the given position in the given block is valid, or an error if not.
	Validate(block *common.Block, namespace string, txPosition int, actionPosition int, contextData ...ContextDatum) error

	// Init injects dependencies into the instance of the Plugin
	Init(dependencies ...Dependency) error
}
```

当前验证插件有2种实现，`TxValidatorV1_2`和`V1_3Validation`,`Validate`还从context取出了序列化的背书策略，vscc会调用PolicyEvalutor交易的背书是否满足背书策略。

```go
func (v *DefaultValidation) Validate(block *common.Block, namespace string, txPosition int, actionPosition int, contextData ...validation.ContextDatum) error {
	if len(contextData) == 0 {
		logger.Panicf("Expected to receive policy bytes in context data")
	}

	// 拿到序列化后的policy
	serializedPolicy, isSerializedPolicy := contextData[0].(SerializedPolicy)
	if !isSerializedPolicy {
		logger.Panicf("Expected to receive a serialized policy in the first context data")
	}
	if block == nil || block.Data == nil {
		return errors.New("empty block")
	}
	if txPosition >= len(block.Data.Data) {
		return errors.Errorf("block has only %d transactions, but requested tx at position %d", len(block.Data.Data), txPosition)
	}
	if block.Header == nil {
		return errors.Errorf("no block header")
	}

	// 调用不同版本的validator进行验证
	var err error
	switch {
	case v.Capabilities.V1_3Validation():
		err = v.TxValidatorV1_3.Validate(block, namespace, txPosition, actionPosition, serializedPolicy.Bytes())

	case v.Capabilities.V1_2Validation():
		fallthrough

	default:
		err = v.TxValidatorV1_2.Validate(block, namespace, txPosition, actionPosition, serializedPolicy.Bytes())
	}

	logger.Debugf("block %d, namespace: %s, tx %d validation results is: %v", block.Header.Number, namespace, txPosition, err)
	return convertErrorTypeOrPanic(err)
}

// 验证代码使用v2/validation_logic.go中的实现
// Validate validates the given envelope corresponding to a transaction with an endorsement
// policy as given in its serialized form
func (vscc *Validator) Validate(
	block *common.Block,
	namespace string,
	txPosition int,
	actionPosition int,
	policyBytes []byte,
) commonerrors.TxValidationError {
  ...
  // evaluate the signature set against the policy
  err = vscc.policyEvaluator.Evaluate(policyBytes, signatureSet)
  if err != nil {
    logger.Warningf("Endorsement policy failure for transaction txid=%s, err: %s", chdr.GetTxId(), err.Error())
    if len(signatureSet) < len(cap.Action.Endorsements) {
      // Warning: duplicated identities exist, endorsement failure might be cause by this reason
      return policyErr(errors.New(DUPLICATED_IDENTITY_ERROR))
    }
    return policyErr(fmt.Errorf("VSCC error: endorsement policy failure, err: %s", err))
  }
  ...
}

// PolicyEvaluator evaluates policies
type PolicyEvaluator interface {
	validation.Dependency

	// Evaluate takes a set of SignedData and evaluates whether this set of signatures satisfies
	// the policy with the given bytes
	Evaluate(policyBytes []byte, signatureSet []*common.SignedData) error
}

```

`Evaluate`会创建背书策略实例，然后利用背书策略验证背书签名。

```
// Evaluate takes a set of SignedData and evaluates whether this set of signatures satisfies the policy
func (id *PolicyEvaluator) Evaluate(policyBytes []byte, signatureSet []*common.SignedData) error {
	pp := cauthdsl.NewPolicyProvider(id.IdentityDeserializer)
	policy, _, err := pp.NewPolicy(policyBytes)
	if err != nil {
		return err
	}
	return policy.Evaluate(signatureSet)
}

// Policy is used to determine if a signature is valid
type Policy interface {
	// Evaluate takes a set of SignedData and evaluates whether this set of signatures satisfies the policy
	Evaluate(signatureSet []*cb.SignedData) error
}

// Evaluate takes a set of SignedData and evaluates whether this set of signatures satisfies the policy
func (p *policy) Evaluate(signatureSet []*cb.SignedData) error {
	if p == nil {
		return fmt.Errorf("No such policy")
	}
	idAndS := make([]IdentityAndSignature, len(signatureSet))
	for i, sd := range signatureSet {
		idAndS[i] = &deserializeAndVerify{
			signedData:   sd,
			deserializer: p.deserializer,
		}
	}

	ok := p.evaluator(deduplicate(idAndS), make([]bool, len(signatureSet)))
	if !ok {
		return errors.New("signature set did not satisfy policy")
	}
	return nil
}
```

具体背书验证签名的实现，当下就先不关心了。**回过头来想一下，VSCC从哪拿到了背书策略？**





## VSCC的背书策略哪来的？

回到上文第一次出现背书策略的地方：

```
func (pv *PluginValidator) ValidateWithPlugin(ctx *Context) error {
  err = plugin.Validate(ctx.Block, ctx.Namespace, ctx.Seq, 0, SerializedPolicy(ctx.Policy))
}

// Context defines information about a transaction
// that is being validated
type Context struct {
	Seq       int
	Envelope  []byte
	TxID      string
	Channel   string
	VSCCName  string
	Policy    []byte // 背书策略
	Namespace string
	Block     *common.Block
}
```

`VSCCValidateTx`函数会创建Context，填写policy字段，其中policy是调用`GetInfoForValidate`获取的。

```go
func (v *VsccValidatorImpl) VSCCValidateTx(seq int, payload *common.Payload, envBytes []byte, block *common.Block) (error, peer.TxValidationCode) {
  ...
  // 普通链码
  if !v.sccprovider.IsSysCC(ccID) {
    ...
    // 获取policy、vscc等
    // Get latest chaincode version, vscc and validate policy
    txcc, vscc, policy, err := v.GetInfoForValidate(chdr, ns)
    ...
    // do VSCC validation
    ctx := &Context{
      Seq:       seq,
      Envelope:  envBytes,
      Block:     block,
      TxID:      chdr.TxId,
      Channel:   chdr.ChannelId,
      Namespace: ns,
      Policy:    policy, // Here
      VSCCName:  vscc.ChaincodeName,
    }
    if err = v.VSCCValidateTxForCC(ctx); err != nil {
      switch err.(type) {
      case *commonerrors.VSCCEndorsementPolicyError:
        return err, peer.TxValidationCode_ENDORSEMENT_POLICY_FAILURE
      default:
        return err, peer.TxValidationCode_INVALID_OTHER_REASON
      }
    }
  } else {
  // SCC
  }
}
```

`GetInfoForValidate`先是获取了`ChaincodeDefinition`，它记录了peer对某个链码的proposal背书和验证的必要信息，然后利用`ChaincodeDefinition.Validation`获取了policy。

```go
// GetInfoForValidate gets the ChaincodeInstance(with latest version) of tx, vscc and policy from lscc
func (v *VsccValidatorImpl) GetInfoForValidate(chdr *common.ChannelHeader, ccID string) (*sysccprovider.ChaincodeInstance, *sysccprovider.ChaincodeInstance, []byte, error) {
	cc := &sysccprovider.ChaincodeInstance{
		ChainID:          chdr.ChannelId,
		ChaincodeName:    ccID,
		ChaincodeVersion: coreUtil.GetSysCCVersion(),
	}
	vscc := &sysccprovider.ChaincodeInstance{
		ChainID:          chdr.ChannelId,
		ChaincodeName:    "vscc",                     // default vscc for system chaincodes
		ChaincodeVersion: coreUtil.GetSysCCVersion(), // Get vscc version
	}
	var policy []byte
	var err error
	if !v.sccprovider.IsSysCC(ccID) {
		// when we are validating a chaincode that is not a
		// system CC, we need to ask the CC to give us the name
		// of VSCC and of the policy that should be used

		// obtain name of the VSCC and the policy
		// 获取cc 定义
		cd, err := v.getCDataForCC(chdr.ChannelId, ccID)
		if err != nil {
			msg := fmt.Sprintf("Unable to get chaincode data from ledger for txid %s, due to %s", chdr.TxId, err)
			logger.Errorf(msg)
			return nil, nil, nil, err
		}
		cc.ChaincodeName = cd.CCName()
		cc.ChaincodeVersion = cd.CCVersion()
		// 拿到policy
		vscc.ChaincodeName, policy = cd.Validation()
	} else {
		// when we are validating a system CC, we use the default
		// VSCC and a default policy that requires one signature
		// from any of the members of the channel
		p := cauthdsl.SignedByAnyMember(v.support.GetMSPIDs(chdr.ChannelId))
		policy, err = utils.Marshal(p)
		if err != nil {
			return nil, nil, nil, err
		}
	}

	return cc, vscc, policy, nil
}

//-------- ChaincodeDefinition - interface for ChaincodeData ------
// ChaincodeDefinition describes all of the necessary information for a peer to decide whether to endorse
// a proposal and whether to validate a transaction, for a particular chaincode.
type ChaincodeDefinition interface {
	// CCName returns the name of this chaincode (the name it was put in the ChaincodeRegistry with).
	CCName() string

	// Hash returns the hash of the chaincode.
	Hash() []byte

	// CCVersion returns the version of the chaincode.
	CCVersion() string

	// Validation returns how to validate transactions for this chaincode.
	// The string returned is the name of the validation method (usually 'vscc')
	// and the bytes returned are the argument to the validation (in the case of
	// 'vscc', this is a marshaled pb.VSCCArgs message).
	Validation() (string, []byte)

	// Endorsement returns how to endorse proposals for this chaincode.
	// The string returns is the name of the endorsement method (usually 'escc').
	Endorsement() string
}
```

`ChaincodeData`实现了`ChaincodeDefinition`接口，`ChaincodeData`是LSCC保存的数据，它其中有1个字段就是Policy。

```go
// Validation returns how to validate transactions for this chaincode.
// The string returned is the name of the validation method (usually 'vscc')
// and the bytes returned are the argument to the validation (in the case of
// 'vscc', this is a marshaled pb.VSCCArgs message).
func (cd *ChaincodeData) Validation() (string, []byte) {
	return cd.Vscc, cd.Policy
}

//-------- ChaincodeData is stored on the LSCC -------

// ChaincodeData defines the datastructure for chaincodes to be serialized by proto
// Type provides an additional check by directing to use a specific package after instantiation
// Data is Type specifc (see CDSPackage and SignedCDSPackage)
type ChaincodeData struct {
	// Name of the chaincode
	Name string `protobuf:"bytes,1,opt,name=name"`

	// Version of the chaincode
	Version string `protobuf:"bytes,2,opt,name=version"`

	// Escc for the chaincode instance
	Escc string `protobuf:"bytes,3,opt,name=escc"`

	// Vscc for the chaincode instance
	Vscc string `protobuf:"bytes,4,opt,name=vscc"`

	// 背书策略
	// Policy endorsement policy for the chaincode instance
	Policy []byte `protobuf:"bytes,5,opt,name=policy,proto3"`

	// Data data specific to the package
	Data []byte `protobuf:"bytes,6,opt,name=data,proto3"`

	// Id of the chaincode that's the unique fingerprint for the CC This is not
	// currently used anywhere but serves as a good eyecatcher
	Id []byte `protobuf:"bytes,7,opt,name=id,proto3"`

	// InstantiationPolicy for the chaincode
	InstantiationPolicy []byte `protobuf:"bytes,8,opt,name=instantiation_policy,proto3"`
}
```

## LSCC的Policy哪来的？

> 提醒：链码实例化在代码里使用**Deploy**，而不是Instantiate，这样可以让代码更简洁，所以链码实例化也常称为链码部署。

`executeDeploy`为部署链码，也就是在部署链码的时候会保存背书策略。

```go
// executeDeploy implements the "instantiate" Invoke transaction
func (lscc *LifeCycleSysCC) executeDeploy(
	stub shim.ChaincodeStubInterface,
	chainname string,
	cds *pb.ChaincodeDeploymentSpec,
	policy []byte,
	escc []byte,
	vscc []byte,
	cdfs *ccprovider.ChaincodeData,
	ccpackfs ccprovider.CCPackage,
	collectionConfigBytes []byte,
) (*ccprovider.ChaincodeData, error) {
	//just test for existence of the chaincode in the LSCC
	chaincodeName := cds.ChaincodeSpec.ChaincodeId.Name
	_, err := lscc.getCCInstance(stub, chaincodeName)
	if err == nil {
		return nil, ExistsErr(chaincodeName)
	}

	//retain chaincode specific data and fill channel specific ones
	cdfs.Escc = string(escc)
	cdfs.Vscc = string(vscc)
	// 保存背书策略
	cdfs.Policy = policy
}
```

`executeDeployOrUpgrade`是执行链码实例化和升级时调用，它会传递Policy，在链码部署和升级时都会保存背书策略。

```go
// executeDeployOrUpgrade routes the code path either to executeDeploy or executeUpgrade
// depending on its function argument
func (lscc *LifeCycleSysCC) executeDeployOrUpgrade(
	stub shim.ChaincodeStubInterface,
	chainname string,
	cds *pb.ChaincodeDeploymentSpec,
	policy, escc, vscc, collectionConfigBytes []byte,
	function string,
) (*ccprovider.ChaincodeData, error) {

	chaincodeName := cds.ChaincodeSpec.ChaincodeId.Name
	chaincodeVersion := cds.ChaincodeSpec.ChaincodeId.Version

	if err := lscc.isValidChaincodeName(chaincodeName); err != nil {
		return nil, err
	}

	if err := lscc.isValidChaincodeVersion(chaincodeName, chaincodeVersion); err != nil {
		return nil, err
	}

	ccpack, err := lscc.Support.GetChaincodeFromLocalStorage(chaincodeName, chaincodeVersion)
	if err != nil {
		retErrMsg := fmt.Sprintf("cannot get package for chaincode (%s:%s)", chaincodeName, chaincodeVersion)
		logger.Errorf("%s-err:%s", retErrMsg, err)
		return nil, fmt.Errorf("%s", retErrMsg)
	}
	cd := ccpack.GetChaincodeData()

	switch function {
	case DEPLOY:
		return lscc.executeDeploy(stub, chainname, cds, policy, escc, vscc, cd, ccpack, collectionConfigBytes)
	case UPGRADE:
		return lscc.executeUpgrade(stub, chainname, cds, policy, escc, vscc, cd, ccpack, collectionConfigBytes)
	default:
		logger.Panicf("Programming error, unexpected function '%s'", function)
		panic("") // unreachable code
	}
}
```

LSCC也实现了ChainCode接口，与普通链码的实现并没有区别，只不过LSCC并不运行在容器中。`LifeCycleSysCC.Invoke`会根据参数调用不同的函数，而部署和升级时，会调用`executeDeployOrUpgrade`部署链码。

```go
// Invoke implements lifecycle functions "deploy", "start", "stop", "upgrade".
// Deploy's arguments -  {[]byte("deploy"), []byte(<chainname>), <unmarshalled pb.ChaincodeDeploymentSpec>}
//
// Invoke also implements some query-like functions
// Get chaincode arguments -  {[]byte("getid"), []byte(<chainname>), []byte(<chaincodename>)}
func (lscc *LifeCycleSysCC) Invoke(stub shim.ChaincodeStubInterface) pb.Response {
  ...
  switch function {
    case INSTALL:
      ...
    case DEPLOY, UPGRADE:
      // 提取背书策略
      // optional arguments here (they can each be nil and may or may not be present)
      // args[3] is a marshalled SignaturePolicyEnvelope representing the endorsement policy
      // args[4] is the name of escc
      // args[5] is the name of vscc
      // args[6] is a marshalled CollectionConfigPackage struct
      var EP []byte
      if len(args) > 3 && len(args[3]) > 0 {
        EP = args[3]
      } else {
        p := cauthdsl.SignedByAnyMember(peer.GetMSPIDs(channel))
        EP, err = utils.Marshal(p)
        if err != nil {
          return shim.Error(err.Error())
        }
      }
      ...
      cd, err := lscc.executeDeployOrUpgrade(stub, channel, cds, EP, escc, vscc, collectionsConfig, function)
      ...
    case ...:
      ...
  }
}  
```

## 总结

我们终于知道Policy是哪来的，又是如何被使用的了。管理和查看链码信息，本质是创建一个调用LSCC的Proposal或者交易，链码的信息会保存在LSCC，当VSCC验证链码的交易时，会从LSCC获取信息，包括背书策略、vscc插件等，以验证交易。

最后，ESCC、VSCC也是进行了可插拔设计的。

![endorser policy](http://img.lessisbetter.site/2019-09-endorser-policy.png)




