---
title: 以太坊源码分析：事件框架
date: 2018-10-18 20:16:01
tags: ['以太坊', '区块链']
---




过去在学Actor模型的时候，就认为异步消息是相当的重要，在华为的时候，也深扒了一下当时产品用的消息模型，简单实用，支撑起了很多模块和业务，但也有一个缺点是和其他的框架有耦合，最近看到以太坊的事件框架，同样简单简洁，理念很适合初步接触事件框架的同学，写文介绍一下。

以太坊的事件框架是一个单独的基础模块，存在于目录`go-ethereum/event`中，它有2中独立的事件框架实现，老点的叫`TypeMux`，已经基本弃用，新的叫`Feed`，当前正在广泛使用。

`TypeMux`和`Feed`还只是简单的事件框架，与Kafka、RocketMQ等消息系统相比，是非常的传统和简单，但是`TypeMux`和`Feed`的简单简洁，已经很好的支撑以太坊的上层模块，这是当下最好的选择。

`TypeMux`和`Feed`各有优劣，最优秀的共同特点是，他们只依赖于Golang原始的包，完全与以太坊的其他模块隔离开来，也就是说，你完全可以把这两个事件框架用在自己的项目中。

`TypeMux`的特点是，你把所有的订阅塞给它就好，事件来了它自会通知你，但有可能会阻塞，通知你不是那么及时，甚至过了一段挺长的时间。

`Feed`的特点是，它通常不存在阻塞的情况，会及时的把事件通知给你，但需要你为**每类事件**都建立一个Feed，然后不同的事件去不同的Feed上订阅和发送，这其实挺烦人的，如果你用错了Feed，会导致panic。

接下来，介绍下这种简单事件框架的抽象模型，然后再回归到以太坊，介绍下`TypeMux`和`Feed`。



<!--more-->



## 事件框架的抽象结构

