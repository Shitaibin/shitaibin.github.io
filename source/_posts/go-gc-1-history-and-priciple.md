---
title: Go垃圾回收 1：历史和原理
date: 2019-10-20 11:13:11
tags: ['Go']
---



新老朋友好久不见，我是大彬。今天为大家带来的分享是Go语言垃圾回收，这篇文章筹划的了很久，因为GC也是很强大的一个话题，关于GC已经有很多篇论文还有书籍，想通过一篇文章来介绍Go语言的垃圾回收是困难的，所以决定分几篇文章来完成Go语言垃圾回收的相关话题：

1. Go垃圾回收 1: 历史和原理
1. Go垃圾回收 2: GC主要流程
1. Go垃圾回收 3: 源码分析
1. Go垃圾回收 4: GC对性能的影响与优化

虽然划分成了3部分，但每个子话题依然很大，依然难写，依然大而不全，每一篇文章都会有宏观与细节，这样的大而不全对于不了解GC的朋友是好事，即可以有宏观上的认识，又可以有重要细节的感知。

这篇文章就是第一个话题：Go垃圾回收历史和原理，希望各位有所收获。

## Go语言垃圾回收简介

**垃圾**指内存中不再使用的内存区域，自动发现与释放这种内存区域的过程就是垃圾回收。

内存资源是有限的，而垃圾回收可以让内存重复使用，并且减轻开发者对内存管理的负担，减少程序中的内存问题。

以下是从网上对垃圾回收的2个定义：

> 1. Garbage consists of objects that are dead.
> 2. In tracing garbage collection, the term is sometimes used to mean objects that are known to be dead; that is, objects that are unreachable.

### Go垃圾回收发展史

