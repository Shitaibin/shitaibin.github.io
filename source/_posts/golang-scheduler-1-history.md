---
title: Go调度器系列（1）起源
date: 2019-03-10 17:25:57
tags: ['Go']
---



如果把语言比喻为武侠小说中的武功，如果只是会用，也就是达到四五层，如果用的熟练也就六七层，如果能见招拆招也得八九层，如果你出神入化，立于不败之地十层。

如果你想真正掌握一门语言的，怎么也得八层以上，需要你深入了解这门语言方方面面的细节。

希望以后对Go语言的掌握能有八九层，怎么能不懂调度器！？

Google、百度、微信搜索了许多Go语言调度的文章，这些文章上来就讲调度器是什么样的，它由哪些组成，它的运作原理，搞的我只能从这些零散的文章中形成调度器的“概貌”，这是我想要的结果，但这还不够。

学习不仅要知其然，还要知其所以然。

学习之前，先学知识点的历史，再学知识，这样你就明白，为什么它是当下这个样子。

所以，我打算写一个goroutine调度器的系列文章，从历史背景讲起，循序渐进，希望大家能对goroutine调度器有一个全面的认识。

这篇文章介绍调度器相关的历史背景，请慢慢翻阅。

### 远古时代

![](https://lessisbetter.site/images/2019-03-Eniac.jpg)

上面这个大家伙是ENIAC，它诞生在宾夕法尼亚大学，是世界第一台真正的通用计算机，和现代的计算机相比，它是相当的“笨重”，它的计算能力，跟现代人手普及的智能手机相比，简直是一个天上一个地下，ENIAC在地下，智能手机在天上。

它上面没有操作系统，更别提进程、线程和协程了。

### 进程时代

![](https://lessisbetter.site/images/2019-03-apple-II.jpeg)

后来，现代化的计算机有了操作系统，每个程序都是一个进程，但是操作系统在一段时间只能运行一个进程，直到这个进程运行完，才能运行下一个进程，这个时期可以成为**单进程时代——串行时代**。

和ENIAC相比，单进程是有了几万倍的提度，但依然是太慢了，比如进程要读数据阻塞了，CPU就在哪浪费着，伟大的程序员们就想了，不能浪费啊，**怎么才能充分的利用CPU呢？**

后来操作系统就具有了**最早的并发能力：多进程并发**，当一个进程阻塞的时候，切换到另外等待执行的进程，这样就能尽量把CPU利用起来，CPU就不浪费了。

### 线程时代

![](https://lessisbetter.site/images/2019-03-Macintosh.jpeg)

多进程真实个好东西，有了对进程的调度能力之后，伟大的程序员又发现，进程拥有太多资源，在创建、切换和销毁的时候，都会占用很长的时间，CPU虽然利用起来了，但CPU有很大的一部分都被用来进行进程调度了，**怎么才能提高CPU的利用率呢？**

大家希望能有一种轻量级的进程，调度不怎么花时间，这样CPU就有更多的时间用在执行任务上。

后来，操作系统支持了线程，线程在进程里面，线程运行所需要资源比进程少多了，跟进程比起来，切换简直是“不算事”。

一个进程可以有多个线程，CPU在执行调度的时候切换的是线程，如果下一个线程也是当前进程的，就只有线程切换，“很快”就能完成，如果下一个线程不是当前的进程，就需要切换进程，这就得费点时间了。

这个时代，**CPU的调度切换的是进程和线程**。多线程看起来很美好，但实际多线程编程却像一坨屎，一是由于线程的设计本身有点复杂，而是由于需要考虑很多底层细节，比如锁和冲突检测。

### 协程

![](https://lessisbetter.site/images/2019-macbook-steve.jpeg)

多进程、多线程已经提高了系统的并发能力，但是在当今互联网高并发场景下，为每个任务都创建一个线程是不现实的，因为会消耗大量的内存（每个线程的内存占用级别为MB），线程多了之后调度也会消耗大量的CPU。伟大的程序员们有开始想了，**如何才能充分利用CPU、内存等资源的情况下，实现更高的并发**？

既然线程的资源占用、调度在高并发的情况下，依然是比较大的，是否有一种东西，更加轻量？

你可能知道：线程分为内核态线程和用户态线程，用户态线程需要绑定内核态线程，CPU并不能感知用户态线程的存在，它只知道它在运行1个线程，这个线程实际是内核态线程。

**用户态线程实际有个名字叫协程（co-routine）**，为了容易区分，我们使用协程指用户态线程，使用线程指内核态线程。

> User-level threads, Application-level threads, Green threads都指一样的东西，就是不受OS感知的线程，如果你Google coroutine相关的资料，会看到它指的就是用户态线程，在[Green threads的维基百科](https://en.wikipedia.org/wiki/Green_threads)里，看Green threads的实现列表，你会看到好很多coroutine实现，比如Java、Lua、Go、Erlang、Common Lisp、Haskell、Rust、PHP、Stackless Python，所以，我认为用户态线程就是协程。

协程跟线程是有区别的，线程由CPU调度是抢占式的，**协程由用户态调度是协作式的**，一个协程让出CPU后，才执行下一个协程。

协程和线程有3种映射关系：

- N:1，N个协程绑定1个线程，优点就是**协程在用户态线程即完成切换，不会陷入到内核态，这种切换非常的轻量快速**。但也有很大的缺点，1个进程的所有协程都绑定在1个线程上，一是某个程序用不了硬件的多核加速能力，二是一旦某协程阻塞，造成线程阻塞，本进程的其他协程都无法执行了，根本就没有并发的能力了。
- 1:1，1个协程绑定1个线程，这种最容易实现。协程的调度都由CPU完成了，不存在N:1缺点，但有一个缺点是协程的创建、删除和切换的代价都由CPU完成，有点略显昂贵了。
- M:N，M个协程绑定N个线程，是N:1和1:1类型的结合，克服了以上2种模型的缺点，但实现起来最为复杂。

协程是个好东西，不少语言支持了协程，比如：Lua、Erlang、Java（C++即将支持），就算语言不支持，也有库支持协程，比如C语言的[coroutine](https://github.com/cloudwu/coroutine/)（云风大牛作品）、Kotlin的kotlinx.coroutines、Python的gevent。

### goroutine

**Go语言的诞生就是为了支持高并发**，有2个支持高并发的模型：CSP和Actor。[鉴于Occam和Erlang都选用了CSP](https://golang.org/doc/faq)(来自Go FAQ)，并且效果不错，Go也选了CSP，但与前两者不同的是，Go把channel作为头等公民。

就像前面说的多线程编程太不友好了，**Go为了提供更容易使用的并发方法，使用了goroutine和channel**。goroutine来自协程的概念，让一组可复用的函数运行在一组线程之上，即使有协程阻塞，该线程的其他协程也可以被`runtime`调度，转移到其他可运行的线程上。最关键的是，程序员看不到这些底层的细节，这就降低了编程的难度，提供了更容易的并发。

Go中，协程被称为goroutine（Rob Pike说goroutine不是协程，因为他们并不完全相同），它非常轻量，一个goroutine只占几KB，并且这几KB就足够goroutine运行完，这就能在有限的内存空间内支持大量goroutine，支持了更多的并发。虽然一个goroutine的栈只占几KB，但实际是可伸缩的，如果需要更多内容，`runtime`会自动为goroutine分配。

### Go语言的老调度器

终于来到了Go语言的调度器环节。

**调度器的任务是在用户态完成goroutine的调度，而调度器的实现好坏，对并发实际有很大的影响，并且Go的调度器就是M:N类型的，实现起来也是最复杂**。

现在的Go语言调度器是2012年重新设计的（[设计方案](https://golang.org/s/go11sched)），在这之前的调度器称为老调度器，老调度器的实现不太好，存在性能问题，所以用了4年左右就被替换掉了，老调度器大概是下面这个样子：

![](https://lessisbetter.site/images/2019-03-old-scheduler.png)

最下面是操作系统，中间是runtime，runtime在Go中很重要，许多程序运行时的工作都由runtime完成，调度器就是runtime的一部分，虚线圈出来的为调度器，它有两个重要组成：

- **M，代表线程**，它要运行goroutine。
- Global G Queue，是全局goroutine队列，所有的goroutine都保存在这个队列中，**goroutine用G进行代表**。

M想要执行、放回G都必须访问全局G队列，并且M有多个，即多线程访问同一资源需要加锁进行保证互斥/同步，所以全局G队列是有互斥锁进行保护的。

老调度器有4个缺点：

1. 创建、销毁、调度G都需要每个M获取锁，这就形成了**激烈的锁竞争**。
2. M转移G会造成**延迟和额外的系统负载**。比如当G中包含创建新协程的时候，M创建了G’，为了继续执行G，需要把G’交给M’执行，也造成了**很差的局部性**，因为G’和G是相关的，最好放在M上执行，而不是其他M'。
3. M中的mcache是用来存放小对象的，mcache和栈都和M关联造成了大量的内存开销和差的局部性。
4. 系统调用导致频繁的线程阻塞和取消阻塞操作增加了系统开销。



### Go语言的新调度器

面对以上老调度的问题，Go设计了新的调度器，设计文稿：https://golang.org/s/go11sched

新调度器引入了：

- **P**：**Processor，它包含了运行goroutine的资源**，如果线程想运行goroutine，必须先获取P，P中还包含了可运行的G队列。
- work stealing：当M绑定的P没有可运行的G时，它可以从其他运行的M’那里偷取G。

现在，**调度器中3个重要的缩写你都接触到了，所有文章都用这几个缩写，请牢记**：

- **G**: goroutine 
- **M**: 工作线程 
- **P**: 处理器，它包含了运行Go代码的资源，M必须和一个P关联才能运行G。 



这篇文章的目的不是介绍调度器的实现，而是调度器的一些理念，帮助你后面更好理解调度器的实现，所以我们回归到调度器设计思想上。





![thoughts-of-scheduler](https://lessisbetter.site/images/2019-03-thoughts-of-scheduler.png)



调度器的有**两大思想**：

**复用线程**：协程本身就是运行在一组线程之上，不需要频繁的创建、销毁线程，而是对线程的复用。在调度器中复用线程还有2个体现：1）work stealing，当本线程无可运行的G时，尝试从其他线程绑定的P偷取G，而不是销毁线程。2）hand off，当本线程因为G进行系统调用阻塞时，线程释放绑定的P，把P转移给其他空闲的线程执行。

**利用并行**：GOMAXPROCS设置P的数量，当GOMAXPROCS大于1时，就最多有GOMAXPROCS个线程处于运行状态，这些线程可能分布在多个CPU核上同时运行，使得并发利用并行。另外，GOMAXPROCS也限制了并发的程度，比如GOMAXPROCS = 核数/2，则最多利用了一半的CPU核进行并行。

调度器的**两小策略**：

**抢占**：在coroutine中要等待一个协程主动让出CPU才执行下一个协程，在Go中，一个goroutine最多占用CPU 10ms，防止其他goroutine被饿死，这就是goroutine不同于coroutine的一个地方。

**全局G队列**：在新的调度器中依然有全局G队列，但功能已经被弱化了，当M执行work stealing从其他P偷不到G时，它可以从全局G队列获取G。



上面提到并行了，关于并发和并行再说一下：Go创始人Rob Pike一直在强调go是并发，不是并行，因为Go做的是在一段时间内完成几十万、甚至几百万的工作，而不是同一时间同时在做大量的工作。**并发可以利用并行提高效率，调度器是有并行设计的**。

并行依赖多核技术，每个核上在某个时间只能执行一个线程，当我们的CPU有8个核时，我们能同时执行8个线程，这就是并行。

![](https://lessisbetter.site/images/2019-03-concurrency-parallelism.png)




### 结束语

这篇文章的主要目的是为后面介绍Go语言调度器做铺垫，由远及近的方式简要介绍了多进程、多线程、协程、并发和并行有关的“史料”，希望你了解为什么Go采用了goroutine，又为何调度器如此重要。



如果你等不急了，想了解Go调度器相关的原理，看下这些文章：

- 设计方案：https://golang.org/s/go11sched
- 代码中关于调度器的描述：https://golang.org/src/runtime/proc.go
- 引用最多的调度器文章：https://morsmachine.dk/go-scheduler
- kavya的PPT，目前看到的讲调度最好的PPT：https://speakerdeck.com/kavya719/the-scheduler-saga
- work stealing论文：http://supertech.csail.mit.edu/papers/steal.pdf
- 分析调度器的论文（就问你6不6，还有论文研究）：http://www.cs.columbia.edu/~aho/cs6998/reports/12-12-11_DeshpandeSponslerWeiss_GO.pdf



**声明**：关于老调度器的资料已经完全搜不到，根据新版调度器设计方案的描述，想象着写了老调度器这一章，可能存在错误。

### 参考资料

1. https://en.wikipedia.org/wiki/Computer#History
2. https://en.wikipedia.org/wiki/Process_(computing)#History
3. https://en.wikipedia.org/wiki/Thread_(computing)#History
4. https://golang.org/doc/faq#goroutines
5. https://golang.org/s/go11sched
6. https://golang.org/src/runtime/proc.go

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/03/10/golang-scheduler-1-history](http://lessisbetter.site/2019/03/10/golang-scheduler-1-history)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="https://lessisbetter.site/images/2019-01-article_qrcode.jpg" style="border:0"  align=center />