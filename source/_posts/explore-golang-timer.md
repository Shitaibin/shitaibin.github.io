---
title: 探索Golang定时器的陷阱
date: 2018-09-04 17:43:41
tags: ['Go', '定时器']
---



所谓陷阱，就是它不是你认为的那样，这种认知误差可能让你的软件留下隐藏Bug。刚好Timer就有3个陷阱，我们会讲1）Reset的陷阱和2）通道的陷阱，3）Stop的陷阱与Reset的陷阱类似，自己探索吧。


# Reset的陷阱在哪

`Timer.Reset()`函数的返回值是bool类型，我们看一个问题三连：
1. 它的返回值代表什么呢？
2. 我们想要的成功是什么？
3. 失败是什么？

- 成功：一段时间之后定时器超时，收到超时事件。
- 失败：成功的反面，我们收不到那个事件。对于失败，我们应当做些什么，确保我们的定时器发挥作用。

Reset的返回值是不是这个意思？

<!--more-->


通过查看文档和实现，**`Timer.Reset()`的返回值并不符合我们的预期，这就是误差**。它的返回值不代表重设定时器成功或失败，而是在表达定时器在重设前的状态：
- 当Timer已经停止或者超时，返回false。
- 当定时器未超时时，返回true。

所以，当Reset返回false时，我们并不能认为一段时间之后，超时不会到来，实际上可能会到来，定时器已经生效了。

# 跳过陷阱，再遇陷阱

如何跳过前面的陷阱，让Reset符合我们的预期功能呢？直接忽视Reset的返回值好了，它不能帮助你达到预期的效果。

**真正的陷阱是Timer的通道，它和我们预期的成功、失败密切相关。我们所期望的定时器设置失败，通常只和通道有关：设置定时器前，定时器的通道`Timer.C`中是否已经有数据。**
- 如果有，我们设置的定时器失败了，我们可能读到不正确的超时事件。
- 如果没有，我们设置的定时器成功了，我们在设定的时间得到超时事件。

接下来解释为何失败只与通道中是否存在超时事件有关。

定时器的缓存通道大小只为1，无法多存放超时事件，看源码。
```go
// NewTimer creates a new Timer that will send
// the current time on its channel after at least duration d.
func NewTimer(d Duration) *Timer {
	c := make(chan Time, 1) // 缓存通道大小为1
	t := &Timer{
		C: c,
		r: runtimeTimer{
			when: when(d),
			f:    sendTime,
			arg:  c,
		},
	}
	startTimer(&t.r)
	return t
}
```

定时器创建后是单独运行的，超时后会向通道写入数据，你从通道中把数据读走。**当前一次的超时数据没有被读取，而设置了新的定时器，然后去通道读数据，结果读到的是上次超时的超时事件，看似成功，实则失败，完全掉入陷阱。**

# 跨越陷阱，确保成功

**如果确保`Timer.Reset()`成功，得到我们想要的结果？`Timer.Reset()`前清空通道。**

