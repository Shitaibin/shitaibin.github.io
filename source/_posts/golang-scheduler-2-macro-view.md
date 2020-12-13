---
title: Go调度器系列（2）宏观看调度器
date: 2019-03-26 17:29:29
tags: ['Go']
---


上一篇文章[《Go语言高阶：调度器系列（1）起源》](http://lessisbetter.site/2019/03/10/golang-scheduler-1-history/)，学goroutine调度器之前的一些背景知识，**这篇文章则是为了对调度器有个宏观的认识，从宏观的3个角度，去看待和理解调度器是什么样子的，但仍然不涉及具体的调度原理**。

三个角度分别是：

1. 调度器的宏观组成
2. 调度器的生命周期
3. GMP的可视化感受

在开始前，先回忆下调度器相关的3个缩写：

- **G**: goroutine，每个G都代表1个goroutine 
- **M**: 工作线程，是Go语言定义出来在用户层面描述系统线程的对象 ，每个M代表一个系统线程
- **P**: 处理器，它包含了运行Go代码的资源。

3者的简要关系是P拥有G，M必须和一个P关联才能运行P拥有的G。 

### 调度器的功能

[《Go语言高阶：调度器系列（1）起源》](http://lessisbetter.site/2019/03/10/golang-scheduler-1-history/)中介绍了协程和线程的关系，协程需要运行在线程之上，线程由CPU进行调度。

在Go中，**线程是运行goroutine的实体，调度器的功能是把可运行的goroutine分配到工作线程上**。

Go的调度器也是经过了多个版本的开发才是现在这个样子的，

- 1.0版本发布了最初的、最简单的调度器，是G-M模型，存在4类问题
- 1.1版本重新设计，修改为G-P-M模型，奠定当前调度器基本模样
- [1.2版本](https://golang.org/doc/go1.2#preemption)加入了抢占式调度，防止协程不让出CPU导致其他G饿死



> 在`$GOROOT/src/runtime/proc.go`的开头注释中包含了对Scheduler的重要注释，介绍Scheduler的设计曾拒绝过3种方案以及原因，本文不再介绍了，希望你不要忽略为数不多的官方介绍。



### Scheduler的宏观组成

[Tony Bai](https://tonybai.com/)在[《也谈goroutine调度器》](https://tonybai.com/2017/06/23/an-intro-about-goroutine-scheduler/)中的这幅图，展示了goroutine调度器和系统调度器的关系，而不是把二者割裂开来，并且从宏观的角度展示了调度器的重要组成。

![](https://lessisbetter.site/images/2019-03-goroutine-scheduler-model.png)



自顶向下是调度器的4个部分：

1. **全局队列**（Global Queue）：存放等待运行的G。
1. **P的本地队列**：同全局队列类似，存放的也是等待运行的G，存的数量有限，不超过256个。新建G'时，G'优先加入到P的本地队列，如果队列满了，则会把本地队列中一半的G移动到全局队列。
2. **P列表**：所有的P都在程序启动时创建，并保存在数组中，最多有GOMAXPROCS个。
3. **M**：线程想运行任务就得获取P，从P的本地队列获取G，P队列为空时，M也会尝试从全局队列**拿**一批G放到P的本地队列，或从其他P的本地队列**偷**一半放到自己P的本地队列。M运行G，G执行之后，M会从P获取下一个G，不断重复下去。

**Goroutine调度器和OS调度器是通过M结合起来的，每个M都代表了1个内核线程，OS调度器负责把内核线程分配到CPU的核上执行**。

### 调度器的生命周期

接下来我们从另外一个宏观角度——生命周期，认识调度器。

所有的Go程序运行都会经过一个完整的调度器生命周期：从创建到结束。

![](https://lessisbetter.site/images/2019-03-scheduler-lifetime.png)

即使下面这段简单的代码：

```go
package main

import "fmt"

// main.main
func main() {
	fmt.Println("Hello scheduler")
}
```

也会经历如上图所示的过程：
1. runtime创建最初的线程m0和goroutine g0，并把2者关联。
2. 调度器初始化：初始化m0、栈、垃圾回收，以及创建和初始化由GOMAXPROCS个P构成的P列表。
3. 示例代码中的main函数是`main.main`，`runtime`中也有1个main函数——`runtime.main`，代码经过编译后，`runtime.main`会调用`main.main`，程序启动时会为`runtime.main`创建goroutine，称它为main goroutine吧，然后把main goroutine加入到P的本地队列。
4. 启动m0，m0已经绑定了P，会从P的本地队列获取G，获取到main goroutine。
5. G拥有栈，M根据G中的栈信息和调度信息设置运行环境
6. M运行G
7. G退出，再次回到M获取可运行的G，这样重复下去，直到`main.main`退出，`runtime.main`执行Defer和Panic处理，或调用`runtime.exit`退出程序。

调度器的生命周期几乎占满了一个Go程序的一生，`runtime.main`的goroutine执行之前都是为调度器做准备工作，`runtime.main`的goroutine运行，才是调度器的真正开始，直到`runtime.main`结束而结束。

### GMP的可视化感受

上面的两个宏观角度，都是根据文档、代码整理出来，最后我们从可视化角度感受下调度器，有2种方式。

**方式1：go tool trace**

trace记录了运行时的信息，能提供可视化的Web页面。

简单测试代码：main函数创建trace，trace会运行在单独的goroutine中，然后main打印"Hello trace"退出。

```go
func main() {
	// 创建trace文件
	f, err := os.Create("trace.out")
	if err != nil {
		panic(err)
	}
	defer f.Close()

	// 启动trace goroutine
	err = trace.Start(f)
	if err != nil {
		panic(err)
	}
	defer trace.Stop()

	// main
	fmt.Println("Hello trace")
}
```

运行程序和运行trace：

```bash
➜  trace git:(master) ✗ go run trace1.go
Hello trace
➜  trace git:(master) ✗ ls
trace.out trace1.go
➜  trace git:(master) ✗
➜  trace git:(master) ✗ go tool trace trace.out
2019/03/24 20:48:22 Parsing trace...
2019/03/24 20:48:22 Splitting trace...
2019/03/24 20:48:22 Opening browser. Trace viewer is listening on http://127.0.0.1:55984
```

效果：

![trace1](https://lessisbetter.site/images/2019-03-go-tool-trace.png)

从上至下分别是goroutine（G）、堆、线程（M）、Proc（P）的信息，从左到右是时间线。用鼠标点击颜色块，最下面会列出详细的信息。

我们可以发现：

- `runtime.main`的goroutine是`g1`，这个编号应该永远都不变的，`runtime.main`是在`g0`之后创建的第一个goroutine。
- g1中调用了`main.main`，创建了`trace goroutine g18`。g1运行在P2上，g18运行在P0上。
- P1上实际上也有goroutine运行，可以看到短暂的竖线。

go tool trace的资料并不多，如果感兴趣可阅读：https://making.pusher.com/go-tool-trace/ ，中文翻译是：https://mp.weixin.qq.com/s/nf_-AH_LeBN3913Pt6CzQQ 。

**方式2：Debug trace**

示例代码：

```go
// main.main
func main() {
	for i := 0; i < 5; i++ {
		time.Sleep(time.Second)
		fmt.Println("Hello scheduler")
	}
}
```

编译和运行，运行过程会打印trace：

```bash
➜  one_routine2 git:(master) ✗ go build .
➜  one_routine2 git:(master) ✗ GODEBUG=schedtrace=1000 ./one_routine2
```

结果：

```log
SCHED 0ms: gomaxprocs=8 idleprocs=5 threads=5 spinningthreads=1 idlethreads=0 runqueue=0 [0 0 0 0 0 0 0 0]
SCHED 1001ms: gomaxprocs=8 idleprocs=8 threads=5 spinningthreads=0 idlethreads=3 runqueue=0 [0 0 0 0 0 0 0 0]
Hello scheduler
SCHED 2002ms: gomaxprocs=8 idleprocs=8 threads=5 spinningthreads=0 idlethreads=3 runqueue=0 [0 0 0 0 0 0 0 0]
Hello scheduler
SCHED 3004ms: gomaxprocs=8 idleprocs=8 threads=5 spinningthreads=0 idlethreads=3 runqueue=0 [0 0 0 0 0 0 0 0]
Hello scheduler
SCHED 4005ms: gomaxprocs=8 idleprocs=8 threads=5 spinningthreads=0 idlethreads=3 runqueue=0 [0 0 0 0 0 0 0 0]
Hello scheduler
SCHED 5013ms: gomaxprocs=8 idleprocs=8 threads=5 spinningthreads=0 idlethreads=3 runqueue=0 [0 0 0 0 0 0 0 0]
Hello scheduler
```

看到这密密麻麻的文字就有点担心，不要愁！因为每行字段都是一样的，各字段含义如下：

- SCHED：调试信息输出标志字符串，代表本行是goroutine调度器的输出；
- 0ms：即从程序启动到输出这行日志的时间；
- gomaxprocs: P的数量，本例有8个P；
- idleprocs: 处于idle状态的P的数量；通过gomaxprocs和idleprocs的差值，我们就可知道执行go代码的P的数量；
- threads: os threads/M的数量，包含scheduler使用的m数量，加上runtime自用的类似sysmon这样的thread的数量；
- spinningthreads: 处于自旋状态的os thread数量；
- idlethread: 处于idle状态的os thread的数量；
- runqueue=0： Scheduler全局队列中G的数量；
- `[0 0 0 0 0 0 0 0]`: 分别为8个P的local queue中的G的数量。

看第一行，含义是：刚启动时创建了8个P，其中5个空闲的P，共创建5个M，其中1个M处于自旋，没有M处于空闲，8个P的本地队列都没有G。

再看个复杂版本的，加上`scheddetail=1`可以打印更详细的trace信息。

命令：

```bash
➜  one_routine2 git:(master) ✗ GODEBUG=schedtrace=1000,scheddetail=1 ./one_routine2
```

结果：

![](https://lessisbetter.site/images/2019-03-for-print-syscall.png)
*截图可能更代码匹配不起来，最初代码是for死循环，后面为了减少打印加了限制循环5次*


每次分别打印了每个P、M、G的信息，P的数量等于`gomaxprocs`，M的数量等于`threads`，主要看圈黄的地方：

- 第1处：P1和M2进行了绑定。
- 第2处：M2和P1进行了绑定，但M2上没有运行的G。
- 第3处：代码中使用fmt进行打印，会进行系统调用，P1系统调用的次数很多，说明我们的用例函数基本在P1上运行。
- 第4处和第5处：M0上运行了G1，G1的状态为3（系统调用），G进行系统调用时，M会和P解绑，但M会记住之前的P，所以M0仍然记绑定了P1，而P1称未绑定M。

### 总结时刻

这篇文章，从3个宏观的角度介绍了调度器，也许你依然不知道调度器的原理，心里感觉模模糊糊，没关系，一步一步走，通过这篇文章希望你了解了：

1. Go调度器和OS调度器的关系
2. Go调度器的生命周期/总体流程
3. P的数量等于GOMAXPROCS
4. M需要通过绑定的P获取G，然后执行G，不断重复这个过程



### 示例代码

本文所有示例代码都在Github，可通过阅读原文访问：[golang_step_by_step/tree/master/scheduler](https://github.com/Shitaibin/golang_step_by_step/tree/master/scheduler)

### 参考资料

- [Go程序的“一生”](https://zhuanlan.zhihu.com/p/28058856)
- [也谈goroutine调度器](https://tonybai.com/2017/06/23/an-intro-about-goroutine-scheduler/)
- [Debug trace, 当前调度器设计人Dmitry Vyukov的文章](https://software.intel.com/en-us/blogs/2014/05/10/debugging-performance-issues-in-go-programs)
- [Go tool trace中文翻译](https://mp.weixin.qq.com/s/nf_-AH_LeBN3913Pt6CzQQ)
- [Dave关于GODEBUG的介绍](https://dave.cheney.net/tag/godebug)



> 最近的感受是：自己懂是一个层次，能写出来需要抬升一个层次，给他人讲懂又需要抬升一个层次。希望朋友们有所收获。

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/03/26/golang-scheduler-2-macro-view/](http://lessisbetter.site/2019/03/26/golang-scheduler-2-macro-view/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="https://lessisbetter.site/images/2019-01-article_qrcode.jpg" style="border:0"  align=center />