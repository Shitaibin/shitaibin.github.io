---
title: Golang的sync.WaitGroup陷阱
date: 2018-10-29 14:27:06
tags: ["Go"]
---

`sync.WaitGroup`是并发环境中，一个相当常用的数据结构，用来等待所有协程的结束，在写代码的时候都是按着例子的样子写的，也没用深究过它的使用。前几日想着能不能在协程中执行`Add()`函数，答案是不能，这里介绍下。

陷阱在WaitGroup的3个函数的调用顺序上。先回顾下3个函数的功能：

1. `Add(delta int)`：给计数器增加delta，比如启动1个协程就增加1。
2. `Done()`：协程退出前执行，把计数器减1。
3. `Wait()`：阻塞等待计数器为0。

<!--more-->

# 考一考

下面的程序是创建了协程father，然后father协程创建了10个子协程，main函数等待所有协程结束后退出，看看下面代码有没有什么问题？

```go
package main

import (
	"fmt"
	"sync"
)

func father(wg *sync.WaitGroup) {
	wg.Add(1)
	defer wg.Done()

	fmt.Printf("father\n")
	for i := 0; i < 10; i++ {
		go child(wg, i)
	}
}

func child(wg *sync.WaitGroup, id int) {
	wg.Add(1)
	defer wg.Done()

	fmt.Printf("child [%d]\n", id)
}

func main() {
	var wg sync.WaitGroup
	go father(&wg)

	wg.Wait()
	log.Printf("main: father and all chindren exit")
}
```

发现问题了吗？如果没有看下面的运行结果：main函数在子协程结束前就开始结束了。

```bash
father
main: father and all chindren exit
child [9]
child [0]
child [4]
child [7]
child [8]
```

# 陷阱分析

产生以上问题的原因在于，创建协程后在协程内才执行`Add()`函数，而此时`Wait()`函数**可能**已经在执行，甚至`Wait()`函数在所有`Add()`执行前就执行了，`Wait()`执行时立马就满足了WaitGroup的计数器为0，Wait结束，主程序退出，导致所有子协程还没完全退出，main函数就结束了。



# 正确的做法

**Add函数一定要在Wait函数执行前执行**，这在Add函数的[文档](https://golang.org/src/sync/waitgroup.go?s=2022:2057#L43)中就提示了: *Note that calls with a positive delta that occur when the counter is zero must happen before a Wait.*。

如何确保Add函数一定在Wait函数前执行呢？在协程情况下，我们不能预知协程中代码执行的时间是否早于Wait函数的执行时间，但是，我们可以在分配协程前就执行Add函数，然后再执行Wait函数，以此确保。

下面是修改后的程序，以及输出结果。

```go
package main

import (
	"fmt"
	"sync"
)

func father(wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Printf("father\n")
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go child(wg, i)
	}
}

func child(wg *sync.WaitGroup, id int) {
	defer wg.Done()
	fmt.Printf("child [%d]\n", id)
}

func main() {
	var wg sync.WaitGroup
	wg.Add(1)
	go father(&wg)

	wg.Wait()
	fmt.Println("main: father and all chindren exit")
}
```



```bash
father
child [9]
child [7]
child [8]
child [1]
child [4]
child [5]
child [2]
child [6]
child [0]
child [3]
main: father and all chindren exit
```

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/10/29/Golang-trap-of-waitgroup/](http://lessisbetter.site/2018/10/29/Golang-trap-of-waitgroup/)