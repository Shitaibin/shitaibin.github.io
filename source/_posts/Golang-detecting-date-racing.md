---
title: 轻松检测Golang并发的数据竞争
date: 2018-11-17 20:27:09
tags: ['Go']
---

Golang中我们使用Channel或者sync.Mutex等锁保护数据，有没有一种机制可以检测代码中的数据竞争呢？



> 背景知识
>
> 数据竞争是并发情况下，存在多线程/协程读写相同数据的情况，必须存在至少一方写。另外，全是读的情况下是不存在数据竞争的。



# 使用race检测数据竞争

`go build`有个标记`race`可以帮助检测代码中的数据竞争。

```bash
➜  awesome git:(master) ✗ go help build
//.... omit
-race
		enable data race detection.
		Supported only on linux/amd64, freebsd/amd64, darwin/amd64 and windows/amd64.
```

<!--more-->

下面举个栗子：

```go
package main

import "fmt"

func main() {
	i := 0

	go func() {
		i++ // write i
	}()

	fmt.Println(i) // read i
}
```



测试方法：

```bash
➜  awesome git:(master) ✗ go build -race hi.go
➜  awesome git:(master) ✗ ./hi
0
==================
WARNING: DATA RACE
Write at 0x00c00009c008 by goroutine 6:
  main.main.func1()
      /Users/mac/go/src/github.com/mac/awesome/hi.go:9 +0x4e

Previous read at 0x00c00009c008 by main goroutine:
  main.main()
      /Users/mac/go/src/github.com/mac/awesome/hi.go:12 +0x88

Goroutine 6 (running) created at:
  main.main()
      /Users/mac/go/src/github.com/mac/awesome/hi.go:8 +0x7a
==================
Found 1 data race(s)
exit status 66
```



提示示例代码存在1处数据竞争，说明了数据会在第9行写，并且同时会在12行读形成了数据竞争。

当然你也可以使用`go run`一步到位：

```bash
➜  awesome git:(master) ✗ go run -race hi.go
0
==================
WARNING: DATA RACE
Write at 0x00c000094008 by goroutine 6:
  main.main.func1()
      /Users/shitaibin/go/src/github.com/shitaibin/awesome/hi.go:9 +0x4e

Previous read at 0x00c000094008 by main goroutine:
  main.main()
      /Users/shitaibin/go/src/github.com/shitaibin/awesome/hi.go:12 +0x88

Goroutine 6 (running) created at:
  main.main()
      /Users/shitaibin/go/src/github.com/shitaibin/awesome/hi.go:8 +0x7a
==================
Found 1 data race(s)
exit status 66
```

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/11/17/Golang-detecting-date-racing/](http://lessisbetter.site/2018/11/17/Golang-detecting-date-racing/)