- 当业务场景简单时，没有必要主动清空通道。比如，处理流程是：设置1次定时器，处理一次定时器，中间无中断，下次Reset前，通道必然是空的。
- 当业务场景复杂时，不确定通道是否为空，那就主动清除。
```go
// 方法1
if len(Timer.C) > 0{
    <-Timer.C
}
Timer.Reset(time.Second)
```
经过和[@周志荣_9447](https://www.jianshu.com/u/987596c52194)的讨论和思考，更加合理的做法还是下面这样：
```go
// 方法2
if !Timer.Stop() && len(Timer.C) > 0{
    <-Timer.C
}
Timer.Reset(time.Second)
```
定时器的运行和`len(Timer.C)`的判断是在不同的协程中，当判断的时候通道大小可能为0，但当执行`Reset()`的前的这段时间，旧的定时器超时，通道中存在超时事件，再执行`Reset()`也达不到预期的效果。
**方法2才是合理的方法。**先执行`Stop()`，可以确保旧定时器已经停止，不会再向通道中写入超时事件，就可解决上面的问题。`Stop()`返回false并不是代表，通道中一定存在超时事件，所以还需使用`len(Timer.C)  > 0`进行判断再决定是否清空通道。

# 测试代码

```go
package main

import (
	"fmt"
	"time"
)

// 不同情况下，Timer.Reset()的返回值
func test1() {
	fmt.Println("第1个测试：Reset返回值和什么有关？")
	tm := time.NewTimer(time.Second)
	defer tm.Stop()

	quit := make(chan bool)

	// 退出事件
	go func() {
		time.Sleep(3 * time.Second)
		quit <- true
	}()

	// Timer未超时，看Reset的返回值
	if !tm.Reset(time.Second) {
		fmt.Println("未超时，Reset返回false")
	} else {
		fmt.Println("未超时，Reset返回true")
	}

	// 停止timer
	tm.Stop()
	if !tm.Reset(time.Second) {
		fmt.Println("停止Timer，Reset返回false")
	} else {
		fmt.Println("停止Timer，Reset返回true")
	}

	// Timer超时
	for {
		select {
		case <-quit:
			return

		case <-tm.C:
			if !tm.Reset(time.Second) {
				fmt.Println("超时，Reset返回false")
			} else {
				fmt.Println("超时，Reset返回true")
			}
		}
	}
}

func test2() {
	fmt.Println("\n第2个测试:超时后，不读通道中的事件，可以Reset成功吗？")
	sm2Start := time.Now()
	tm2 := time.NewTimer(time.Second)
	time.Sleep(2 * time.Second)
	fmt.Printf("Reset前通道中事件的数量:%d\n", len(tm2.C))
	if !tm2.Reset(time.Second) {
		fmt.Println("不读通道数据，Reset返回false")
	} else {
		fmt.Println("不读通道数据，Reset返回true")
	}
	fmt.Printf("Reset后通道中事件的数量:%d\n", len(tm2.C))

	select {
	case t := <-tm2.C:
		fmt.Printf("tm2开始的时间: %v\n", sm2Start.Unix())
		fmt.Printf("通道中事件的时间：%v\n", t.Unix())
		if t.Sub(sm2Start) <= time.Second+time.Millisecond {
			fmt.Println("通道中的时间是重新设置sm2前的时间，即第一次超时的时间，所以第二次Reset失败了")
		}
	}

	fmt.Printf("读通道后，其中事件的数量:%d\n", len(tm2.C))
	tm2.Reset(time.Second)
	fmt.Printf("再次Reset后，通道中事件的数量:%d\n", len(tm2.C))
	time.Sleep(2 * time.Second)
	fmt.Printf("超时后通道中事件的数量:%d\n", len(tm2.C))
}

func test3() {
	fmt.Println("\n第3个测试：Reset前清空通道，尽可能通畅")
	smStart := time.Now()
	tm := time.NewTimer(time.Second)
	time.Sleep(2 * time.Second)
	
	// 停掉定时器再清空
	if !tm.Stop() && len(tm.C) > 0 {
		<-tm.C
	}
	tm.Reset(time.Second)

	// 超时
	t := <-tm.C
	fmt.Printf("tm开始的时间: %v\n", smStart.Unix())
	fmt.Printf("通道中事件的时间：%v\n", t.Unix())
	if t.Sub(smStart) <= time.Second+time.Millisecond {
		fmt.Println("通道中的时间是重新设置sm前的时间，即第一次超时的时间，所以第二次Reset失败了")
	} else {
		fmt.Println("通道中的时间是重新设置sm后的时间，Reset成功了")
	}
}

func main() {
	test1()
	test2()
	test3()
}
```


# 补充
1. 在Github的讨论：https://github.com/developer-learning/reading-go/issues/371
2. 跟曹大的讨论：我认为1个P某个时刻上1个G，1个P又1个timerBucket，这就形成了一一对应的关系，认为timerBucket锁没用。曹大最后说到了goroutine栈扩容，如果不加锁，g1运行到操作定时器的某个函数时，比如deltimerLocked，进行了栈扩容，后来其他goroutine g2执行，那岂不是就是多个goroutine访问timerBucket了，g1还没操作完，g2又操作了？然后曹大扔给我了栈扩容文章：https://github.com/go-internals-cn/go-internals/tree/master/chapter1_assembly_primer

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/09/04/explore-golang-timer/](http://lessisbetter.site/2018/09/04/explore-golang-timer/)