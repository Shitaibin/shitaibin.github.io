---
title: Fabric 1.4源码解读 2：系统链码SCC是如何部署的
date: 2019-09-11 11:37:27
tags: ['Fabric', '区块链']
---

## 前言

一份Peer节点启动的INFO级别日志如下，可以发现：
1. 先注册了scc目录下的lscc, cscc, qscc，未注册chaincode目录下的lifecycle
1. 然后又依次部署了上述scc。

本文的目的就是梳理出，系统链码的部署流程，这是peer节点提供背书、链码管理、配置、查询等功能的基础。

```
2019-09-09 07:52:09.409 UTC [gossip.gossip] start -> INFO 013 Gossip instance peer1.org1.example.com:8051 started
2019-09-09 07:52:09.418 UTC [sccapi] deploySysCC -> INFO 014 system chaincode lscc/(github.com/hyperledger/fabric/core/scc/lscc) deployed
2019-09-09 07:52:09.420 UTC [cscc] Init -> INFO 015 Init CSCC
2019-09-09 07:52:09.422 UTC [sccapi] deploySysCC -> INFO 016 system chaincode cscc/(github.com/hyperledger/fabric/core/scc/cscc) deployed
2019-09-09 07:52:09.424 UTC [qscc] Init -> INFO 017 Init QSCC
2019-09-09 07:52:09.424 UTC [sccapi] deploySysCC -> INFO 018 system chaincode qscc/(github.com/hyperledger/fabric/core/scc/qscc) deployed
2019-09-09 07:52:09.425 UTC [sccapi] deploySysCC -> INFO 019 system chaincode (+lifecycle,github.com/hyperledger/fabric/core/chaincode/lifecycle) disabled
...
2019-09-09 07:52:14.386 UTC [sccapi] deploySysCC -> INFO 031 system chaincode lscc/mychannel(github.com/hyperledger/fabric/core/scc/lscc) deployed
2019-09-09 07:52:14.386 UTC [cscc] Init -> INFO 032 Init CSCC
2019-09-09 07:52:14.386 UTC [sccapi] deploySysCC -> INFO 033 system chaincode cscc/mychannel(github.com/hyperledger/fabric/core/scc/cscc) deployed
2019-09-09 07:52:14.387 UTC [qscc] Init -> INFO 034 Init QSCC
2019-09-09 07:52:14.387 UTC [sccapi] deploySysCC -> INFO 035 system chaincode qscc/mychannel(github.com/hyperledger/fabric/core/scc/qscc) deployed
2019-09-09 07:52:14.387 UTC [sccapi] deploySysCC -> INFO 036 system chaincode (+lifecycle,github.com/hyperledger/fabric/core/chaincode/lifecycle) disabled
```

## 宏观流程

> 提醒，本文使用**SCC代指系统链码**，使用scc代指core.scc模块。

在介绍源码之前，先给出总体流程，以便看源码的时候不会迷失。

部署SCC会涉及到4个模块：
1. peer.node，它是peer的主程序，可以调用core.scc进行注册和部署SCC
1. core.scc，它包含了lscc、qscc、cscc这3个scc，以及SCC的注册和部署
1. core.chaincode，它是链码管理，普通链码和SCC都会走该模块，去部署和调用链码，和链码容器交互，并且它还提供了1个链码容器的工具shim
1. core.container，它是实现链码容器，有2种链码容器，SCC使用的InprocVM，和普通链码使用的DockerVM

注册和部署的简要流程如下：