- [go1.1](https://golang.org/doc/go1.1#performance)，提高效率和垃圾回收精确度。
- [go1.3](https://golang.org/doc/go1.3#garbage_collector)，提高了垃圾回收的精确度。
- [go1.4](https://golang.org/doc/go1.4#runtime)，之前版本的runtime大部分是使用C写的，这个版本大量使用Go进行了重写，让GC有了扫描stack的能力，进一步提高了垃圾回收的精确度。

- [go1.5](https://golang.org/doc/go1.5#gc)，目标是降低GC延迟，采用了**并发标记和并发清除，三色标记**，**write barrier**，以及实现了更好的**回收器调度**，设计[文档1](https://docs.google.com/document/d/16Y4IsnNRCN43Mx0NZc5YXZLovrHvvLhK_h0KN8woTO4/edit)，[文档2](https://golang.org/s/go15gcpacing)，以及这个版本的[Go talk][gotalk]。
- [go1.6](https://golang.org/doc/go1.6)，小优化，当程序使用大量内存时，GC暂停时间有所降低。
- [go1.7](https://golang.org/doc/go1.7)，小优化，当程序有大量空闲goroutine，stack大小波动比较大时，GC暂停时间有显著降低。
- [go1.8](https://golang.org/doc/go1.8)，**write barrier切换到hybrid write barrier**，以消除STW中的re-scan，把STW的最差情况降低到**50us**，设计[文档](https://github.com/golang/proposal/blob/master/design/17503-eliminate-rescan.md)。
- [go1.9](https://golang.org/doc/go1.9#gc)，提升指标比较多，1）过去 [`runtime.GC`](https://golang.org/pkg/runtime/#GC), [`debug.SetGCPercent`](https://golang.org/pkg/runtime/debug/#SetGCPercent), 和 [`debug.FreeOSMemory`](https://golang.org/pkg/runtime/debug/#FreeOSMemory)都不能触发**并发GC**，他们触发的GC都是阻塞的，go1.9可以了，变成了在垃圾回收之前只阻塞调用GC的goroutine。2）[`debug.SetGCPercent`](https://golang.org/pkg/runtime/debug/#SetGCPercent)只在有必要的情况下才会触发GC。
- [go.1.10](https://golang.org/doc/go1.10#performance)，小优化，加速了GC，程序应当运行更快*一点点*。
- [go1.12](https://golang.org/doc/go1.12)，显著提高了堆内存存在大碎片情况下的sweeping性能，能够降低GC后立即分配内存的延迟。


以上的历史版本信息都来自[Go release归档](https://golang.org/doc/devel/release.html)，有兴趣可以去翻阅一下。


### Go垃圾回收主要流程

下面这幅图来自Go1.5的[go talk][gotalk]，虽然go1.12的GC与go1.5有了许多改变，但总体的流程没有较大改变，并且也找不到官方更新的图了，所有就用这幅图介绍GC主流程。

![Go GC](http://img.lessisbetter.site/2019-10-gc-go1.7.png)


Go 垃圾回收是分**轮次**的，每一轮GC都是从 Off 状态开始，如果不是 Off 状态，则代表上一轮GC还未完成，如果这时修改指针的值，是直接修改的。

Go 垃圾回收的主要分2部分，第1部分是扫描所有对象进行三色标记，标记为黑色、灰色和白色，标记完成后只有黑色和白色对象，黑色代表使用中对象，白色对象代表垃圾，灰色是白色过渡到黑色的中间临时状态，第2部分是清扫垃圾，即清理白色对象。

第1部分包含了栈扫描、标记和标记结束3个阶段。在栈扫描之前有2个重要的准备：STW（Stop The World）和开启**写屏障**（WB，Write Barrier）。

STW是为了暂停当前所有运行中的goroutine，进行一些准备工作，比如开启WB，把全局变量，以及每个goroutine中的 **Root对象** 收集起来，Root对象是标记扫描的源头，可以从Root对象依次索引到使用中的对象。

![Objects Reference Tree](http://img.lessisbetter.site/2019-10-obj-tree.png)

> 假设内存中的对象用圆圈表示，那根据对象的指向关系，所有的对象可以组成若干依赖树，每一个 Root对象 都是树根，按图索骥能找到每一个使用中的对象。但树根不一定是Root对象，也有可能是垃圾，使用灰色树根代表Root对象，白色树根代表垃圾。

每个P都有一个 `mcache` ，每个 `mcache` 都有1个Span用来存放 TinyObject，TinyObject 都是不包含指针的对象，所以这些对象可以直接标记为黑色，然后关闭 STW。

> 如果不了解mcache和Tiny对象，赶紧翻一下这篇文章[Go内存分配那些事][go-memory-alloc]。

每个P都有1个进行扫描标记的 goroutine，可以进行并发标记，关闭STW后，这些 goroutine 就变成可运行状态，接收 Go Scheduler 的调度，被调度时执行1轮标记，它负责第1部分任务：栈扫描、标记和标记结束。

**栈扫描阶段**就是把前面搜集的Root对象找出来，标记为黑色，然后把它们引用的对象也找出来，标记为灰色，并且加入到**gcWork队列**，gcWork队列保存了灰色的对象，每个灰色的对象都是一个Work。

后面可以进入**标记阶段**，它是一个循环，不断的从gcWork队列中取出work，所指向的对象标记为黑色，该对象指向的对象标记为灰色，然后加入队列，直到队列为空。

然后进入**标记结束阶段**，再次开启STW，不同的版本处理方式是不同的。

在Go1.7的版本是**Dijkstra写屏障**，这个写屏障只监控堆上指针数据的变动，由于成本原因，没有监控栈上指针的变动，由于应用goroutine和GC的标记goroutine都在运行，当栈上的指针指向的对象变更为白色对象时，这个白色对象应当标记为黑色，需要再次扫描全局变量和栈，以免释放这类不该释放的对象。

在Go1.8及以后的版本引入了**混合写屏障**，这个写屏障依然不监控栈上指针的变动，但是它的策略，使得无需再次扫描栈和全局变量，但依然需要STW然后进行一些检查。

标记结束阶段的最后会关闭写屏障，然后关闭STW，唤醒熟睡已久的负责清扫垃圾的goroutine。

**清扫goroutine是应用启动后立即创建的一个后台goroutine**，它会立刻进入睡眠，等待被唤醒，然后执行垃圾清理：把白色对象挨个清理掉，清扫goroutine和应用goroutine是并发进行的。清扫完成之后，它再次进入睡眠状态，等待下次被唤醒。

最后执行一些数据统计和状态修改的工作，并且设置好触发下一轮GC的阈值，把GC状态设置为Off。

**以上就是Go垃圾回收的主要流程，但和go1.12的源码稍微有一些不同**，比如标记结束后，就开始设置各种状态数据以及把GC状态成了Off，在开启一轮GC时，会自动检测当前是否处于Off，如果不是Off，则当前goroutine会调用清扫函数，帮助清扫goroutine一起清扫span，实际的Go垃圾回收流程以源码为准。

主要流程是宏观一点的角度，接下去会扩散一下，介绍主要流程中提到的各种概念，比如三色标记、并发标记清理、STW、写屏障、辅助GC、GC persent。

## 几类垃圾回收思想

垃圾回收的研究已经存在了几十年，远在Go诞生之前，就存在了多种垃圾回收的思想，我们这里看几个跟Go垃圾回收相关的几个。

### Tracing GC

WIKI介绍：https://en.wikipedia.org/wiki/Tracing_garbage_collection

Tracing GC 是垃圾回收的一个大类，另外一个大类是**引用计数**，关于各种垃圾回收的类别可以看下这个系列文章[深入浅出垃圾回收](https://liujiacai.net/blog/2018/08/04/incremental-gc/)。

本文主要介绍Tracing GC的简要原理，我们首先看一下引用树的概念。把内存中所有的对象，都作为一个节点，对象A中的指针，指向了对象B，就存在从对象A指向对象B的一条边，对象B也可能指向了其他对象，那么根据指向关系就能生成一颗对象引用树。

![Objects Reference Tree](http://img.lessisbetter.site/2019-10-obj-ref-tree.png)

把内存中所有的对象引用树组合起来，就组成了一幅图。

![Memory Objects](http://img.lessisbetter.site/2019-10-mem-obj.png)

Tracing GC中有2类对象：

1. 可到达对象，即使用中对象
2. 不可到达对象，即垃圾

Tracing GC使用对象引用树找到所有可到达的对象，找到可到达对象有2个原则。



**原则1：被程序中调用栈，或者全局变量指向的对象是可到达对象。**

![Root Objects](http://img.lessisbetter.site/2019-10-obj-root.png)

**原则2：被可到达对象指向的对象也是可到达对象。**

A是可到达的，并且B被A引用，所以B也是可到达的。

![Reachable Objects](http://img.lessisbetter.site/2019-10-obj-reachable.png)

Tracing GC使用任何一种图论的遍历算法，都可以从**Root对象**，根据引用关系找到所有的可到达对象，并把他们做标记。Tracing GC扫描后，**黑色**对象为可到达对象，剩下的**白色**对象为不可到达对象。

> 原生的 Tracing GC 只有黑色和白色2种颜色。

![Tracing GC](http://img.lessisbetter.site/2019-10-obj-traced.png)

### 增量式垃圾回收思想

垃圾回收离不开STW，STW是Stop The World，指会暂停所有正在执行的用户线程/协程，进行垃圾回收的操作，STW为垃圾对象的扫描和标记提供了必要的条件。

**非增量式垃圾**回收需要STW，在STW期间完成**所有**垃圾对象的标记，STW结束后慢慢的执行垃圾对象的清理。

**增量式垃圾回收**也需要STW，在STW期间完成**部分**垃圾对象的标记，然后结束STW继续执行用户线程，一段时间后再次执行STW再标记**部分**垃圾对象，这个过程会多次重复执行，直到**所有**垃圾对象标记完成。

![Increment GC](http://img.lessisbetter.site/2019-10-increment-gc.png)

GC算法有3大性能指标：吞吐量、最大暂停时间（最大的STW占时）、内存占用率。**增量式垃圾回收不能提高吞吐量，但和非增量式垃圾回收相比，每次STW的时间更短，能够降低最大暂停时间**，就是Go每个版本Release Note中提到的GC延迟、GC暂停时间。

下图是非增量式GC和增量式GC的对比：

![Normal V.S. Increment GC](http://img.lessisbetter.site/2019-10-normal-vs-incremnt.png)


> 以上图片来自 [Incremental Garbage Collection in Ruby 2.2](https://blog.heroku.com/incremental-gc) ，它也很好的介绍了增量式垃圾回收的思想。

### 并发垃圾回收

减少最大暂停时间还有一种思路：并发垃圾回收，注意不是并行垃圾回收。

**并行垃圾回收**是每个核上都跑垃圾回收的线程，同时进行垃圾回收，这期间为STW，会暂停用户线程的执行。

**并发垃圾回收**是先STW找到所有的Root对象，然后结束STW，让垃圾标记线程和用户线程并发执行，垃圾标记完成后，再次开启STW，再次扫描和标记，以免释放使用中的内存。

并发垃圾回收和并行垃圾回收的重要区别就是不会持续暂停用户线程，并发垃圾回收也降低了STW的时间，达到了减少最大暂停时间的目的。

![](https://dt-cdn.net/images/the-different-gc-algorithms-510-ed7afde0fb.png)


> 图片来自 [Reducing Garbage-Collection Pause Time](https://www.dynatrace.com/resources/ebooks/javabook/reduce-garbage-collection-pause-time/) ，橙色线条为垃圾回收线程的运行，蓝色线条为用户线程。

## Go垃圾回收主要原理

### 三色标记

**为什么需要三色标记？**

三色标记的目的，主要是利用Tracing GC做增量式垃圾回收，降低最大暂停时间。原生Tracing GC只有黑色和白色，没有中间的状态，这就要求GC扫描过程必须一次性完成，得到最后的黑色和白色对象。在前面增量式GC中介绍到了，这种方式会存在较大的暂停时间。

三色标记增加了中间状态灰色，增量式GC运行过程中，应用线程的运行可能改变了对象引用树，只要让黑色对象不直接引用白色对象，GC就可以增量式的运行，减少停顿时间。

**什么是三色标记？**

三色标记，望文生义可以知道它由3种颜色组成：
1. 黑色 Black：表示对象是**可达的**，即使用中的对象，黑色是已经被扫描的对象。
1. 灰色 Gary：表示**被黑色对象直接引用的对象**，但还没对它进行扫描。
1. 白色 White：白色是对象的初始颜色，如果扫描完成后，对象依然还是白色的，说明此对象是垃圾对象。

三色标记规则：
1. 黑色不能指向白色对象。
2. 即黑色可以指向灰色，灰色可以指向白色。


三色标记主要流程：

1. 初始所有对象被标记为白色。
1. 寻找所有Root对象，比如被线程直接引用的对象，把Root对象标记为灰色。
1. 把灰色对象标记为黑色，并把它们引用的对象标记为灰色。
1. 持续遍历每一个灰色对象，直到没有灰色对象。
1. 剩余白色对象为垃圾对象。

推荐一篇结合Go代码展示了三色标记的过程的优秀文章：
[Golang’s Real-time GC in Theory and Practice](https://making.pusher.com/golangs-real-time-gc-in-theory-and-practice/) 。

**记录三色的方法简介**

Go1.12 使用位图和队列结合表示三种颜色状态：
1. 白色：位图没有标记被扫描。
1. 灰色：位图被标记已扫描，并且对象在队列。
1. 黑色：位图被标记已扫描，并且对象已从队列弹出。

位图是全局的，表示了Heap中内存块是否被扫描，是否包含指针等。

队列有全局的一个和每个P有一个本地队列，扫描对象进行标记的过程，优先处理本P的队列，其思想与P的g本地队列和全局队列类似，减少资源竞争，提高并行化。

### 写屏障

我们结合一段用户代码介绍写屏障：

```go
A.Next = B
A.Next = &C{}
```

三色标记的扫描线程是跟用户线程并发执行的，考虑这种情况：

用户线程执行完 `A.Next = B` 后，扫描线程把A标记为黑色，B标记为灰色，用户线程执行 `A.Next = &C{}` ，C是新对象，被标记为白色，由于A已经被扫描，不会重复扫描，所以C不会被标记为灰色，造成了黑色对象指向白色对象的情况，这违反了三色标记中的不变性规则，结果是C被认为是垃圾对象，最终被清扫掉，当访问C时会造成非法内存访问而Panic。

写屏障可以解决这个问题，当对象引用树发生改变时，即对象指向关系发生变化时，将被指向的对象标记为灰色，维护了三色标记的约束：黑色对象不能直接引用白色对象，这避免了使用中的对象被释放。

有写屏障后，用户线程执行 `A.Next = &C{}` 后，写屏障把C标记为灰色。

### 并发标记

并发垃圾回收的主要思想上文已经介绍，Go的垃圾回收为每个P都分配了一个gcMarker协程，用于并发标记对象，这样有些P在标记对象，而有些P上继续运行用户协程。

Go的并发标记有4种运行模式，还没深入研究，这里举一个并发标记的场景：在goroutine的调度过程中，如果当前P上已经没有g可以执行，也偷不到g时，P就空闲下来了，这时候可以运行当前P的gcMarker协程。


### 触发GC

GC有3种触发方式：

* 辅助GC
  
  在分配内存时，会判断当前的Heap内存分配量是否达到了触发一轮GC的阈值（每轮GC完成后，该阈值会被动态设置），如果超过阈值，则启动一轮GC。

* 调用`runtime.GC()`强制启动一轮GC。

* **sysmon**是运行时的守护进程，当超过 `forcegcperiod` (2分钟)没有运行GC会启动一轮GC。

### GC调节参数

Go垃圾回收不像Java垃圾回收那样，有很多参数可供调节，Go为了保证使用GC的简洁性，只提供了一个参数`GOGC`。

`GOGC`代表了占用中的内存增长比率，达到该比率时应当触发1次GC，该参数可以通过环境变量设置。

它的单位是百分比，取值范围并不是 [0, 100]，可以是1000，甚至2000，2000时代表2000%，即20倍。

假如当前heap占用内存为4MB，`GOGC = 75`，

```
4 * (1+75%) = 7MB
```

等heap占用内存大小达到7MB时会触发1轮GC。

`GOGC`还有2个特殊值：
1. `"off"` : 代表关闭GC
2. `0` : 代表持续进行垃圾回收，只用于调试 


## 总结

本文主要介绍了Go垃圾回收的发展史，以及Go垃圾回收的一些主要概念，是为掌握Go垃圾回收提供一个基础。下期文章将把本文提到的概念串起来，介绍Go垃圾回收的主要流程，下期见。

## 参考资料

* [一个专家眼中的Go与Java垃圾回收算法大对比](https://cloud.tencent.com/developer/article/1186944)

  这篇文章介绍了一些垃圾回收的标准，比如GC吞吐量、分配性能、暂停时间等等。

* [理解垃圾回收算法](https://www.infoq.cn/article/2017/03/garbage-collection-algorithm)

  这篇文章介绍了几种常见的垃圾机制，并使用gif展示回收过程。


* [深入浅出垃圾回收（一）简介篇](https://liujiacai.net/blog/2018/06/15/garbage-collection-intro/)，[深入浅出垃圾回收（三）增量式 GC](https://liujiacai.net/blog/2018/08/04/incremental-gc/)，[深入浅出垃圾回收（四）分代式 GC](https://liujiacai.net/blog/2018/08/18/generational-gc/)

  这个系列文章介绍了垃圾回收的概念、策略，以及三色标记等增量回收，以及分代收集。

* [Go gc](https://engineering.linecorp.com/en/blog/go-gc/)

  这篇文章做了Go和Java GC的简单对比表。看起来Go Gc比JVM GC少很多东西，但这其中解释了一些理由。

  Go没有使用compaction来解决碎片问题，而是使用了TCMalloc来减缓碎片和优化分配。

|                   | JAVA (JAVA8 HOTSPOT VM)                                 | GO                  |
| ----------------- | ------------------------------------------------------- | ------------------- |
| Collector         | Several collectors (Serial, Parallel, CMS, G1)          | CMS                 |
| Compaction        | Compacts                                                | Does not compact    |
| Generational GC   | Generational GC                                         | Non-generational GC |
| Tuning parameters | Depends on the collector.Multiple parameters available. | Go垃圾回收 only     |


* [【译】 Golang 中的垃圾回收（一）](https://juejin.im/post/5d2825bff265da1b6836e8d4)

  这篇文章是William Kennedy垃圾回收系列文章的第一篇的译文，这个文章从宏观的角度介绍了垃圾回收的原理，把垃圾回收跟调度结合起来介绍，分析了Go GC是如何实现低延时的。并且详细介绍了并发标记、STW、并发清除等。

* [图解Golang的GC算法](https://i6448038.github.io/2019/03/04/golang-garbage-collector/)

  RyuGou用图的方式简述了三色标记法的标记清除过程以及写屏障。

* [Golang’s Real-time GC in Theory and Practice](https://making.pusher.com/golangs-real-time-gc-in-theory-and-practice/)

  这篇文章有一个非常棒的GC动画。

* [学习 Golang GC](https://blog.wangriyu.wang/2019/04-Golang-GC.html)

  这篇文章对GC的历史、原理、goroutine栈，Go GC历史，基础原理，触发时间都有介绍，是一篇大而全的文章，但每个部分确实也都不详细，值得再参考。

* [Golang 垃圾回收剖析](http://legendtkl.com/2017/04/28/golang-gc/)


* [Golang源码探索(三) GC的实现原理](https://www.cnblogs.com/zkweb/p/7880099.html)

  Go垃圾回收的绝佳源码文章，图文并茂，从内存分配，讲到垃圾回收。


* [Go talk 2015: Go Gc: Latency Problem Solved](https://talks.golang.org/2015/go-gc.pdf)
  
  go1.5降低GC延迟的PPT介绍。

* [Proposal: Eliminate STW stack re-scanning](<https://github.com/golang/proposal/blob/master/design/17503-eliminate-rescan.md>)

  消除Go垃圾回收中第二次STW的re-scanning的提案。


[gotalk]: https://talks.golang.org/2015/go-gc.pdf "Go talk: go1.5"
[go-memory-alloc]: https://mp.weixin.qq.com/s/3gGbJaeuvx4klqcv34hmmw "Go内存分配那些事，就这么简单!"

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/10/20/go-gc-1-history-and-priciple/](http://lessisbetter.site/2019/10/20/go-gc-1-history-and-priciple/)

<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="http://img.lessisbetter.site/blog-gzh.png" style="border:0"  align=center />