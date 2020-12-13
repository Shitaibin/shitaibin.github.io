---
title: 一招教你无阻塞读写Golang channel
date: 2018-11-3 20:19:57
tags: ['Go', 'Channel']
---

无论是无缓冲通道，还是有缓冲通道，都存在阻塞的情况，教你一招再也不遇到channel阻塞的问题。

这篇文章会介绍，哪些情况会存在阻塞，以及如何使用select解决阻塞。



# 阻塞场景

阻塞场景共4个，有缓存和无缓冲各2个。

**无缓冲通道**的特点是，发送的数据需要被读取后，发送才会完成，它阻塞场景：

1. 通道中无数据，但执行读通道。
2. 通道中无数据，向通道写数据，但无协程读取。

<!--more-->

```go
// 场景1
func ReadNoDataFromNoBufCh() {
	noBufCh := make(chan int)

	<-noBufCh
	fmt.Println("read from no buffer channel success")

	// Output:
	// fatal error: all goroutines are asleep - deadlock!
}

// 场景2
func WriteNoBufCh() {
	ch := make(chan int)

	ch <- 1
	fmt.Println("write success no block")
	
	// Output:
	// fatal error: all goroutines are asleep - deadlock!
}
```

*注：示例代码中的Output注释代表函数的执行结果，每一个函数都由于阻塞在通道操作而无法继续向下执行，最后报了死锁错误。*

**有缓存通道**的特点是，有缓存时可以向通道中写入数据后直接返回，缓存中有数据时可以从通道中读到数据直接返回，这时有缓存通道是不会阻塞的，它阻塞的场景是：

1. 通道的缓存无数据，但执行读通道。
2. 通道的缓存已经占满，向通道写数据，但无协程读。

```go
// 场景1
func ReadNoDataFromBufCh() {
	bufCh := make(chan int, 1)

	<-bufCh
	fmt.Println("read from no buffer channel success")

	// Output:
	// fatal error: all goroutines are asleep - deadlock!
}

// 场景2
func WriteBufChButFull() {
	ch := make(chan int, 1)
	// make ch full
	ch <- 100

	ch <- 1
	fmt.Println("write success no block")
	
	// Output:
	// fatal error: all goroutines are asleep - deadlock!
}
```



# 使用Select实现无阻塞读写

[select](https://golang.org/src/reflect/value.go?s=61144:61213#L2015)是执行选择操作的一个结构，它里面有一组case语句，它会执行其中无阻塞的那一个，如果都阻塞了，那就等待其中一个不阻塞，进而继续执行，它有一个default语句，该语句是永远不会阻塞的，我们可以借助它实现无阻塞的操作。

下面示例代码是使用select修改后的无缓冲通道和有缓冲通道的读写，以下函数可以直接通过main函数调用，其中的Ouput的注释是运行结果，从结果能看出，在通道不可读或者不可写的时候，不再阻塞等待，而是直接返回。

```go
// 无缓冲通道读
func ReadNoDataFromNoBufChWithSelect() {
	bufCh := make(chan int)

	if v, err := ReadWithSelect(bufCh); err != nil {
		fmt.Println(err)
	} else {
		fmt.Printf("read: %d\n", v)
	}

	// Output:
	// channel has no data
}

// 有缓冲通道读
func ReadNoDataFromBufChWithSelect() {
	bufCh := make(chan int, 1)

	if v, err := ReadWithSelect(bufCh); err != nil {
		fmt.Println(err)
	} else {
		fmt.Printf("read: %d\n", v)
	}

	// Output:
	// channel has no data
}

// select结构实现通道读
func ReadWithSelect(ch chan int) (x int, err error) {
	select {
	case x = <-ch:
		return x, nil
	default:
		return 0, errors.New("channel has no data")
	}
}

// 无缓冲通道写
func WriteNoBufChWithSelect() {
	ch := make(chan int)
	if err := WriteChWithSelect(ch); err != nil {
		fmt.Println(err)
	} else {
		fmt.Println("write success")
	}

	// Output:
	// channel blocked, can not write
}

// 有缓冲通道写
func WriteBufChButFullWithSelect() {
	ch := make(chan int, 1)
	// make ch full
	ch <- 100
	if err := WriteChWithSelect(ch); err != nil {
		fmt.Println(err)
	} else {
		fmt.Println("write success")
	}

	// Output:
	// channel blocked, can not write
}

// select结构实现通道写
func WriteChWithSelect(ch chan int) error {
	select {
	case ch <- 1:
		return nil
	default:
		return errors.New("channel blocked, can not write")
	}
}
```

# 使用Select+超时改善无阻塞读写

使用default实现的无阻塞通道阻塞有一个**缺陷**：当通道不可读或写的时候，**会即可返回**。实际场景，更多的需求是，我们希望，尝试读一会数据，或者尝试写一会数据，如果实在没法读写，再返回，程序继续做其它的事情。

**使用定时器替代default**可以解决这个问题。比如，我给通道读写数据的容忍时间是500ms，如果依然无法读写，就即刻返回，修改一下会是这样：

```go
func ReadWithSelect(ch chan int) (x int, err error) {
	timeout := time.NewTimer(time.Microsecond * 500)

	select {
	case x = <-ch:
		return x, nil
	case <-timeout.C:
		return 0, errors.New("read time out")
	}
}

func WriteChWithSelect(ch chan int) error {
	timeout := time.NewTimer(time.Microsecond * 500)

	select {
	case ch <- 1:
		return nil
	case <-timeout.C:
		return errors.New("write time out")
	}
}
```

结果就会变成超时返回：

```text
read time out
write time out
read time out
write time out
```

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/11/03/Golang-channel-read-and-write-without-blocking/](http://lessisbetter.site/2018/11/03/Golang-channel-read-and-write-without-blocking/)