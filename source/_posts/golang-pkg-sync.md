---
title: Golang并发的次优选择：sync包
date: 2019-01-04 21:31:48
tags: ['Go']
---



我们都知道Golang并发优选channel，但channel不是万能的，Golang为我们提供了另一种选择：sync。通过这篇文章，你会了解sync包最基础、最常用的方法，至于sync和channel之争留给下一篇文章。

[sync包](https://golang.org/pkg/sync/)提供了基础的异步操作方法，比如互斥锁（Mutex）、单次执行（Once）和等待组（WaitGroup），这些异步操作主要是为低级库提供，上层的异步/并发操作最好选用通道和通信。

sync包提供了：
1. Mutex：互斥锁
1. RWMutex：读写锁
1. WaitGroup：等待组
1. Once：单次执行
1. Cond：信号量
1. Pool：临时对象池
1. Map：自带锁的map

这篇文章是sync包的入门文章，所以只介绍常用的结构和方法：`Mutex`、`RWMutex`、`WaitGroup`、`Once`，而`Cond`、`Pool`和`Map`留给大家自行探索，或有需求再介绍。

<!--more-->

### 互斥锁
常做并发工作的朋友对互斥锁应该不陌生，Golang里**互斥锁需要确保的是某段时间内，不能有多个协程同时访问一段代码（临界区）**。

互斥锁被称为`Mutex`，它有2个函数，`Lock()`和`Unlock()`分别是获取锁和释放锁，如下：
```go
type Mutex
func (m *Mutex) Lock(){}
func (m *Mutex) Unlock(){}
```

**`Mutex`的初始值为未锁的状态，并且`Mutex`通常作为结构体的匿名成员存在**。

经过了上面这么“官方”的介绍，举个例子：你在工商银行有100元存款，这张卡绑定了支付宝和微信，在中午12点你用支付宝支付外卖30元，你在微信发红包，抢到10块。银行需要按顺序执行上面两件事，先减30再加10或者先加10再减30，结果都是80，但如果同时执行，结果可能是，只减了30或者只加了10，即你有70元或者你有110元。前一个结果是你赔了，后一个结果是银行赔了，银行可不希望把这种事算错。

看看实际使用吧：创建一个银行，银行里存每个账户的钱，存储查询都加了锁操作，这样银行就不会算错账了。
银行的定义：
```go
type Bank struct {
	sync.Mutex
	saving map[string]int // 每账户的存款金额
}

func NewBank() *Bank {
	b := &Bank{
		saving: make(map[string]int),
	}
	return b
}
```

银行的存取钱：
```go
// Deposit 存款
func (b *Bank) Deposit(name string, amount int) {
	b.Lock()
	defer b.Unlock()

	if _, ok := b.saving[name]; !ok {
		b.saving[name] = 0
	}
	b.saving[name] += amount
}

// Withdraw 取款，返回实际取到的金额
func (b *Bank) Withdraw(name string, amount int) int {
	b.Lock()
	defer b.Unlock()

	if _, ok := b.saving[name]; !ok {
		return 0
	}
	if b.saving[name] < amount {
		amount = b.saving[name]
	}
	b.saving[name] -= amount

	return amount
}

// Query 查询余额
func (b *Bank) Query(name string) int {
	b.Lock()
	defer b.Unlock()

	if _, ok := b.saving[name]; !ok {
		return 0
	}

	return b.saving[name]
}
```

模拟操作：小米支付宝存了100，并且同时花了20。
```go
func main() {
	b := NewBank()
	go b.Deposit("xiaoming", 100)
	go b.Withdraw("xiaoming", 20)
	go b.Deposit("xiaogang", 2000)

	time.Sleep(time.Second)
	fmt.Printf("xiaoming has: %d\n", b.Query("xiaoming"))
	fmt.Printf("xiaogang has: %d\n", b.Query("xiaogang"))
}
```
结果：先存后花。
```bash
➜  sync_pkg git:(master) ✗ go run mutex.go
xiaoming has: 80
xiaogang has: 2000
```
也可能是：先花后存，因为先花20，因为小明没钱，所以没花出去。
```bash
➜  sync_pkg git:(master) ✗ go run mutex.go
xiaoming has: 100
xiaogang has: 2000
```

*这个例子只是介绍了mutex的基本使用，如果你想多研究下mutex，那就去我的Github（阅读原文）下载下来代码，自己修改测试。Github中还提供了没有锁的例子，运行多次总能碰到错误：*
> fatal error: concurrent map writes
这是由于并发访问map造成的。

### 读写锁


读写锁是互斥锁的特殊变种，如果是计算机基本知识扎实的朋友会知道，读写锁来自于读者和写者的问题，这个问题就不介绍了，介绍下我们的重点：**读写锁要达到的效果是同一时间可以允许多个协程读数据，但只能有且只有1个协程写数据**。

**也就是说，读和写是互斥的，写和写也是互斥的，但读和读并不互斥**。具体讲，当有至少1个协程读时，如果需要进行写，就必须等待所有已经在读的协程结束读操作，写操作的协程才获得锁进行写数据。当写数据的协程已经在进行时，有其他协程需要进行读或者写，就必须等待已经在写的协程结束写操作。

读写锁是`RWMutex`，它有5个函数，它需要为读操作和写操作分别提供锁操作，这样就4个了：
- `Lock()`和`Unlock()`是给写操作用的。 
- `RLock()`和`RUnlock()`是给读操作用的。

**`RLocker()`能获取读锁，然后传递给其他协程使用。使用较少**。

```go
type RWMutex
func (rw *RWMutex) Lock(){}
func (rw *RWMutex) RLock(){}
func (rw *RWMutex) RLocker() Locker{}
func (rw *RWMutex) RUnlock(){}
func (rw *RWMutex) Unlock(){}
```

上面的银行**实现不合理**：大家都是拿手机APP查余额，可以同时几个人一起查呀，这根本不影响，银行的锁可以换成读写锁。存、取钱是写操作，查询金额是读操作，代码修改如下，其他不变：
```go
type Bank struct {
	sync.RWMutex
	saving map[string]int // 每账户的存款金额
}

// Query 查询余额
func (b *Bank) Query(name string) int {
	b.RLock()
	defer b.RUnlock()

	if _, ok := b.saving[name]; !ok {
		return 0
	}

	return b.saving[name]
}

func main() {
	b := NewBank()
	go b.Deposit("xiaoming", 100)
	go b.Withdraw("xiaoming", 20)
	go b.Deposit("xiaogang", 2000)

	time.Sleep(time.Second)
	print := func(name string) {
		fmt.Printf("%s has: %d\n", name, b.Query(name))
	}

	nameList := []string{"xiaoming", "xiaogang", "xiaohong", "xiaozhang"}
	for _, name := range nameList {
		go print(name)
	}

	time.Sleep(time.Second)
}
```

结果，**可能不一样，因为协程都是并发执行的，执行顺序不固定**：
```go
➜  sync_pkg git:(master) ✗ go run rwmutex.go
xiaohong has: 0
xiaozhang has: 0
xiaogang has: 2000
xiaoming has: 100
```

### 等待组

互斥锁和读写锁大多数人可能比较熟悉，而对等待组（`WaitGroup`）可能就不那么熟悉，甚至有点陌生，所以先来介绍下等待组在现实中的例子。

你们团队有5个人，你作为队长要带领大家打开藏有宝藏的箱子，但这个箱子需要4把钥匙才能同时打开，你把寻找4把钥匙的任务，分配给4个队员，让他们分别去寻找，而你则守着宝箱，在这**等待**，等他们都找到回来后，一起插进钥匙打开宝箱。

这其中有个很重要的过程叫等待：**等待一些工作完成后，再进行下一步的工作**。如果使用Golang实现，就得使用等待组。

等待组是`WaitGroup`，它有3个函数:
- `Add()`：在被等待的协程启动前加1，代表要等待1个协程。
- `Done()`：被等待的协程执行Done，代表该协程已经完成任务，通知等待协程。
- `Wait()`: 等待其他协程的协程，使用Wait进行等待。
```go
type WaitGroup
func (wg *WaitGroup) Add(delta int){}
func (wg *WaitGroup) Done(){}
func (wg *WaitGroup) Wait(){}
```

来，一起看下怎么用WaitGroup实现上面的问题。

队长先创建一个WaitGroup对象wg，每个队员都是1个协程， 队长让队员出发前，使用`wg.Add()`，队员出发寻找钥匙，队长使用`wg.Wait()`等待（阻塞）所有队员完成，某个队员完成时执行`wg.Done()`，等所有队员找到钥匙，`wg.Wait()`则返回，完成了等待的过程，接下来就是开箱。

结合之前的协程池的例子，修改成WG等待协程池协程退出，实例代码：
```go
func leader() {
	var wg sync.WaitGroup
	wg.Add(4)
	for i := 0; i < 4; i++ {
		go follower(&wg, i)
	}
	wg.Wait()
	
	fmt.Println("open the box together")
}

func follower(wg *sync.WaitGroup, id int) {
	fmt.Printf("follwer %d find key\n", id)
	wg.Done()
}
```

结果:
```bah
➜  sync_pkg git:(master) ✗ go run waitgroup.go
follwer 3 find key
follwer 1 find key
follwer 0 find key
follwer 2 find key
open the box together
```

WaitGroup也常用在协程池的处理上，协程池等待所有协程退出，把上篇文章[《Golang并发模型：轻松入门协程池》](http://lessisbetter.site/2018/12/20/golang-simple-goroutine-pool/)的例子改下：
```go
func workerPool(n int, jobCh <-chan int, retCh chan<- string) {
	var wg sync.WaitGroup
	wg.Add(n)
	for i := 0; i < n; i++ {
		go worker(&wg, i, jobCh, retCh)
	}

	wg.Wait()
	close(retCh)
}

func worker(wg *sync.WaitGroup, id int, jobCh <-chan int, retCh chan<- string) {
	cnt := 0
	for job := range jobCh {
		cnt++
		ret := fmt.Sprintf("worker %d processed job: %d, it's the %dth processed by me.", id, job, cnt)
		retCh <- ret
	}

	wg.Done()
}
```
### 单次执行

在程序执行前，通常需要做一些初始化操作，但触发初始化操作的地方是有多处的，但是这个初始化又只能执行1次，怎么办呢？

使用Once就能轻松解决，`once`对象是用来存放**1个无入参无返回值的函数，once可以确保这个函数只被执行1次**。

```go
type Once
func (o *Once) Do(f func()){}
```

直接把官方代码给大家搬过来看下，once在10个协程中调用，但once中的函数`onceBody()`只执行了1次：
```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var once sync.Once
	onceBody := func() {
		fmt.Println("Only once")
	}
	done := make(chan bool)
	for i := 0; i < 10; i++ {
		go func() {
			once.Do(onceBody)
			done <- true
		}()
	}
	for i := 0; i < 10; i++ {
		<-done
	}
}
```

结果：
```bash
➜  sync_pkg git:(master) ✗ go run once.go
Only once
```

### 下期预告
这次先介绍入门的知识，下次再介绍一些深入思考、最佳实践，不能一口吃个胖子，咱们慢慢来，顺序渐进。

下一篇我以这些主题进行介绍，欢迎关注：
1. 哪个协程先获取锁
1. 一定要用锁吗
1. 锁与通道的选择

### 示例源码
本文所有示例源码，及历史文章、代码都存储在Github：[https://github.com/Shitaibin/golang_step_by_step/tree/master/sync_pkg](https://github.com/Shitaibin/golang_step_by_step/tree/master/sync_pkg)


### 文章推荐

1. [Golang并发模型：轻松入门流水线模型](http://lessisbetter.site/2018/11/16/golang-introduction-to-pipeline/)
1. [Golang并发模型：轻松入门流水线FAN模式](http://lessisbetter.site/2018/11/28/golang-pipeline-fan-model/)
1. [Golang并发模型：并发协程的优雅退出](http://lessisbetter.site/2018/12/02/golang-exit-goroutine-in-3-ways/)
1. [Golang并发模型：轻松入门select](http://lessisbetter.site/2018/12/13/golang-slect/)
1. [Golang并发模型：select进阶](http://lessisbetter.site/2018/12/17/golang-selete-advance/)
1. [Golang并发模型：轻松入门协程池](http://lessisbetter.site/2018/12/20/golang-simple-goroutine-pool/)
1. [Golang并发的次优选择：sync包](http://lessisbetter.site/2019/01/04/golang-pkg-sync/)


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有新文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/01/04/golang-pkg-sync/](http://lessisbetter.site/2019/01/04/golang-pkg-sync/)


<div style="text-align:center">关注公众号，获取最新Golang文章。</div>

<img src="http://img.lessisbetter.site/gzh-qrcode-with-text.png" style="border:0" width="256" hegiht="30" align=center />


<div style="color:#0096FF; text-align:center">一起学Golang-分享有料的Go语言技术</div>