![原始事件框架抽象结构](http://img.lessisbetter.site/2018-12-event-framework.png)


如上图，轻量级的事件框架会把所有的被订阅的事件收集起来，然后把每个订阅者组合成一个列表，当事件框架收到某个事件的时候，就把订阅该事件的所有订阅者找出来，然后把这个事件发给他们。

它需要具有2个功能：

1. 让订阅者订阅、取消订阅某类事件。
2. 让发布者能够发布某个事件，并且把事件送到每个订阅者。

如果做成完善的消息系统，就还得考虑这些特性：可用性、吞吐量、传输延迟、有序消息、消息存储、过滤、重发，这和事件框架相比就复杂上去了，我们专注的介绍下以太坊的事件模型怎么完成上述3个功能的。

## 以太坊的事件模型

`TypeMux`是一个以太坊不太满意的事件框架，所以以太坊就搞了`Feed`出来，它解决了`TypeMux`效率低下，延迟交付的问题。接下来就先看下这个`TypeMux`。



### TypeMux：同步事件框架

**TypeMux是一个同步事件框架。**它的实现和上面讲的事件框架的抽象结构是完全一样的，它维护了一个订阅表，表里维护了每个事件的订阅者列表。它的特点：

1. 采用**多对多**结构：多个事件对多个订阅者。
2. 采用推模式，把事件/消息推送给订阅者，就像信件一样，会被送到你的信箱，你在信箱里取信就行了。
3. 是一个同步事件框架。这也是它的缺点所在，举个例子就是：邮递员要给小红、小明送信，只有信箱里的信被小红取走后，邮递员才去给小明送信，如果小红旅游去了无法取信，邮递员就一直等在小红家，而小明一直收不到信，小明很无辜无辜啊！

看下它2个功能的实现：

1. 订阅和取消订阅。订阅通过函数`TypeMux.Subscribe()`，入参为要订阅的事件类型，会返回`TypeMuxSubscription`给订阅者，订阅者可通过此控制订阅，通过`TypeMuxSubscription.Unsubscribe()` 可以取消订阅。
2. 发布事件和传递事件。`TypeMux.Post()`，入参为事件类型，根据订阅表找出该事件的订阅者列表，遍历列表，依次向每个订阅者传递事件，如果前一个没有传递完成进入阻塞，会导致后边的订阅者不能及时收到事件。


![TypeMux抽象结构](http://img.lessisbetter.site/2018-12-typemux.png
)


### TypeMux源码速递

`TypeMux`的精简组成：

```go
// A TypeMux dispatches events to registered receivers. Receivers can be
// registered to handle events of certain type. Any operation
// called after mux is stopped will return ErrMuxClosed.
//
// The zero value is ready to use.
//
// Deprecated: use Feed
// 本质：哈希列表，每个事件的订阅者都存到对于的列表里
type TypeMux struct {
	mutex   sync.RWMutex // 锁
	subm    map[reflect.Type][]*TypeMuxSubscription // 订阅表：所有事件类型的所有订阅者
	stopped bool
}
```



订阅：

```go
// Subscribe creates a subscription for events of the given types. The
// subscription's channel is closed when it is unsubscribed
// or the mux is closed.
// 订阅者只传入订阅的事件类型，然后TypeMux会返回给它一个订阅对象
func (mux *TypeMux) Subscribe(types ...interface{}) *TypeMuxSubscription {
	sub := newsub(mux)
	mux.mutex.Lock()
	defer mux.mutex.Unlock()
	if mux.stopped {
		// set the status to closed so that calling Unsubscribe after this
		// call will short circuit.
		sub.closed = true
		close(sub.postC)
	} else {
		if mux.subm == nil {
			mux.subm = make(map[reflect.Type][]*TypeMuxSubscription)
		}
		for _, t := range types {
			rtyp := reflect.TypeOf(t)
			// 在同一次订阅中，不要重复订阅同一个类型的事件
			oldsubs := mux.subm[rtyp]
			if find(oldsubs, sub) != -1 {
				panic(fmt.Sprintf("event: duplicate type %s in Subscribe", rtyp))
			}
			subs := make([]*TypeMuxSubscription, len(oldsubs)+1)
			copy(subs, oldsubs)
			subs[len(oldsubs)] = sub
			mux.subm[rtyp] = subs
		}
	}
	return sub
}
```



取消订阅:

```
func (s *TypeMuxSubscription) Unsubscribe() {
	s.mux.del(s)
	s.closewait()
}
```



发布事件和传递事件：

```go
// Post sends an event to all receivers registered for the given type.
// It returns ErrMuxClosed if the mux has been stopped.
// 遍历map，找到所有订阅的人，向它们传递event，同一个event对象，非拷贝，运行在调用者goroutine
func (mux *TypeMux) Post(ev interface{}) error {
	event := &TypeMuxEvent{
		Time: time.Now(),
		Data: ev,
	}
	rtyp := reflect.TypeOf(ev)
	mux.mutex.RLock()
	if mux.stopped {
		mux.mutex.RUnlock()
		return ErrMuxClosed
	}
	subs := mux.subm[rtyp]
	mux.mutex.RUnlock()
	for _, sub := range subs {
		sub.deliver(event)
	}
	return nil
}

func (s *TypeMuxSubscription) deliver(event *TypeMuxEvent) {
	// Short circuit delivery if stale event
	// 不发送过早（老）的消息
	if s.created.After(event.Time) {
		return
	}
	// Otherwise deliver the event
	s.postMu.RLock()
	defer s.postMu.RUnlock()

	select {
	case s.postC <- event:
	case <-s.closing:
	}
}
```



我上面指出了发送事件可能阻塞，阻塞在哪？关键就在下面这里：创建`TypeMuxSubscription`时，通道使用的是无缓存通道，读写是同步的，这里注定了**TypeMux是一个同步事件框架，这是以太坊改用Feed的最大原因**。

```go
func newsub(mux *TypeMux) *TypeMuxSubscription {
	c := make(chan *TypeMuxEvent) // 无缓冲通道，同步读写
	return &TypeMuxSubscription{
		mux:     mux,
		created: time.Now(),
		readC:   c,
		postC:   c,
		closing: make(chan struct{}),
	}
}
```



### Feed：流式框架

**Feed是一个流式事件框架。**上文强调了TypeMux是一个同步框架，也正是因为此以太坊丢弃了它，难道`Feed`就是一个异步框架？**不一定是的，这取决于订阅者是否采用有缓存的通道，采用有缓存的通道，则Feed就是异步的，采用无缓存的通道，Feed就是同步的，把同步还是异步的选择交给使用者**。

本节强调Feed的流式特点。事件本质是一个数据，连续不断的事件就组成了一个数据流，这些数据流不停的流向它的订阅者那里，并且不会阻塞在任何一个订阅者那里。

举几个不是十分恰当的例子。

1. 公司要放中秋节，HR给所有同事都发了一封邮件，有些同事读了，有些同事没读，要到国庆节了HR又给所有同事发了一封邮件，这些邮件又进入到每个人的邮箱，不会因为任何一个人没有读邮件，导致剩下的同事收不到邮件。
2. 你在朋友圈给朋友旅行的照片点了个赞，每当你们共同朋友点赞或者评论的时候，你都会收到提醒，无论你看没看这些提醒，这些提醒都会不断的发过来。
3. 你微博关注了谢娜，谢娜发了个搞笑的视频，你刷微博的时候就收到了，但也有很多人根本没刷微博，你不会因为别人没有刷，你就收不到谢娜的动态。

Feed和TypeMux相同的是，它们都是推模式，不同的是Feed是异步的，如果有些订阅者阻塞了，没关系，它会继续向后面的订阅者发送事件/消息。

Feed是一个一对多的事件流框架。**每个类型的事件都需要一个与之对应的Feed**，订阅者通过这个Feed进行订阅事件，发布者通过这个Feed发布事件。

![Feed抽象结构](http://img.lessisbetter.site/2018-12-event-feed.png
)

看下Feed是如何实现2个功能的：

1. 订阅和取消订阅：`Feed.Subscribe()`，入参是一个通道，通常是有缓冲的，就算是无缓存也不会造成Feed阻塞，Feed会校验这个通道的类型和本Feed管理的事件类型是否一致，然后把通道保存下来，返回给订阅者一个`Subscription`，可以通过它取消订阅和读取通道错误。
2. 发布事件和传递事件。`Feed.Send()`入参是一个事件，加锁确保本类型事件只有一个发送协程正在进行，然后校验事件类型是否匹配，Feed会尝试给每个订阅者发送事件，如果订阅者阻塞，Feed就继续尝试给下一个订阅者发送，直到给每个订阅者发送事件，返回发送该事件的数量。


### Feed源码速递

Feed定义：

```go
// Feed implements one-to-many subscriptions where the carrier of events is a channel.
// Values sent to a Feed are delivered to all subscribed channels simultaneously.
//
// Feeds can only be used with a single type. The type is determined by the first Send or
// Subscribe operation. Subsequent calls to these methods panic if the type does not
// match.
//
// The zero value is ready to use.
// 一对多的事件订阅管理：每个feed对象，当别人调用send的时候，会发送给所有订阅者
// 每种事件类型都有一个自己的feed，一个feed内订阅的是同一种类型的事件，得用某个事件的feed才能订阅该事件
type Feed struct {
	once      sync.Once        // ensures that init only runs once
	sendLock  chan struct{}    // sendLock has a one-element buffer and is empty when held.It protects sendCases. 这个锁确保了只有一个协程在使用go routine
	removeSub chan interface{} // interrupts Send
	sendCases caseList         // the active set of select cases used by Send，订阅的channel列表，这些channel是活跃的

	// The inbox holds newly subscribed channels until they are added to sendCases.
	mu     sync.Mutex
	inbox  caseList // 不活跃的在这里
	etype  reflect.Type
	closed bool
}
```



订阅事件：

```go
// Subscribe adds a channel to the feed. Future sends will be delivered on the channel
// until the subscription is canceled. All channels added must have the same element type.
//
// The channel should have ample buffer space to avoid blocking other subscribers.
// Slow subscribers are not dropped.
// 订阅者传入接收事件的通道，feed将通道保存为case，然后返回给订阅者订阅对象
func (f *Feed) Subscribe(channel interface{}) Subscription {
	f.once.Do(f.init)

	// 通道和通道类型检查
	chanval := reflect.ValueOf(channel)
	chantyp := chanval.Type()
	if chantyp.Kind() != reflect.Chan || chantyp.ChanDir()&reflect.SendDir == 0 {
		panic(errBadChannel)
	}
	sub := &feedSub{feed: f, channel: chanval, err: make(chan error, 1)}

	f.mu.Lock()
	defer f.mu.Unlock()
	if !f.typecheck(chantyp.Elem()) {
		panic(feedTypeError{op: "Subscribe", got: chantyp, want: reflect.ChanOf(reflect.SendDir, f.etype)})
	}
	
	// 把通道保存到case
	// Add the select case to the inbox.
	// The next Send will add it to f.sendCases.
	cas := reflect.SelectCase{Dir: reflect.SelectSend, Chan: chanval}
	f.inbox = append(f.inbox, cas)
	return sub
}
```



发送和传递事件：这个发送是比较绕一点的，要想真正掌握其中的运行，最好写个小程序练习下。

```go
// Send delivers to all subscribed channels simultaneously.
// It returns the number of subscribers that the value was sent to.
// 同时向所有的订阅者发送事件，返回订阅者的数量
func (f *Feed) Send(value interface{}) (nsent int) {
	rvalue := reflect.ValueOf(value)

	f.once.Do(f.init)
	<-f.sendLock // 获取发送锁

	// Add new cases from the inbox after taking the send lock.
	// 从inbox加入到sendCases，不能订阅的时候直接加入到sendCases，因为可能其他协程在调用发送
	f.mu.Lock()
	f.sendCases = append(f.sendCases, f.inbox...)
	f.inbox = nil

	// 类型检查：如果该feed不是要发送的值的类型，释放锁，并且执行panic
	if !f.typecheck(rvalue.Type()) {
		f.sendLock <- struct{}{}
		panic(feedTypeError{op: "Send", got: rvalue.Type(), want: f.etype})
	}
	f.mu.Unlock()

	// Set the sent value on all channels.
	// 把发送的值关联到每个case/channel，每一个事件都有一个feed，所以这里全是同一个事件的
	for i := firstSubSendCase; i < len(f.sendCases); i++ {
		f.sendCases[i].Send = rvalue
	}

	// Send until all channels except removeSub have been chosen. 'cases' tracks a prefix
	// of sendCases. When a send succeeds, the corresponding case moves to the end of
	// 'cases' and it shrinks by one element.
	// 所有case仍然保留在sendCases，只是用过的会移动到最后面
	cases := f.sendCases
	for {
		// Fast path: try sending without blocking before adding to the select set.
		// This should usually succeed if subscribers are fast enough and have free
		// buffer space.
		// 使用非阻塞式发送，如果不能发送就及时返回
		for i := firstSubSendCase; i < len(cases); i++ {
			// 如果发送成功，把这个case移动到末尾，所以i这个位置就是没处理过的，然后大小减1
			if cases[i].Chan.TrySend(rvalue) {
				nsent++
				cases = cases.deactivate(i)
				i--
			}
		}

		// 如果这个地方成立，代表所有订阅者都不阻塞，都发送完了
		if len(cases) == firstSubSendCase {
			break
		}

		// Select on all the receivers, waiting for them to unblock.
		// 返回一个可用的，直到不阻塞。
		chosen, recv, _ := reflect.Select(cases)
		if chosen == 0 /* <-f.removeSub */ {
			// 这个接收方要删除了，删除并缩小sendCases
			index := f.sendCases.find(recv.Interface())
			f.sendCases = f.sendCases.delete(index)
			if index >= 0 && index < len(cases) {
				// Shrink 'cases' too because the removed case was still active.
				cases = f.sendCases[:len(cases)-1]
			}
		} else {
			// reflect已经确保数据已经发送，无需再尝试发送
			cases = cases.deactivate(chosen)
			nsent++
		}
	}

	// 把sendCases中的send都标记为空
	// Forget about the sent value and hand off the send lock.
	for i := firstSubSendCase; i < len(f.sendCases); i++ {
		f.sendCases[i].Send = reflect.Value{}
	}
	f.sendLock <- struct{}{}
	return nsent
}
```

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/10/18/ethereum-code-event-framework/](http://lessisbetter.site/2018/10/18/ethereum-code-event-framework/)