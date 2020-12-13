---
title: Go调度器系列（4）源码阅读与探索
date: 2019-04-14 15:38:59
tags: ['Go']
---


各位朋友，这次想跟大家分享一下Go调度器源码阅读相关的知识和经验，网络上已经有很多剖析源码的好文章，所以这篇文章**不是又一篇源码剖析文章，注重的不是源码分析分享，而是带给大家一些学习经验，希望大家能更好的阅读和掌握Go调度器的实现**。

本文主要分2个部分：

1. **解决如何阅读源码的问题**。阅读源码本质是把脑海里已经有的调度设计，看看到底是不是这么实现的，是怎么实现的。
2. **带给你一个探索Go调度器实现的办法**。源码都到手了，你可以修改、**窥探**，通过这种方式解决阅读源码过程中的疑问，验证一些想法。比如：负责调度的是g0，怎么才能`schedule()`在执行时，当前是g0呢？



## 如何阅读源码

### 阅读前提

阅读Go源码前，最好已经掌握Go调度器的设计和原理，如果你还无法回答以下问题：
1. 为什么需要Go调度器？
1. Go调度器与系统调度器有什么区别和关系/联系？
1. G、P、M是什么，三者的关系是什么？
1. P有默认几个？
1. M同时能绑定几个P？
1. M怎么获得G？
1. M没有G怎么办？
1. 为什么需要全局G队列？
1. Go调度器中的负载均衡的2种方式是什么？
1. work stealing是什么？什么原理？
1. 系统调用对G、P、M有什么影响？
1. Go调度器抢占是什么样的？一定能抢占成功吗？