![](http://img.lessisbetter.site/2019-09-deploy-scc-flow.png)


1. peer运行启动程序
2. 注册scc
    1. peer.node创建好lscc、cscc、qscc等scc实例，以及从配置文件读取的scc
    1. peer.node调用core.scc依次注册每一个scc实例
    1. core.scc调用core.container把scc实例信息注册到container
3. 部署scc
    1. peer.node调用core.scc依次部署每一个注册的scc
    1. core.scc部署scc的流程复用普通链码部署流程，调用core.chaincode
    1. core.chaincode执行启动链码容器，scc也有链码容器是Inproc类型，不是Docker类型
    1. core.chaincode会调用core.container建立scc的Inproc容器实例
    1. core.container调用core.chaincode.shim启动容器内的程序，并负责和peer通信
    1. 启动完成后，core.chaincode向容器发送Init消息，让容器初始化，容器初始化完成会发送响应消息给core.chaincode，core.chaincode部署scc完成



## 总流程

> 列出源码的过程，会省略大量不相关代码，用`...`代替。

peer启动过程中，会调用`node.serve`，其中包含了为系统链码注册SCC和部署SCC。之后，还会为应用通道部署SCC，说明每个通道有各自的SCC，这里省略掉这部分。

```go
func serve(args []string) error {
    ...
    // 获取support，会注册SCC
    // Initialize chaincode service
    chaincodeSupport, ccp, sccp, packageProvider := startChaincodeServer(peerHost, aclProvider, pr, opsSystem)
    ...
    // 为系统通道部署已经注册的SCC
    // deploy system chaincodes
	sccp.DeploySysCCs("", ccp)
	logger.Infof("Deployed system chaincodes")
    ...
}
```

## 注册SCC

注册SCC的流程：

peer.node -> core.scc -> core.container


### peer.node

```go
// startChaincodeServer will finish chaincode related initialization, including:
// 1) setup local chaincode install path
// 2) create chaincode specific tls CA
// 3) start the chaincode specific gRPC listening service
func startChaincodeServer(
	peerHost string,
	aclProvider aclmgmt.ACLProvider,
	pr *platforms.Registry,
	ops *operations.System,
) (*chaincode.ChaincodeSupport, ccprovider.ChaincodeProvider, *scc.Provider, *persistence.PackageProvider) {
    ...
	// 会注册SCC
	chaincodeSupport, ccp, sccp := registerChaincodeSupport(
		ccSrv,
		ccEndpoint,
		ca,
		packageProvider,
		aclProvider,
		pr,
		lifecycleSCC,
		ops,
	)
	go ccSrv.Start()
	return chaincodeSupport, ccp, sccp, packageProvider
}

func registerChaincodeSupport(
	grpcServer *comm.GRPCServer,
	ccEndpoint string,
	ca tlsgen.CA,
	packageProvider *persistence.PackageProvider,
	aclProvider aclmgmt.ACLProvider,
	pr *platforms.Registry,
	lifecycleSCC *lifecycle.SCC,
	ops *operations.System,
) (*chaincode.ChaincodeSupport, ccprovider.ChaincodeProvider, *scc.Provider) {
	...
	// SCC的VM provider
	ipRegistry := inproccontroller.NewRegistry()

	// 创建SCC provider
	sccp := scc.NewProvider(peer.Default, peer.DefaultSupport, ipRegistry)
	// 创建lscc实例
    lsccInst := lscc.New(sccp, aclProvider, pr)
    
    // 普通链码，docker容器类型的VM provider
	dockerProvider := dockercontroller.NewProvider(
		viper.GetString("peer.id"),
		viper.GetString("peer.networkId"),
		ops.Provider,
	)
	dockerVM := dockercontroller.NewDockerVM(
		dockerProvider.PeerID,
		dockerProvider.NetworkID,
		dockerProvider.BuildMetrics,
	)
    ...
    chaincodeSupport := chaincode.NewChaincodeSupport(
		chaincode.GlobalConfig(),
		ccEndpoint,
		userRunsCC,
		ca.CertBytes(),
		authenticator,
		packageProvider,
		lsccInst, // chaincodeSupport的声明周期管理使用了lscc，而不是lifecycle
		aclProvider,
		container.NewVMController(
			map[string]container.VMProvider{
				dockercontroller.ContainerType: dockerProvider,
				inproccontroller.ContainerType: ipRegistry,
			},
		),
		sccp,
		pr,
		peer.DefaultSupport,
		ops.Provider,
	)
	ipRegistry.ChaincodeSupport = chaincodeSupport
	// chaincode provider，可以用来创建cscc
	ccp := chaincode.NewProvider(chaincodeSupport)
    ...
    // 创建cscc、qscc
	csccInst := cscc.New(ccp, sccp, aclProvider)
	qsccInst := qscc.New(aclProvider)

	//Now that chaincode is initialized, register all system chaincodes.
	sccs := scc.CreatePluginSysCCs(sccp)
	// 加入lscc、cscc、qscc
	// lifecycleSCC在1.4中disable了
	// sccs是用户自定义的系统链码
	for _, cc := range append([]scc.SelfDescribingSysCC{lsccInst, csccInst, qsccInst, lifecycleSCC}, sccs...) {
		// 注册每一个SCC
		sccp.RegisterSysCC(cc)
    }
    ...
	return chaincodeSupport, ccp, sccp
}
```

### core.scc

注册某1个系统合约。

```go
// Provider implements sysccprovider.SystemChaincodeProvider
type Provider struct {
	Peer        peer.Operations
	PeerSupport peer.Support
	Registrar   Registrar             // 注册
	SysCCs      []SelfDescribingSysCC // 注册的scc，包含失败的
}

// RegisterSysCC registers a system chaincode with the syscc provider.
func (p *Provider) RegisterSysCC(scc SelfDescribingSysCC) {
	// 收集/注册scc到scc provider
	p.SysCCs = append(p.SysCCs, scc)
	_, err := p.registerSysCC(scc)
	if err != nil {
		sysccLogger.Panicf("Could not register system chaincode: %s", err)
	}
}

// registerSysCC registers the given system chaincode with the peer
func (p *Provider) registerSysCC(syscc SelfDescribingSysCC) (bool, error) {
	// 检测该scc是否开启或不在白名单
	if !syscc.Enabled() || !isWhitelisted(syscc) {
		sysccLogger.Info(fmt.Sprintf("system chaincode (%s,%s,%t) disabled", syscc.Name(), syscc.Path(), syscc.Enabled()))
		return false, nil
	}

	// XXX This is an ugly hack, version should be tied to the chaincode instance, not he peer binary
	version := util.GetSysCCVersion()

	// cc的描述信息
	ccid := &ccintf.CCID{
		Name:    syscc.Name(),
		Version: version,
	}
	// 注册scc的chaincode
	err := p.Registrar.Register(ccid, syscc.Chaincode())
	if err != nil {
		//if the type is registered, the instance may not be... keep going
		if _, ok := err.(inproccontroller.SysCCRegisteredErr); !ok {
			errStr := fmt.Sprintf("could not register (%s,%v): %s", syscc.Path(), syscc, err)
			sysccLogger.Error(errStr)
			return false, fmt.Errorf(errStr)
		}
	}

	sysccLogger.Infof("system chaincode %s(%s) registered", syscc.Name(), syscc.Path())
	return true, err
}

// Registrar provides a way for system chaincodes to be registered
type Registrar interface {
	// Register registers a system chaincode
	Register(ccid *ccintf.CCID, cc shim.Chaincode) error
}
```

### core.container

```go
//Register registers system chaincode with given path. The deploy should be called to initialize
func (r *Registry) Register(ccid *ccintf.CCID, cc shim.Chaincode) error {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	// 注册系统链码
	name := ccid.GetName()
	inprocLogger.Debugf("Registering chaincode instance: %s", name)
	tmp := r.typeRegistry[name]
	if tmp != nil {
		return SysCCRegisteredErr(name)
	}

	r.typeRegistry[name] = &inprocContainer{chaincode: cc}
	return nil
}


// Registry stores registered system chaincodes.
// It implements container.VMProvider and scc.Registrar
type Registry struct {
	mutex        sync.Mutex
	typeRegistry map[string]*inprocContainer // 已注册链码映射
	instRegistry map[string]*inprocContainer // 链码示例映射

	ChaincodeSupport ccintf.CCSupport
}
```

## 部署SCC

部署SCC的流程：

peer.node -> core.scc -> core.chaincode -> core.container


### peer.node

```go
func serve(args []string) error {
    ...
	// 为系统通道部署已经注册的SCC
	// deploy system chaincodes
	sccp.DeploySysCCs("", ccp)
    logger.Infof("Deployed system chaincodes")
    ...
}
```

### core.scc

`DeploySysCCs`会为chainID对应的channel，部署注册过程中收集的每一个SCC，它们在`p.SysCCs`中。

部署链码实际是一笔交易，为了复用普通链码的部署流程，core.scc使用`deploySysCC`封装部署链码需要的参数，链码是实际部署，走core.chaincode流程。

```go
//DeploySysCCs is the hook for system chaincodes where system chaincodes are registered with the fabric
//note the chaincode must still be deployed and launched like a user chaincode will be
func (p *Provider) DeploySysCCs(chainID string, ccp ccprovider.ChaincodeProvider) {
	// 部署每一个scc
	for _, sysCC := range p.SysCCs {
		deploySysCC(chainID, ccp, sysCC)
	}
}

// deploySysCC deploys the given system chaincode on a chain
func deploySysCC(chainID string, ccprov ccprovider.ChaincodeProvider, syscc SelfDescribingSysCC) error {
	// disable或不在白名单的scc不执行部署
	if !syscc.Enabled() || !isWhitelisted(syscc) {
		sysccLogger.Info(fmt.Sprintf("system chaincode (%s,%s) disabled", syscc.Name(), syscc.Path()))
		return nil
	}

	// 为scc生成txid，因为部署链码的过程需要txParams，与普通链码的流程相同
	txid := util.GenerateUUID()

	// Note, this structure is barely initialized,
	// we omit the history query executor, the proposal
	// and the signed proposal
	txParams := &ccprovider.TransactionParams{
		TxID:      txid,
		ChannelID: chainID,
	}

	// 设置交易执行模拟器，系统通道chainID为""，所以系统通道的scc没有模拟器
	if chainID != "" {
		// 获取链/通道的账本
		lgr := peer.GetLedger(chainID)
		if lgr == nil {
			panic(fmt.Sprintf("syschain %s start up failure - unexpected nil ledger for channel %s", syscc.Name(), chainID))
		}

		// 根据交易id创建链码模拟器
		txsim, err := lgr.NewTxSimulator(txid)
		if err != nil {
			return err
		}

		// 指定链码执行模拟器
		txParams.TXSimulator = txsim
		defer txsim.Done()
	}

	chaincodeID := &pb.ChaincodeID{Path: syscc.Path(), Name: syscc.Name()}
	spec := &pb.ChaincodeSpec{Type: pb.ChaincodeSpec_Type(pb.ChaincodeSpec_Type_value["GOLANG"]), ChaincodeId: chaincodeID, Input: &pb.ChaincodeInput{Args: syscc.InitArgs()}}

	// ChaincodeDeploymentSpec_SYSTEM标明：部署SCC
	chaincodeDeploymentSpec := &pb.ChaincodeDeploymentSpec{ExecEnv: pb.ChaincodeDeploymentSpec_SYSTEM, ChaincodeSpec: spec}

	// XXX This is an ugly hack, version should be tied to the chaincode instance, not he peer binary
	version := util.GetSysCCVersion()

	cccid := &ccprovider.CCContext{
		Name:    chaincodeDeploymentSpec.ChaincodeSpec.ChaincodeId.Name,
		Version: version,
	}

	// 部署SCC
	resp, _, err := ccprov.ExecuteLegacyInit(txParams, cccid, chaincodeDeploymentSpec)
	if err == nil && resp.Status != shim.OK {
		err = errors.New(resp.Message)
	}

	sysccLogger.Infof("system chaincode %s/%s(%s) deployed", syscc.Name(), chainID, syscc.Path())

	return err
}


// ChaincodeProvider provides an abstraction layer that is
// used for different packages to interact with code in the
// chaincode package without importing it; more methods
// should be added below if necessary
type ChaincodeProvider interface {
	// Execute executes a standard chaincode invocation for a chaincode and an input
	Execute(txParams *TransactionParams, cccid *CCContext, input *pb.ChaincodeInput) (*pb.Response, *pb.ChaincodeEvent, error)
	// ExecuteLegacyInit is a special case for executing chaincode deployment specs,
	// which are not already in the LSCC, needed for old lifecycle
	ExecuteLegacyInit(txParams *TransactionParams, cccid *CCContext, spec *pb.ChaincodeDeploymentSpec) (*pb.Response, *pb.ChaincodeEvent, error)
	// Stop stops the chaincode give
	Stop(ccci *ChaincodeContainerInfo) error
}
```

### core.chaincode

`CCProviderImpl`实现了`ChaincodeProvider`接口，可以用来部署链码，`ExecuteLegacyInit`会执行2项：
1. 启动链码容器
1. 执行链码Init函数，链码容器启动后，peer和链码容器通过消息通信，`ChaincodeMessage_INIT`是执行链码容器的Init函数

```go
// ExecuteLegacyInit executes a chaincode which is not in the LSCC table
func (c *CCProviderImpl) ExecuteLegacyInit(txParams *ccprovider.TransactionParams, cccid *ccprovider.CCContext, spec *pb.ChaincodeDeploymentSpec) (*pb.Response, *pb.ChaincodeEvent, error) {
	return c.cs.ExecuteLegacyInit(txParams, cccid, spec)
}


// ExecuteLegacyInit is a temporary method which should be removed once the old style lifecycle
// is entirely deprecated.  Ideally one release after the introduction of the new lifecycle.
// It does not attempt to start the chaincode based on the information from lifecycle, but instead
// accepts the container information directly in the form of a ChaincodeDeploymentSpec.
func (cs *ChaincodeSupport) ExecuteLegacyInit(txParams *ccprovider.TransactionParams, cccid *ccprovider.CCContext, spec *pb.ChaincodeDeploymentSpec) (*pb.Response, *pb.ChaincodeEvent, error) {
	// 部署链码需要的信息
    ccci := ccprovider.DeploymentSpecToChaincodeContainerInfo(spec)
	ccci.Version = cccid.Version

	// 启动容器
	err := cs.LaunchInit(ccci)
	if err != nil {
		return nil, nil, err
	}

	cname := ccci.Name + ":" + ccci.Version
	h := cs.HandlerRegistry.Handler(cname)
	if h == nil {
		return nil, nil, errors.Wrapf(err, "[channel %s] claimed to start chaincode container for %s but could not find handler", txParams.ChannelID, cname)
	}

	// 调用链码Init
	resp, err := cs.execute(pb.ChaincodeMessage_INIT, txParams, cccid, spec.GetChaincodeSpec().Input, h)
	return processChaincodeExecutionResult(txParams.TxID, cccid.Name, resp, err)
}
```

`LaunchInit`是启动容器的一层检查，实际启动由`Launcher.Launch`完成。启动链码容器是异步的，会创建单独的goroutine去执行。


core.chaincode使用`Runtime`接口操控链码容器的启停。

```go
// LaunchInit bypasses getting the chaincode spec from the LSCC table
// as in the case of v1.0-v1.2 lifecycle, the chaincode will not yet be
// defined in the LSCC table
func (cs *ChaincodeSupport) LaunchInit(ccci *ccprovider.ChaincodeContainerInfo) error {
	cname := ccci.Name + ":" + ccci.Version
	// 已经有handler，即容器已经启动。调用链码的时候，也会获取handler
	if cs.HandlerRegistry.Handler(cname) != nil {
		return nil
	}

	// 否则启动容器，设置handler
	return cs.Launcher.Launch(ccci)
}

func (r *RuntimeLauncher) Launch(ccci *ccprovider.ChaincodeContainerInfo) error {
	var startFailCh chan error
	var timeoutCh <-chan time.Time

	startTime := time.Now()
	cname := ccci.Name + ":" + ccci.Version
	launchState, alreadyStarted := r.Registry.Launching(cname)
	// 链码容器未启动，启动容器
	if !alreadyStarted {
		startFailCh = make(chan error, 1)
		timeoutCh = time.NewTimer(r.StartupTimeout).C

		codePackage, err := r.getCodePackage(ccci)
		if err != nil {
			return err
		}

		go func() {
			// 启动容器
			if err := r.Runtime.Start(ccci, codePackage); err != nil {
				startFailCh <- errors.WithMessage(err, "error starting container")
				return
			}
			exitCode, err := r.Runtime.Wait(ccci)
			if err != nil {
				launchState.Notify(errors.Wrap(err, "failed to wait on container exit"))
			}
			launchState.Notify(errors.Errorf("container exited with %d", exitCode))
		}()
	}
  ...
}

// Runtime is used to manage chaincode runtime instances.
type Runtime interface {
	Start(ccci *ccprovider.ChaincodeContainerInfo, codePackage []byte) error
	Stop(ccci *ccprovider.ChaincodeContainerInfo) error
	Wait(ccci *ccprovider.ChaincodeContainerInfo) (int, error)
}
```


`ContainerRuntime`是core.chaincode封装出来和core.container交互的，在这里它会创建启动链码请求，交给container。

```go
// Start launches chaincode in a runtime environment.
func (c *ContainerRuntime) Start(ccci *ccprovider.ChaincodeContainerInfo, codePackage []byte) error {
	cname := ccci.Name + ":" + ccci.Version

	lc, err := c.LaunchConfig(cname, ccci.Type)
	if err != nil {
		return err
	}

	chaincodeLogger.Debugf("start container: %s", cname)
	chaincodeLogger.Debugf("start container with args: %s", strings.Join(lc.Args, " "))
	chaincodeLogger.Debugf("start container with env:\n\t%s", strings.Join(lc.Envs, "\n\t"))

	// 启动链码的请求
	scr := container.StartContainerReq{
		Builder: &container.PlatformBuilder{
			Type:             ccci.Type,
			Name:             ccci.Name,
			Version:          ccci.Version,
			Path:             ccci.Path,
			CodePackage:      codePackage,
			PlatformRegistry: c.PlatformRegistry,
		},
		Args:          lc.Args,
		Env:           lc.Envs,
		FilesToUpload: lc.Files,
		CCID: ccintf.CCID{
			Name:    ccci.Name,
			Version: ccci.Version,
		},
	}

	// 处理容器操作请求
	if err := c.Processor.Process(ccci.ContainerType, scr); err != nil {
		return errors.WithMessage(err, "error starting container")
	}

	return nil
}


// Processor processes vm and container requests.
type Processor interface {
	Process(vmtype string, req container.VMCReq) error
}
```

### core.container

`VMController`实现了Processor，它会按指定的类型建立虚拟机，明明就是容器，为啥内部又叫VM，VM有2种：
1. InprocVM，意思是运行在单独进程中的虚拟机，但不是指操作系统的进程，而是指一个隔离的环境，SCC是这类。
1. DockerVM，指利用Docker启动的容器，普通链码就是这类。


类型是存在`ccci.ContainerType`中的，`ccci`包含了部署链码所需要的信息，这个信息在core.chaincode很早就获取到了，可以往前翻。

`Process`就是创建VM，然后利用VM处理请求的过程。

```go
// 根据请求对VM进行某种操作
func (vmc *VMController) Process(vmtype string, req VMCReq) error {
	// 创建vm
	v := vmc.newVM(vmtype)
	ccid := req.GetCCID()
	id := ccid.GetName()

	vmc.lockContainer(id)
	defer vmc.unlockContainer(id)
	
	// 把vm传递给请求，即用该vm执行请求内容
	return req.Do(v)
}
```

#### 虚拟机创建



```go
// 利用指定类型的vm provider创建vm
func (vmc *VMController) newVM(typ string) VM {
	v, ok := vmc.vmProviders[typ]
	if !ok {
		vmLogger.Panicf("Programming error: unsupported VM type: %s", typ)
	}
	return v.NewVM()
}

// NewVMController creates a new instance of VMController
func NewVMController(vmProviders map[string]VMProvider) *VMController {
	return &VMController{
		containerLocks: make(map[string]*refCountedLock),
		vmProviders:    vmProviders,
	}
}
```

创建VM需要使用`NewVMController`，回过去找它的创建地方。

在注册SCC的过程中，调用`registerChaincodeSupport`创建了`chaincodeSupport`，其中一个字段为创建`NewVMController`，就包含了2类Vm provider：
1. ipRegistry，SCC的
1. dockerProvider，普通链码的

```go
func registerChaincodeSupport(
	grpcServer *comm.GRPCServer,
	ccEndpoint string,
	ca tlsgen.CA,
	packageProvider *persistence.PackageProvider,
	aclProvider aclmgmt.ACLProvider,
	pr *platforms.Registry,
	lifecycleSCC *lifecycle.SCC,
	ops *operations.System,
) (*chaincode.ChaincodeSupport, ccprovider.ChaincodeProvider, *scc.Provider) {
    ...
    // SCC的VM provider
	ipRegistry := inproccontroller.NewRegistry()
    ...
    // 普通链码，docker容器类型的VM provider
	dockerProvider := dockercontroller.NewProvider(
		viper.GetString("peer.id"),
		viper.GetString("peer.networkId"),
		ops.Provider,
	)
    ...
    chaincodeSupport := chaincode.NewChaincodeSupport(
		chaincode.GlobalConfig(),
		ccEndpoint,
		userRunsCC,
		ca.CertBytes(),
		authenticator,
		packageProvider,
		lsccInst, // chaincodeSupport的声明周期管理使用了lscc，而不是lifecycle
		aclProvider,
        // 创建了VM controller，controller提供了inproc和docker 2中子controller，
		// 即2中链码运行方式
		container.NewVMController(
			map[string]container.VMProvider{
				dockercontroller.ContainerType: dockerProvider,
				inproccontroller.ContainerType: ipRegistry,
			},
		),
		sccp,
		pr,
		peer.DefaultSupport,
		ops.Provider,
	)
  ...
}
```

#### VM处理操作虚拟机的请求

core.container的请求，都实现了`VMCReq`接口，StartContainerReq、StopContainerReq、WaitContainerReq是实现VMCReq的3类请求。

启动实际是启动虚拟机接口，处理请求。

```go
//VMCReq - all requests should implement this interface.
//The context should be passed and tested at each layer till we stop
//note that we'd stop on the first method on the stack that does not
//take context
type VMCReq interface {
	Do(v VM) error
	GetCCID() ccintf.CCID
}


// 启动容器
func (si StartContainerReq) Do(v VM) error {
	return v.Start(si.CCID, si.Args, si.Env, si.FilesToUpload, si.Builder)
}

//VM is an abstract virtual image for supporting arbitrary virual machines
type VM interface {
	Start(ccid ccintf.CCID, args []string, env []string, filesToUpload map[string][]byte, builder Builder) error
	Stop(ccid ccintf.CCID, timeout uint, dontkill bool, dontremove bool) error
	Wait(ccid ccintf.CCID) (int, error)
	HealthCheck(context.Context) error
}
```

DockerVM和InprocVM都实现了VM接口，本文只关注InprocVM类型，即SCC的。

InprocVM会得到一个容器实例ipc，用它来运行SCC。

```go
//Start starts a previously registered system codechain
func (vm *InprocVM) Start(ccid ccintf.CCID, args []string, env []string, filesToUpload map[string][]byte, builder container.Builder) error {
	path := ccid.GetName()

	ipctemplate := vm.registry.getType(path)
	if ipctemplate == nil {
		return fmt.Errorf(fmt.Sprintf("%s not registered", path))
	}

	// 即ccid.Name
	instName := vm.GetVMName(ccid)

	// 获取容器实例
	ipc, err := vm.getInstance(ipctemplate, instName, args, env)
	if err != nil {
		return fmt.Errorf(fmt.Sprintf("could not create instance for %s", instName))
	}

	// 已经在运行了，还部署个啥！
	if ipc.running {
		return fmt.Errorf(fmt.Sprintf("chaincode running %s", path))
	}

	ipc.running = true

	go func() {
		defer func() {
			if r := recover(); r != nil {
				inprocLogger.Criticalf("caught panic from chaincode  %s", instName)
			}
		}()
		// 启动进程级容器
		ipc.launchInProc(instName, args, env)
	}()

	return nil
}
```

`inprocContainer`开启2个goroutine：
1. 第一个调用`shimStartInProc`，即利用core.chaincode.shim启动InProc类型的容器。
1. 第二个调用`HandleChaincodeStream`，处理peer和Inproc容器间的通信数据，此处的stream是peer端的。

这里可以看到创建了2个通道`peerRcvCCSend`和`ccRcvPeerSend`，它们表明了peer和scc的链码容器是通过通道直接通信的。peer和docker链码容器之间是走gRPC通信的，这个到普通链码的时候再介绍。

```go
// 从进程启动链码
func (ipc *inprocContainer) launchInProc(id string, args []string, env []string) error {
	if ipc.ChaincodeSupport == nil {
		inprocLogger.Panicf("Chaincode support is nil, most likely you forgot to set it immediately after calling inproccontroller.NewRegsitry()")
	}

	// 和调用链码的上层通信的2个通道
	peerRcvCCSend := make(chan *pb.ChaincodeMessage)
	ccRcvPeerSend := make(chan *pb.ChaincodeMessage)
	var err error
	ccchan := make(chan struct{}, 1)
	ccsupportchan := make(chan struct{}, 1)
	shimStartInProc := _shimStartInProc // shadow to avoid race in test
	go func() {
		defer close(ccchan)
		// 启动链码
		inprocLogger.Debugf("chaincode started for %s", id)
		if args == nil {
			args = ipc.args
		}
		if env == nil {
			env = ipc.env
		}
		// 利用shim启动
		err := shimStartInProc(env, args, ipc.chaincode, ccRcvPeerSend, peerRcvCCSend)
		if err != nil {
			err = fmt.Errorf("chaincode-support ended with err: %s", err)
			_inprocLoggerErrorf("%s", err)
		}
		inprocLogger.Debugf("chaincode ended for %s with err: %s", id, err)
	}()

	// shadow function to avoid data race
	inprocLoggerErrorf := _inprocLoggerErrorf
	go func() {
		defer close(ccsupportchan)
		// 处理scc和外部通信的消息流
		inprocStream := newInProcStream(peerRcvCCSend, ccRcvPeerSend)
		inprocLogger.Debugf("chaincode-support started for  %s", id)
		err := ipc.ChaincodeSupport.HandleChaincodeStream(inprocStream)
		if err != nil {
			err = fmt.Errorf("chaincode ended with err: %s", err)
			inprocLoggerErrorf("%s", err)
		}
		inprocLogger.Debugf("chaincode-support ended for %s with err: %s", id, err)
	}()
}
```

#### 利用shim启动Inproc链码容器中的程序

shim是chaincode提供给容器，运行链码的工具，它运行在容器里。

利用shim启动InprocVM使用的函数是`StartInProc`，提取一些**运行链码**需要的数据，比如又一个stream，此处的stream是容器端的。

```go
// 启动SCC的入口
// StartInProc is an entry point for system chaincodes bootstrap. It is not an
// API for chaincodes.
func StartInProc(env []string, args []string, cc Chaincode, recv <-chan *pb.ChaincodeMessage, send chan<- *pb.ChaincodeMessage) error {
	// 有点奇怪，这些日志都没有看到，因为已经在shim，不属于peer日志了
	chaincodeLogger.Debugf("in proc %v", args)

	// 从环境变量获取cc name
	var chaincodename string
	for _, v := range env {
		if strings.Index(v, "CORE_CHAINCODE_ID_NAME=") == 0 {
			p := strings.SplitAfter(v, "CORE_CHAINCODE_ID_NAME=")
			chaincodename = p[1]
			break
		}
	}
	if chaincodename == "" {
		return errors.New("error chaincode id not provided")
	}

	// 创建peer和chaincode通信的通道
	stream := newInProcStream(recv, send)
	chaincodeLogger.Debugf("starting chat with peer using name=%s", chaincodename)
	// 与peer进行通信
	err := chatWithPeer(chaincodename, stream, cc)
	return err
}
```

`chatWithPeer`是通用的，普通的链码也调用这个程序。它创建了一个handler，用来处理消息（发送和接收），以及操作（调用）链码。

这个过程，它会向peer发送REGISTER消息，和peer先“握手”，也会从peer读消息，消息的处理函数就是里面的for循环，这样链码容器就运行起来了。

```go
// 通用，SCC和CC都使用这个函数
func chatWithPeer(chaincodename string, stream PeerChaincodeStream, cc Chaincode) error {
	// 把stream和cc交给handler，handler可以发送和接收数据，即读写通道
	// Create the shim handler responsible for all control logic
	handler := newChaincodeHandler(stream, cc)
	defer stream.CloseSend()

	// Send the ChaincodeID during register.
	chaincodeID := &pb.ChaincodeID{Name: chaincodename}
	payload, err := proto.Marshal(chaincodeID)
	if err != nil {
		return errors.Wrap(err, "error marshalling chaincodeID during chaincode registration")
	}

	// 在stream上向peer发送注册消息
	// Register on the stream
	chaincodeLogger.Debugf("Registering.. sending %s", pb.ChaincodeMessage_REGISTER)
	if err = handler.serialSend(&pb.ChaincodeMessage{Type: pb.ChaincodeMessage_REGISTER, Payload: payload}); err != nil {
		return errors.WithMessage(err, "error sending chaincode REGISTER")
	}

	// holds return values from gRPC Recv below
	type recvMsg struct {
		msg *pb.ChaincodeMessage
		err error
	}
	msgAvail := make(chan *recvMsg, 1)
	errc := make(chan error)

	receiveMessage := func() {
		in, err := stream.Recv()
		msgAvail <- &recvMsg{in, err}
	}

	// 异步读取1个消息
	go receiveMessage()

	// 循环处理peer发送的消息
	for {
		select {
		case rmsg := <-msgAvail:
			switch {
			case rmsg.err == io.EOF:
				err = errors.Wrapf(rmsg.err, "received EOF, ending chaincode stream")
				chaincodeLogger.Debugf("%+v", err)
				return err
			case rmsg.err != nil:
				err := errors.Wrap(rmsg.err, "receive failed")
				chaincodeLogger.Errorf("Received error from server, ending chaincode stream: %+v", err)
				return err
			case rmsg.msg == nil:
				err := errors.New("received nil message, ending chaincode stream")
				chaincodeLogger.Debugf("%+v", err)
				return err
			default:
				// 处理消息
				chaincodeLogger.Debugf("[%s]Received message %s from peer", shorttxid(rmsg.msg.Txid), rmsg.msg.Type)
				err := handler.handleMessage(rmsg.msg, errc)
				if err != nil {
					err = errors.WithMessage(err, "error handling message")
					return err
				}

				// 读取下一个消息
				go receiveMessage()
			}

		case sendErr := <-errc:
			if sendErr != nil {
				err := errors.Wrap(sendErr, "error sending")
				return err
			}
		}
	}
}
```

具体的消息处理函数，先跳过，回过头来，关注scc容器和peer的通信。

#### SCC和Peer的通信通道

链码容器和Peer之间使用Stream进行通信，Stream有2种实现：
1. 使用channel封装的Stream
1. gRPC的Stream

![](http://img.lessisbetter.site/2019-09-peer-cc-communication.png)

链码容器和Peer通信的接口是：

```go
// PeerChaincodeStream interface for stream between Peer and chaincode instance.
type PeerChaincodeStream interface {
	Send(*pb.ChaincodeMessage) error
	Recv() (*pb.ChaincodeMessage, error)
	CloseSend() error
}
```

普通链码使用gRPC：

```go
type chaincodeSupportRegisterClient struct {
	grpc.ClientStream
}
```

系统链码直接使用通道通信，发送和接收消息都在下面了：

```go
// peer和chaincode之间通信的通道
// PeerChaincodeStream interface for stream between Peer and chaincode instance.
type inProcStream struct {
	recv <-chan *pb.ChaincodeMessage
	send chan<- *pb.ChaincodeMessage
}

func newInProcStream(recv <-chan *pb.ChaincodeMessage, send chan<- *pb.ChaincodeMessage) *inProcStream {
	return &inProcStream{recv, send}
}

// 发送其实就是向send写数据
func (s *inProcStream) Send(msg *pb.ChaincodeMessage) (err error) {
	err = nil

	//send may happen on a closed channel when the system is
	//shutting down. Just catch the exception and return error
	defer func() {
		if r := recover(); r != nil {
			err = SendPanicFailure(fmt.Sprintf("%s", r))
			return
		}
	}()
	s.send <- msg
	return
}

// 接收是从recv读数据
func (s *inProcStream) Recv() (*pb.ChaincodeMessage, error) {
	msg, ok := <-s.recv
	if !ok {
		return nil, errors.New("channel is closed")
	}
	return msg, nil
}

func (s *inProcStream) CloseSend() error {
    // 实际啥也没做
	return nil
}
```


### Peer和链码容器的交互，完成链码容器启动

部署链码需要Peer和链码容器交互，不然Peer怎么知道链码容器已经启动。以下是一份peer的DEBUG日志，在下面标注了启动容器和链码Init过程中的消息：

```log
2019-09-09 07:52:09.915 UTC [chaincode] LaunchConfig -> DEBU 098 launchConfig: executable:"chaincode",Args:[chaincode,-peer.address=peer0.org1.example.com:7052],Envs:[CORE_CHAINCODE_LOGGING_LEVEL=info,CORE_CHAINCODE_LOGGING_SHIM=warning,CORE_CHAINCODE_LOGGING_FORMAT=%{color}%{time:2006-01-02 15:04:05.000 MST} [%{module}] %{shortfunc} -> %{level:.4s} %{id:03x}%{color:reset} %{message},CORE_CHAINCODE_ID_NAME=lscc:1.4.3,CORE_PEER_TLS_ENABLED=true,CORE_TLS_CLIENT_KEY_PATH=/etc/hyperledger/fabric/client.key,CORE_TLS_CLIENT_CERT_PATH=/etc/hyperledger/fabric/client.crt,CORE_PEER_TLS_ROOTCERT_FILE=/etc/hyperledger/fabric/peer.crt],Files:[/etc/hyperledger/fabric/client.crt /etc/hyperledger/fabric/client.key /etc/hyperledger/fabric/peer.crt]
2019-09-09 07:52:09.915 UTC [chaincode] Start -> DEBU 099 start container: lscc:1.4.3
2019-09-09 07:52:09.915 UTC [chaincode] Start -> DEBU 09a start container with args: chaincode -peer.address=peer0.org1.example.com:7052
2019-09-09 07:52:09.915 UTC [chaincode] Start -> DEBU 09b start container with env:
	CORE_CHAINCODE_LOGGING_LEVEL=info
	CORE_CHAINCODE_LOGGING_SHIM=warning
	CORE_CHAINCODE_LOGGING_FORMAT=%{color}%{time:2006-01-02 15:04:05.000 MST} [%{module}] %{shortfunc} -> %{level:.4s} %{id:03x}%{color:reset} %{message}
	CORE_CHAINCODE_ID_NAME=lscc:1.4.3
	CORE_PEER_TLS_ENABLED=true
	CORE_TLS_CLIENT_KEY_PATH=/etc/hyperledger/fabric/client.key
	CORE_TLS_CLIENT_CERT_PATH=/etc/hyperledger/fabric/client.crt
	CORE_PEER_TLS_ROOTCERT_FILE=/etc/hyperledger/fabric/peer.crt
2019-09-09 07:52:09.915 UTC [container] lockContainer -> DEBU 09c waiting for container(lscc-1.4.3) lock
2019-09-09 07:52:09.915 UTC [container] lockContainer -> DEBU 09d got container (lscc-1.4.3) lock
2019-09-09 07:52:09.915 UTC [inproccontroller] getInstance -> DEBU 09e chaincode instance created for lscc-1.4.3
2019-09-09 07:52:09.915 UTC [container] unlockContainer -> DEBU 09f container lock deleted(lscc-1.4.3)
2019-09-09 07:52:09.915 UTC [container] lockContainer -> DEBU 0a0 waiting for container(lscc-1.4.3) lock
2019-09-09 07:52:09.915 UTC [container] lockContainer -> DEBU 0a1 got container (lscc-1.4.3) lock
2019-09-09 07:52:09.915 UTC [container] unlockContainer -> DEBU 0a2 container lock deleted(lscc-1.4.3)
2019-09-09 07:52:09.915 UTC [inproccontroller] func2 -> DEBU 0a3 chaincode-support started for  lscc-1.4.3
2019-09-09 07:52:09.915 UTC [inproccontroller] func1 -> DEBU 0a4 chaincode started for lscc-1.4.3
// 以上日志对应的代码流程在上文都讲到了

// 以下是交互过程peer日志
// peer收到容器的注册消息
2019-09-09 07:52:09.916 UTC [chaincode] handleMessage -> DEBU 0a5 [] Fabric side handling ChaincodeMessage of type: REGISTER in state created
2019-09-09 07:52:09.916 UTC [chaincode] HandleRegister -> DEBU 0a6 Received REGISTER in state created
2019-09-09 07:52:09.916 UTC [chaincode] Register -> DEBU 0a7 registered handler complete for chaincode lscc:1.4.3
2019-09-09 07:52:09.916 UTC [chaincode] HandleRegister -> DEBU 0a8 Got REGISTER for chaincodeID = name:"lscc:1.4.3" , sending back REGISTERED
2019-09-09 07:52:09.920 UTC [grpc] HandleSubConnStateChange -> DEBU 0a9 pickfirstBalancer: HandleSubConnStateChange: 0xc0026318c0, READY
2019-09-09 07:52:09.923 UTC [chaincode] HandleRegister -> DEBU 0aa Changed state to established for name:"lscc:1.4.3"

// peer发送ready消息
2019-09-09 07:52:09.923 UTC [chaincode] sendReady -> DEBU 0ab sending READY for chaincode name:"lscc:1.4.3"
2019-09-09 07:52:09.923 UTC [chaincode] sendReady -> DEBU 0ac Changed to state ready for chaincode name:"lscc:1.4.3"

// 已经完成启动容器
2019-09-09 07:52:09.923 UTC [chaincode] Launch -> DEBU 0ad launch complete
2019-09-09 07:52:09.924 UTC [chaincode] Execute -> DEBU 0ae Entry
// 收到容器COMPLETED消息
2019-09-09 07:52:09.925 UTC [chaincode] handleMessage -> DEBU 0af [01b03aae] Fabric side handling ChaincodeMessage of type: COMPLETED in state ready

// 通知scc，部署已经完成
2019-09-09 07:52:09.925 UTC [chaincode] Notify -> DEBU 0b0 [01b03aae] notifying Txid:01b03aae-17a6-4b63-874e-dc20d6f5df0c, channelID:
2019-09-09 07:52:09.925 UTC [chaincode] Execute -> DEBU 0b1 Exit
2019-09-09 07:52:09.925 UTC [sccapi] deploySysCC -> INFO 0b2 system chaincode lscc/(github.com/hyperledger/fabric/core/scc/lscc) deployed
```

可以到REGISTER、READY、COMPLETED等消息，以及状态的改变：created、ready。

但前面还没有介绍Peer和链码容器之间的通信，所以不展示代码了，展示一下Peer和链码容器的消息交互图：

![](http://img.lessisbetter.site/2019-09-deploycc-msg.png)

