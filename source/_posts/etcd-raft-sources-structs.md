---
title: Etcd Raft架构设计和源码剖析3：重要结构体定义
date: 2019-09-05 21:59:35
tags: ['一致性', '共识', 'Raft']
---


## 序言

etcd raft定义了一些重要的结构体，来传递和表示raft使用到的数据。



在介绍各结构体之前，先澄清一下raft、log和state machine的关系，它们三个是独立的，没有隶属关系，尤其是state machine并不属于raft。

![State machine](https://lessisbetter.site/images/2019-08-raft-%E5%9B%BE1.png)

Consensus Module指raft算法，它输出一致的Log Entry序列，State machine指应用Entry后得到的状态，状态机是并不是raft的一部分，而是用来存储数据的模块。

## Entry

每个Raft集群节点都是一个状态机，每个节点都使用相同的log entry序列修改状态机的数据，Entry就是每一个操作项，**raft的核心能力就是为应用层提供序列相同的entry**。

```go
type Entry struct {
	Term             uint64    `protobuf:"varint,2,opt,name=Term" json:"Term"`
	Index            uint64    `protobuf:"varint,3,opt,name=Index" json:"Index"`
	Type             EntryType `protobuf:"varint,1,opt,name=Type,enum=raftpb.EntryType" json:"Type"`
	Data             []byte    `protobuf:"bytes,4,opt,name=Data" json:"Data,omitempty"`
}

type EntryType int32

const (
	EntryNormal       EntryType = 0
	EntryConfChange   EntryType = 1
	EntryConfChangeV2 EntryType = 2
)
```

每一个Entry，都可以使用(Term, Index)进行唯一标记，相当于Entry的ID：

- Term：即raft论文中的Term，表明了当前Entry所属的Term。raft不使用绝对时间，而是使用相对时间，它把时间分割成了大小不等的term，每一轮选举都会开启一个新的term，term值会连续累加。如果当前的节点已经是Term 10缺收到了Term 8的Entry，Term 8的Entry已经过时，会被丢弃。
- Index：每一个Entry都有一个的Index，代表当前Entry在log entry序列中的位置，每个index上最终只有1个达成共识的Entry。

除了用于达成一致的Term和Index外，Entry还携带了数据：

- Type：表明当前Entry的类型，`EntryNormal`代表是Entry携带的是修改状态机的操作数据，`EntryConfChange`和`EntryConfChangeV2`代表的是Entry携带的是修改当前raft集群的配置。
- Data：是序列化的数据，不同的Type类型，对应不同的Data。

## Snapshot

在Entry特别多的场景下，会存在一些问题，比如现在有1亿条已经达成一致Entry，后面还有源源不断的Entry产生，是否有以下问题：

1. 这些Entry占用了大量的磁盘空间，但实际上过去的Entry已经对已经拥有这些Entry的节点没有意义了，只对那些没有Entry的节点有意义，leader把Entry发送给没有这些Entry节点，以让这些节点最终能和leader保持一致的状态。
2. 有些follower非常慢，或者刚启动，或者重启过，与leader的当前状态已经严重脱节，让他们从Entry 0开始同步，然后应用到状态机，这种操作时间效率是不是非常慢？然后每一个Entry都会产生一个历史的状态，当产生新的状态之后，历史状态对当前节点也没有意义。

解决这种问题的办法就是快照，比如虚拟机的快照，或者docker镜像（镜像本质也是一种快照），有了快照就可以把状态机快速恢复到快照时的状态，**空间和时间上效率都能提高很多**。

Raft可以定期产生一些快照，然后在这些快照上按序应用快照之后的Entry就能得到一致的状态。1亿个Entry + 1亿01个Entry得到的状态，跟第1亿个Entry后所产生的快照+1亿零1个Entry得到的状态是一致的。

```go
type Snapshot struct {
	Data             []byte           `protobuf:"bytes,1,opt,name=data" json:"data,omitempty"`
	Metadata         SnapshotMetadata `protobuf:"bytes,2,opt,name=metadata" json:"metadata"`
}

type SnapshotMetadata struct {
	ConfState        ConfState `protobuf:"bytes,1,opt,name=conf_state,json=confState" json:"conf_state"`
	Index            uint64    `protobuf:"varint,2,opt,name=index" json:"index"`
	Term             uint64    `protobuf:"varint,3,opt,name=term" json:"term"`
}
```

- Data：是状态机中状态的快照。
- Metadata：是快照自身相关的数据。
  - ConfState：是快照时，当前raft的配置状态，这些状态数据并不在状态机中，所以需要进行保存。
  - Index、Term：快照所依据的Entry所在的Index和Term。

## Message

Raft集群节点之间的通信只使用了1个结构体`Message`，Message中有一个`Type`成员，表明了当前的Message是哪种消息，比如可以是Raft论文中提到的AppendEntries，RequestVotes等，目前实际可以容纳19种类型的消息，每种消息对Raft都有不同的作用，具体见[这篇文章](https://zhuanlan.zhihu.com/p/51065416)：

```go
// 不同的Message类型会用到不同的字段
type Message struct {
	Type             MessageType `protobuf:"varint,1,opt,name=type,enum=raftpb.MessageType" json:"type"`
	To               uint64      `protobuf:"varint,2,opt,name=to" json:"to"`
	From             uint64      `protobuf:"varint,3,opt,name=from" json:"from"`
	Term             uint64      `protobuf:"varint,4,opt,name=term" json:"term"`
	LogTerm          uint64      `protobuf:"varint,5,opt,name=logTerm" json:"logTerm"`
	Index            uint64      `protobuf:"varint,6,opt,name=index" json:"index"`
	Entries          []Entry     `protobuf:"bytes,7,rep,name=entries" json:"entries"`
	Commit           uint64      `protobuf:"varint,8,opt,name=commit" json:"commit"`
	Snapshot         Snapshot    `protobuf:"bytes,9,opt,name=snapshot" json:"snapshot"`
	Reject           bool        `protobuf:"varint,10,opt,name=reject" json:"reject"`
	RejectHint       uint64      `protobuf:"varint,11,opt,name=rejectHint" json:"rejectHint"`
	Context          []byte      `protobuf:"bytes,12,opt,name=context" json:"context,omitempty"`
}
```

Message中包含了很多字段，不同的消息类型使用的字段组合不相同，可以从不同消息的处理逻辑中看出来。

- To, From：是消息的接收节点和发送节点的的Raft ID。
- Term：创建Message时，发送节点所在的Term。
- LogTerm：创建Message时，发送节点本地所保存的log entry序列中最大的Term，在选举的时候会使用。
- Index：不同的消息类型，Index的含义不同。Term和Index与Entry中的Term和Index不一定会相同，因为某个follower可能比较慢，leader向follower发送已经committed的Entry。
- Entries：发送给follower，待follower处理的Entry。
- Commit：创建Message时，不同消息含义不同，Append时是发送节点本地已committed的Index，Heartbeat时是committed Index或者与follower匹配的Index。
- Snapshot：leader传递给follower的snapshot。
- Reject：投票和Append的响应消息使用，Reject表示拒绝leader发来的消息。
- RejectHint：拒绝Append消息的响应消息使用，用来给leader提示，发送follower已有的最后一个Index。
- Context：某些消息的附加信息，即用来存储通用的数据。比如竞选时，存放`campaignTransfer`。



## Storage

etcd/raft不负责**持久化数据存储**和网络通信，网络数据都是通过Node接口的函数传入和传出raft。持久化数据存储由创建raft.Node的应用层负责，包含：

- 应用层使用Entry生成的状态机，即一致的应用数据。
- WAL：Write Ahead Log，历史的Entry（包含还未达成一致的Entry）和快照数据。

Snapshot是已在节点间达成一致Entry的快照，快照之前的Entry必然都是已经达成一致的，而快照之后，有达成一致的，也有写入磁盘还未达成一致的Entry。etcd/raft会使用到这些Entry和快照，而`Storage`接口，就是用来读这些数据的。


```go
// Storage is an interface that may be implemented by the application
// to retrieve log entries from storage.
//
// If any Storage method returns an error, the raft instance will
// become inoperable and refuse to participate in elections; the
// application is responsible for cleanup and recovery in this case.
type Storage interface {
	// TODO(tbg): split this into two interfaces, LogStorage and StateStorage.

	// InitialState returns the saved HardState and ConfState information.
	InitialState() (pb.HardState, pb.ConfState, error)
	// Entries returns a slice of log entries in the range [lo,hi).
	// MaxSize limits the total size of the log entries returned, but
	// Entries returns at least one entry if any.
	Entries(lo, hi, maxSize uint64) ([]pb.Entry, error)
	// Term returns the term of entry i, which must be in the range
	// [FirstIndex()-1, LastIndex()]. The term of the entry before
	// FirstIndex is retained for matching purposes even though the
	// rest of that entry may not be available.
	Term(i uint64) (uint64, error)
	// LastIndex returns the index of the last entry in the log.
	LastIndex() (uint64, error)
	// FirstIndex returns the index of the first log entry that is
	// possibly available via Entries (older entries have been incorporated
	// into the latest Snapshot; if storage only contains the dummy entry the
	// first log entry is not available).
	FirstIndex() (uint64, error)
	// Snapshot returns the most recent snapshot.
	// If snapshot is temporarily unavailable, it should return ErrSnapshotTemporarilyUnavailable,
	// so raft state machine could know that Storage needs some time to prepare
	// snapshot and call Snapshot later.
	Snapshot() (pb.Snapshot, error)
}
```

使用这个接口，从应用层读取：

- InitialState：HardState和配置状态Confstate
- Entries：根据Index获取连续的Entry
- Term：获取某个Entry所在的Term
- LastIndex：获取本节点已存储的最新的Entry的Index
- FirstIndex：获取本节点已存储的第一个Entry的Index
- Snapshot：获取本节点最近生成的Snapshot，Snapshot是由应用层创建的，并暂时保存起来，raft调用此接口读取

每次都从磁盘文件读取这些数据，效率必然是不高的，所以etcd/raft内定义了`MemoryStorage`，它实现了`Storage`接口，并且提供了函数来维护最新快照后的Entry，关于`MemoryStorage`见[raftLog](#raftLog)小节，其中的`storage`即为`MemoryStorage`。

## unstable

因为Entry的存储是由应用层负责的，所以raft需要暂时存储还未存到Storage中的Entry或者Snapshot，在创建Ready时，Entry和Snapshot会被封装到Ready，由应用层写入到storage。

```go
// unstable.entries[i] has raft log position i+unstable.offset.
// Note that unstable.offset may be less than the highest log
// position in storage; this means that the next write to storage
// might need to truncate the log before persisting unstable.entries.
type unstable struct {
	// the incoming unstable snapshot, if any.
	snapshot *pb.Snapshot
	// all entries that have not yet been written to storage.
	entries []pb.Entry
	offset  uint64
	...
}
```

- Snapshot：是follower从leader收到的最新的Snapshot。
- entries：对leader而已，是raft刚利用请求创建的Entry，对follower而言是从leader收到的Entry。
- offset：Entries[i].Index = i + offset。

## raftLog

raft使用raftLog来管理当前Entry序列和Snapshot等信息，它由Storage、unstable、committed和applied组成。

```go
type raftLog struct {
	// storage contains all stable entries since the last snapshot.
	storage Storage

	// unstable contains all unstable entries and snapshot.
	// they will be saved into storage.
	unstable unstable

	// committed和applied是storage的2个整数下标
	// committed到applied需要Ready
	// committed is the highest log position that is known to be in
	// stable storage on a quorum of nodes.
	committed uint64
	// applied is the highest log position that the application has
	// been instructed to apply to its state machine.
	// Invariant: applied <= committed
	applied uint64
  ...
}
```

Storage和unstable前面已经介绍过了，所以介绍下committed和applied。

committed指最后一个在raft集群多数节点之间达成一致的Entry Index。

applied指当前节点被应用层应用到状态机的最后一个Entry Index。applied和committed之间的Entry就是等待被应用层应用到状态机的Entry。

前面提到Storage接口可以获取第一个索引firstIdx，最后一个索引lastIdx，在生成snapshot之后签名的Entry就可以删除了，所以firstidx是storage中snapshot后的第一个Entry的Index，lastIndex是storage中保存的最后一个Entry的Index，这个Entry可能还没有在raft集群多数节点之间达成一致，所以在committed之后，这些Entry是等待commit的Entry，leader发现某个Entry Index已经在多数节点之间达成一致，就会把committed移动到该Entry Index。

![raftLog](https://lessisbetter.site/images/2019-08-raftLog.png)

## SoftState

SoftState指易变的状态数据，记录了**当前**的Leader的Node ID，以及当前节点的角色。

```go
// SoftState provides state that is useful for logging and debugging.
// The state is volatile and does not need to be persisted to the WAL.
type SoftState struct {
	// leader的Node ID
	Lead uint64 // must use atomic operations to access; keep 64-bit aligned.
	// 节点是什么角色：leader、follower...
	RaftState StateType
}

// StateType represents the role of a node in a cluster.
type StateType uint64

var stmap = [...]string{
	"StateFollower",
	"StateCandidate",
	"StateLeader",
	"StatePreCandidate",
}
```

## HardState

HardState是写入到WAL（存储Entry的文件）的状态，可以在节点重启时恢复raft的状态，它了记录：

- Term：节点当前所在的Term。
- Vote：节点在竞选期间所投的候选节点ID。
- Commit：当前已经committed Entry Index。

```go
type HardState struct {
	Term             uint64 `protobuf:"varint,1,opt,name=term" json:"term"`
	Vote             uint64 `protobuf:"varint,2,opt,name=vote" json:"vote"`
	Commit           uint64 `protobuf:"varint,3,opt,name=commit" json:"commit"`
}
```

## Ready

终于到etcd raft最重要的一个结构体了。raft使用Ready结构体对外传递数据，是多种数据的打包。

```go
// Ready encapsulates the entries and messages that are ready to read,
// be saved to stable storage, committed or sent to other peers.
// All fields in Ready are read-only.
type Ready struct {
	// The current volatile state of a Node.
	// SoftState will be nil if there is no update.
	// It is not required to consume or store SoftState.
	*SoftState

	// The current state of a Node to be saved to stable storage BEFORE
	// Messages are sent.
	// HardState will be equal to empty state if there is no update.
	pb.HardState

	// ReadStates can be used for node to serve linearizable read requests locally
	// when its applied index is greater than the index in ReadState.
	// Note that the readState will be returned when raft receives msgReadIndex.
	// The returned is only valid for the request that requested to read.
	ReadStates []ReadState

	// unstable的entry，即待写入到storage的entry
	// Entries specifies entries to be saved to stable storage BEFORE
	// Messages are sent.
	Entries []pb.Entry

	// Snapshot specifies the snapshot to be saved to stable storage.
	Snapshot pb.Snapshot

	// 待applied的entry
	// CommittedEntries specifies entries to be committed to a
	// store/state-machine. These have previously been committed to stable
	// store.
	CommittedEntries []pb.Entry

	// Messages specifies outbound messages to be sent AFTER Entries are
	// committed to stable storage.
	// If it contains a MsgSnap message, the application MUST report back to raft
	// when the snapshot has been received or has failed by calling ReportSnapshot.
	Messages []pb.Message

	// MustSync indicates whether the HardState and Entries must be synchronously
	// written to disk or if an asynchronous write is permissible.
	MustSync bool
}
```

SoftState、HardState、Entry、Snapshot、Message都已经介绍过，不再单独介绍含义。

Entries和CommittedEntries的区别是，Entries保存的是从unstable读取的Entry，它们即将被应用层写入storage，CommittedEntries是已经被Committed，还没有applied，应用层会把他们应用到状态机。

ReadStates用来处理读请求，MustSync用来指明应用层是否采用异步的方式写数据。

应用层在接收到Ready后，应当处理Ready中的每一个有效字段，处理完毕后，调用`Advance()`通知raft Ready已处理完毕。