建议阅读Go调度器系列文章，以及文章中的参考资料：
1. [Go调度器系列（1）起源](http://lessisbetter.site/2019/03/10/golang-scheduler-1-history/)
1. [Go调度器系列（2）宏观看调度器](http://lessisbetter.site/2019/03/26/golang-scheduler-2-macro-view/)
1. [Go调度器系列（3）图解调度原理](http://lessisbetter.site/2019/04/04/golang-scheduler-3-principle-with-graph/)



### 优秀源码资料推荐

既然你已经能回答以上问题，说明你对Go调度器的设计已经有了一定的掌握，关于Go调度器源码的优秀资料已经有很多，我这里推荐2个：

1. **雨痕的Go源码剖析**六章并发调度，不止是源码，是以源码为基础进行了详细的Go调度器介绍：https://github.com/qyuhen/book
2. **Go夜读**第12期，golang中goroutine的调度，M、P、G各自的一生状态，以及转换关系：https://reading.developerlearning.cn/reading/12-2018-08-02-goroutine-gpm/


Go调度器的源码还涉及GC等，阅读源码时，可以暂时先跳过，主抓调度的逻辑。

另外，Go调度器涉及汇编，也许你不懂汇编，不用担心，雨痕的文章对汇编部分有进行解释。

最后，送大家一幅流程图，画出了主要的调度流程，大家也可边阅读边画，增加理解，**高清版可到博客下载（原图原文跳转）**。

![](http://img.lessisbetter.site/2019-04-shcedule-flow.png)


## 如何探索调度器

这部分教你探索Go调度器的源码，验证想法，主要思想就是，下载Go的源码，添加调试打印，编译修改的源文件，生成修改的go，然后使用修改go运行测试代码，观察结果。


### 下载和编译Go

1. Github下载，并且换到go1.11.2分支，本文所有代码修改都基于go1.11.2版本。
```bash
$ GODIR=$GOPATH/src/github.com/golang/go
$ mkdir -p $GODIR
$ cd $GODIR/..
$ git clone https://github.com/golang/go.git
$ cd go
$ git fetch origin go1.11.2
$ git checkout origin/go1.11.2
$ git checkout -b go1.11.2
$ git checkout go1.11.2
```

2. 初次编译，会跑测试，耗时长一点
```bash
$ cd $GODIR/src
$ ./all.bash
```

3. 以后每次修改go源码后可以这样，4分钟左右可以编译完成
```bash
$ cd  $GODIR/src
$ time ./make.bash
Building Go cmd/dist using /usr/local/go.
Building Go toolchain1 using /usr/local/go.
Building Go bootstrap cmd/go (go_bootstrap) using Go toolchain1.
Building Go toolchain2 using go_bootstrap and Go toolchain1.
Building Go toolchain3 using go_bootstrap and Go toolchain2.
Building packages and commands for linux/amd64.
---
Installed Go for linux/amd64 in /home/xxx/go/src/github.com/golang/go
Installed commands in /home/xxx/go/src/github.com/golang/go/bin

real	1m11.675s
user	4m4.464s
sys	0m18.312s
```
编译好的go和gofmt在`$GODIR/bin`目录。
```bash
$ ll $GODIR/bin
total 16044
-rwxrwxr-x 1 vnt vnt 13049123 Apr 14 10:53 go
-rwxrwxr-x 1 vnt vnt  3377614 Apr 14 10:53 gofmt
```

4. 为了防止我们修改的go和过去安装的go冲突，创建igo软连接，指向修改的go。
```bash
$ mkdir -p ~/testgo/bin
$ cd ~/testgo/bin
$ ln -sf $GODIR/bin/go igo
```

5. 最后，把`~/testgo/bin`加入到`PATH`，就能使用`igo`来编译代码了，运行下igo，应当获得go1.11.2的版本：
```bash
$ igo version
go version go1.11.2 linux/amd64
```

当前，已经掌握编译和使用修改的go的办法，接下来就以1个简单的例子，教大家如何验证想法。

### 验证schedule()由g0执行

阅读源码的文章，你已经知道了g0是负责调度的，并且g0是全局变量，可在runtime包的任何地方直接使用，看到`schedule()`代码如下（所在文件：`$GODIR/src/runtime/proc.go`）：


```go
// One round of scheduler: find a runnable goroutine and execute it.
// Never returns.
func schedule() {
	// 获取当前g，调度时这个g应当是g0
	_g_ := getg()

	if _g_.m.locks != 0 {
		throw("schedule: holding locks")
	}

	// m已经被某个g锁定，先停止当前m，等待g可运行时，再执行g，并且还得到了g所在的p
	if _g_.m.lockedg != 0 {
		stoplockedm()
		execute(_g_.m.lockedg.ptr(), false) // Never returns.
	}

	// 省略...
}
```


**问题**：既然g0是负责调度的，为何`schedule()`每次还都执行`_g_ := getg()`，直接使用g0不行吗？`schedule()`真的是g0执行的吗？

在[《Go调度器系列（2）宏观看调度器》](http://lessisbetter.site/2019/03/26/golang-scheduler-2-macro-view/)这篇文章中我曾介绍了trace的用法，阅读代码时发现**使用`debug.schedtrace`和`print()`函数可以用作打印调试信息**，那我们是不是可以使用这种方法打印我们想获取的信息呢？当然可以。

另外，注意`print()`并不是`fmt.Print()`，也不是C语言的`printf`，所以不是格式化输出，它是汇编实现的，我们不深入去了解它的实现了，现在要掌握它的用法：

```go
// The print built-in function formats its arguments in an
// implementation-specific way and writes the result to standard error.
// Print is useful for bootstrapping and debugging; it is not guaranteed
// to stay in the language.
func print(args ...Type)
```

从上面可以看到，它接受可变长参数，我们使用的时候只需要传进去即可，但要手动控制格式。


我们修改`schedule()`函数，使用`debug.schedtrace > 0`控制打印，加入3行代码，把goid给打印出来，如果始终打印goid为0，则代表调度确实是由g0执行的：

```go
if debug.schedtrace > 0 {
	print("schedule(): goid = ", _g_.goid, "\n") // 会是0吗？是的
}
```

`schedule()`如下：

```go
// One round of scheduler: find a runnable goroutine and execute it.
// Never returns.
func schedule() {
	// 获取当前g，调度时这个g应当是g0
	_g_ := getg()

	if debug.schedtrace > 0 {
		print("schedule(): goid = ", _g_.goid, "\n") // 会是0吗？是的
	}

	if _g_.m.locks != 0 {
		throw("schedule: holding locks")
	}
	// ...
}
```

编译igo：
```
$ cd  $GODIR/src
$ ./make.bash
```

编写一个简单的demo（不能更简单）：

```go
package main

func main() {
}
```

结果如下，你会发现所有的`schedule()`函数调用都打印`goid = 0`，足以证明Go调度器的调度由g0完成（如果你认为还是缺乏说服力，可以写复杂一些的demo）：
```bash
$ GODEBUG=schedtrace=1000 igo run demo1.go
schedule(): goid = 0
schedule(): goid = 0
SCHED 0ms: gomaxprocs=8 idleprocs=6 threads=4 spinningthreads=1 idlethreads=0 runqueue=0 [0 0 0 0 0 0 0 0]
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
schedule(): goid = 0
// 省略几百行
```

**启发比结论更重要，希望各位朋友在学习Go调度器的时候，能多一些自己的探索和研究，而不仅仅停留在看看别人文章之上**。

### 参考资料

1. [Installing Go from source](https://golang.org/doc/install/source)

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/04/14/golang-scheduler-4-explore-source-code/](http://lessisbetter.site/2019/04/14/golang-scheduler-4-explore-source-code/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="http://img.lessisbetter.site/2019-01-article_qrcode.jpg" style="border:0"  align=center />

