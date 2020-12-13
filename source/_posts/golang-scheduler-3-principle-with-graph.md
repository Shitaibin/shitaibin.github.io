---
title: Go调度器系列（3）图解调度原理
date: 2019-04-04 13:02:19
tags: ['Go']
---



如果你已经阅读了前2篇文章：[《调度起源》](http://lessisbetter.site/2019/03/10/golang-scheduler-1-history/)和[《宏观看调度器》](http://lessisbetter.site/2019/03/26/golang-scheduler-2-macro-view/)，你对G、P、M肯定已经不再陌生，我们这篇文章就介绍Go调度器的基本原理，本文总结了12个主要的场景，覆盖了以下内容：

1. G的创建和分配。
2. P的本地队列和全局队列的负载均衡。
3. M如何寻找G。
4. M如何从G1切换到G2。
5. work stealing，M如何去偷G。
6. 为何需要自旋线程。
7. G进行系统调用，如何保证P的其他G'可以被执行，而不是饿死。
8. Go调度器的抢占。



### 12场景

> 提示：图在前，场景描述在后。


![](http://img.lessisbetter.site/2019-04-image-20190331190809649-4030489.png)

> 上图中三角形、正方形、圆形分别代表了M、P、G，正方形连接的绿色长方形代表了P的本地队列。

**场景1**：p1拥有g1，m1获取p1后开始运行g1，g1使用`go func()`创建了g2，为了局部性g2优先加入到p1的本地队列。



![](http://img.lessisbetter.site/2019-04-image-20190331190826838-4030506.png)



**场景2**：**g1运行完成后(函数：`goexit`)，m上运行的goroutine切换为g0，g0负责调度时协程的切换（函数：`schedule`）**。从p1的本地队列取g2，从g0切换到g2，并开始运行g2(函数：`execute`)。实现了**线程m1的复用**。

![](http://img.lessisbetter.site/2019-04-image-20190331160718646-4019638.png)

**场景3**：假设每个p的本地队列只能存4个g。g2要创建了6个g，前4个g（g3, g4, g5, g6）已经加入p1的本地队列，p1本地队列满了。

![](http://img.lessisbetter.site/2019-04-image-20190331160728024-4019648.png)

> 蓝色长方形代表全局队列。

**场景4**：g2在创建g7的时候，发现p1的本地队列已满，需要执行**负载均衡**，把p1中本地队列中前一半的g，还有新创建的g**转移**到全局队列（实现中并不一定是新的g，如果g是g2之后就执行的，会被保存在本地队列，利用某个老的g替换新g加入全局队列），这些g被转移到全局队列时，会被打乱顺序。所以g3,g4,g7被转移到全局队列。

![](http://img.lessisbetter.site/2019-04-image-20190331161138353-4019898.png)

**场景5**：g2创建g8时，p1的本地队列未满，所以g8会被加入到p1的本地队列。



![](http://img.lessisbetter.site/2019-04-image-20190331162734830-4020854.png)

**场景6**：**在创建g时，运行的g会尝试唤醒其他空闲的p和m执行**。假定g2唤醒了m2，m2绑定了p2，并运行g0，但p2本地队列没有g，m2此时为自旋线程（没有G但为运行状态的线程，不断寻找g，后续场景会有介绍）。

![](http://img.lessisbetter.site/2019-04-image-20190331162717486-4020837.png)



**场景7**：m2尝试从全局队列(GQ)取一批g放到p2的本地队列（函数：`findrunnable`）。m2从全局队列取的g数量符合下面的公式：

```
n = min(len(GQ)/GOMAXPROCS + 1, len(GQ/2))
```

公式的含义是，至少从全局队列取1个g，但每次不要从全局队列移动太多的g到p本地队列，给其他p留点。这是**从全局队列到P本地队列的负载均衡**。

假定我们场景中一共有4个P，所以m2只从能从全局队列取1个g（即g3）移动p2本地队列，然后完成从g0到g3的切换，运行g3。

![](http://img.lessisbetter.site/2020-09-go-scheduler-p8.png)

**场景8**：假设g2一直在m1上运行，经过2轮后，m2已经把g7、g4也挪到了p2的本地队列并完成运行，全局队列和p2的本地队列都空了，如上图左边。

**全局队列已经没有g，那m就要执行work stealing：从其他有g的p哪里偷取一半g过来，放到自己的P本地队列**。p2从p1的本地队列尾部取一半的g，本例中一半则只有1个g8，放到p2的本地队列，情况如上图右边。



![](http://img.lessisbetter.site/2019-04-image-20190331170113457-4022873.png)

**场景9**：p1本地队列g5、g6已经被其他m偷走并运行完成，当前m1和m2分别在运行g2和g8，m3和m4没有goroutine可以运行，m3和m4处于**自旋状态**，它们不断寻找goroutine。为什么要让m3和m4自旋，自旋本质是在运行，线程在运行却没有执行g，就变成了浪费CPU？销毁线程不是更好吗？可以节约CPU资源。创建和销毁CPU都是浪费时间的，我们**希望当有新goroutine创建时，立刻能有m运行它**，如果销毁再新建就增加了时延，降低了效率。当然也考虑了过多的自旋线程是浪费CPU，所以系统中最多有GOMAXPROCS个自旋的线程，多余的没事做线程会让他们休眠（见函数：`notesleep()`）。

![](http://img.lessisbetter.site/2019-04-image-20190331182939318-4028179.png)

**场景10**：假定当前除了m3和m4为自旋线程，还有m5和m6为自旋线程，g8创建了g9，g8进行了**阻塞的系统调用**，m2和p2立即解绑，p2会执行以下判断：如果p2本地队列有g、全局队列有g或有空闲的m，p2都会立马唤醒1个m和它绑定，否则p2则会加入到空闲P列表，等待m来获取可用的p。本场景中，p2本地队列有g，可以和其他自旋线程m5绑定。

**场景11**：（无图场景）g8创建了g9，假如g8进行了**非阻塞系统调用**（CGO会是这种方式，见`cgocall()`），m2和p2会解绑，但m2会记住p，然后g8和m2进入系统调用状态。当g8和m2退出系统调用时，会尝试获取p2，如果无法获取，则获取空闲的p，如果依然没有，g8会被记为可运行状态，并加入到全局队列。



**场景12**：（无图场景）Go调度在go1.12实现了抢占，应该更精确的称为**请求式抢占**，那是因为go调度器的抢占和OS的线程抢占比起来很柔和，不暴力，不会说线程时间片到了，或者更高优先级的任务到了，执行抢占调度。**go的抢占调度柔和到只给goroutine发送1个抢占请求，至于goroutine何时停下来，那就管不到了**。抢占请求需要满足2个条件中的1个：1）G进行系统调用超过20us，2）G运行超过10ms。调度器在启动的时候会启动一个单独的线程sysmon，它负责所有的监控工作，其中1项就是抢占，发现满足抢占条件的G时，就发出抢占请求。



### 场景融合

如果把上面所有的场景都融合起来，就能构成下面这幅图了，它从整体的角度描述了Go调度器各部分的关系。图的上半部分是G的创建、负债均衡和work stealing，下半部分是M不停寻找和执行G的迭代过程。

如果你看这幅图还有些似懂非懂，建议赶紧开始看[雨痕大神的Golang源码剖析](github.com/qyuhen/book)，章节：并发调度。

![](http://img.lessisbetter.site/2019-04-arch.png)



总结，Go调度器和OS调度器相比，是相当的轻量与简单了，但它已经足以撑起goroutine的调度工作了，并且让Go具有了原生（强大）并发的能力，这是伟大的。如果你记住的不多，你一定要记住这一点：**Go调度本质是把大量的goroutine分配到少量线程上去执行，并利用多核并行，实现更强大的并发。**

### 下集预告

下篇会是源码层面的内容了，关于源码分析的书籍、文章可以先看起来了，先剧透一篇图，希望阅读下篇文章赶紧关注本公众号。

![](http://img.lessisbetter.site/2019-04-flow.png)



### 推荐阅读

[Go调度器系列（1）起源](http://lessisbetter.site/2019/03/10/golang-scheduler-1-history/)
[Go调度器系列（2）宏观看调度器](http://lessisbetter.site/2019/03/26/golang-scheduler-2-macro-view/)



### 参考资料

在学习调度器的时候，看了很多文章，这里列一些重要的：

1. [The Go scheduler](https://morsmachine.dk/go-scheduler)
2. [Go's work-stealing scheduler](https://rakyll.org/scheduler/)，[中文翻译版](https://lingchao.xin/post/gos-work-stealing-scheduler.html)
3. [Go夜读：golang 中 goroutine 的调度](https://reading.developerlearning.cn/reading/12-2018-08-02-goroutine-gpm/)
4. [Scheduling In Go : Part I、II、III ](https://www.ardanlabs.com/blog/2018/08/scheduling-in-go-part2.html)，[中文翻译版](<https://www.jianshu.com/p/cb6881a2661d>)
5. [雨痕大神的golang源码剖析](https://github.com/qyuhen/book)
6. [也谈goroutine调度器](https://tonybai.com/2017/06/23/an-intro-about-goroutine-scheduler/)
7. [kavya的调度PPT](https://speakerdeck.com/kavya719/the-scheduler-saga)
8. [抢占的设计提案，Proposal: Non-cooperative goroutine preemption](https://github.com/golang/proposal/blob/master/design/24543-non-cooperative-preemption.md)


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/04/04/golang-scheduler-3-principle-with-graph/](http://lessisbetter.site/2019/04/04/golang-scheduler-3-principle-with-graph/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="http://img.lessisbetter.site/2019-01-article_qrcode.jpg" style="border:0"  align=center />