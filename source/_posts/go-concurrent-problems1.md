---
title: Go面试题：并发
date: 2019-05-03 09:23:17
tags: ['Go']
---

### Once

这个once的实现有没有什么问题？

```go
type Once struct {
	m    sync.Mutex
	done uint32
}

func (o *Once) Do(f func()) {
	if o.done == 1 {
		return
	}

	o.m.Lock()
	defer o.m.Unlock()
	if o.done == 0 {
		o.done = 1
		f()
	}
}
```

有。讨论见这里：https://github.com/smallnest/gitalk/issues/101#issuecomment-490738912

正确的姿势是使用原子操作，原子操作在修改变量的值后，会也让其他核立马看到数据的变动。Once.Do的官方实现就使用的原子操作：

```go
func (o *Once) Do(f func()) {
	if atomic.LoadUint32(&o.done) == 1 {
		return
	}
	// Slow-path.
	o.m.Lock()
	defer o.m.Unlock()
	if o.done == 0 {
		defer atomic.StoreUint32(&o.done, 1)
		f()
	}
}
```

关于缓存，可以看鸟窝的[《cacheline 对 Go 程序的影响》](https://colobu.com/2019/01/24/cacheline-affects-performance-in-go/)和知乎[《细说Cache-L1/L2/L3/TLB》](https://zhuanlan.zhihu.com/p/31875174)。

### Wait Group

```go
package main

import (
	"sync"
	"time"
)

func main() {
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		time.Sleep(time.Millisecond)
		wg.Done()
		wg.Add(1)
	}()
	wg.Wait()
}
```

会panic：

```
panic: sync: WaitGroup is reused before previous Wait has returned

goroutine 1 [running]:
sync.(*WaitGroup).Wait(0xc000018090)
	/Users/shitaibin/go/src/github.com/golang/go/src/sync/waitgroup.go:132 +0xae
main.main()
	/Users/shitaibin/Workspace/golang_step_by_step/problems/concurrent/waitgroup0.go:16 +0x79
exit status 2
```

原因：第13行执行`wg.Done()`后，wg的计数已经变成了0，`wg.Wait()`实际以及完成并返回，14行再次使用此`wg.Add()`报错。

### Mutex

```go
package main

import (
	"fmt"
	"sync"
)

type MyMutex struct {
	count int
	sync.Mutex
}

func main() {
	var mu MyMutex
	mu.Lock()
	var mu2 = mu
	mu.count++
	mu.Unlock()
	mu2.Lock()
	mu2.count++
	mu2.Unlock()
	fmt.Println(mu.count, mu2.count)
}
```

结果panic：

```
fatal error: all goroutines are asleep - deadlock!

goroutine 1 [semacquire]:
sync.runtime_SemacquireMutex(0xc0000180ac, 0x100ae00)
	/Users/shitaibin/go/src/github.com/golang/go/src/runtime/sema.go:71 +0x3d
sync.(*Mutex).Lock(0xc0000180a8)
	/Users/shitaibin/go/src/github.com/golang/go/src/sync/mutex.go:134 +0x109
main.main()
	/Users/shitaibin/Workspace/golang_step_by_step/problems/concurrent/mutex0.go:19 +0xb4
```

原因：`MyMutex`和`sync.Mutex`都是结构体，不包含指针，第16行根据mu新建了mu2对象，2者占用不同的内存区域，但2者的“内容”是相同的，所以mu2新建后就已经是Lock状态。第19行`mu2.Lock()`所以会死锁。

修改：

```go
gopackage main

import (
	"fmt"
	"sync"
)

type MyMutex struct {
	count int
	sync.Mutex
}

func main() {
	var mu MyMutex
	mu.Lock()
	var mu2 = mu
	mu.count++
	mu.Unlock()
	mu2.Unlock() // 先解锁，或新建mu2时移动到mu.Lock之前
	mu2.Lock()
	mu2.count++
	mu2.Unlock()
	fmt.Println(mu.count, mu2.count)
}
```


### Pool

```go
package main

import (
	"bytes"
	"fmt"
	"runtime"
	"sync"
	"time"
)

var pool = sync.Pool{New: func() interface{} { return new(bytes.Buffer) }}

func main() {
	go func() {
		for {
			processRequest(1 << 28) // 256MiB
		}
	}()
	for i := 0; i < 1000; i++ {
		go func() {
			for {
				processRequest(1 << 10) // 1KiB
			}
		}()
	}
	var stats runtime.MemStats
	for i := 0; ; i++ {
		runtime.ReadMemStats(&stats)
		fmt.Printf("Cycle %d: %d MB\n", i, stats.Alloc/1024/1024)
		time.Sleep(time.Second)
		runtime.GC()
	}
}
func processRequest(size int) {
	b := pool.Get().(*bytes.Buffer)
	time.Sleep(500 * time.Millisecond)
	b.Grow(size)
	pool.Put(b)
	time.Sleep(1 * time.Millisecond)
}
```


可以编译，运行时内存先暴涨，但是过一会会回收掉。结果：

```
Cycle 0: 0 MB
Cycle 1: 256 MB
Cycle 2: 513 MB
Cycle 3: 769 MB
Cycle 4: 1281 MB
Cycle 5: 1281 MB
Cycle 6: 1281 MB
Cycle 7: 1537 MB
Cycle 8: 1793 MB
Cycle 9: 2049 MB
Cycle 10: 2049 MB
......
Cycle 107: 14593 MB
Cycle 108: 15105 MB
Cycle 109: 2304 MB
Cycle 110: 0 MB
Cycle 111: 256 MB
Cycle 112: 513 MB
......
```

`sync.Pool`用来存放经常使用的临时对象，如果每次这些内存被GC回收，会加大GC的压力，Pool的出现就是为**减缓**GC的压力，而不是完全不让GC回收Pool的内存。

关于Pool不可错过Dave在[高性能Go程序的这段介绍](https://dave.cheney.net/high-performance-go-workshop/gopherchina-2019.html#using_sync_pool)。

### channel 1

```go
package main

import (
	"fmt"
	"runtime"
	"time"
)

func main() {
	var ch chan int
	// g1
	go func() {
		ch = make(chan int, 1)
		ch <- 1
	}()
	//g2
	go func(ch chan int) {
		time.Sleep(time.Second)
		<-ch
	}(ch)
	c := time.Tick(1 * time.Second)
	for range c {
		fmt.Printf("#goroutines: %d\n", runtime.NumGoroutine())
	}
}
```

结果是持续打印`#goroutines: 2`。`ch`声明后为`nil`，在g1中被初始化为缓冲区大小为1的通道，g1向ch写数据后退出；通过参数把ch传递给g2时，ch还是`nil`，所以在g2内部ch为nil，从nil的通道读数据会阻塞，所以g2无法退出；另外Main协程不会退出，会持续遍历通道`c`，感谢[Bububuger](https://github.com/Bububuger)提醒，定时器的通道并不统计在`NumGoroutine`中，所以会打印存在2个goroutine。

### channel 2


```go
package main

import "fmt"

func main() {
	var ch chan int
	var count int
	go func() {
		ch <- 1
	}()
	go func() {
		count++
		close(ch)
	}()
	<-ch
	fmt.Println(count)
}
```

ch只声明，未进行初始化，所以panic：

```
panic: close of nil channel

goroutine 34 [running]:
main.main.func2(0xc000096000, 0x0)
	/Users/shitaibin/Workspace/golang_step_by_step/problems/concurrent/channel1.go:13 +0x33
created by main.main
	/Users/shitaibin/Workspace/golang_step_by_step/problems/concurrent/channel1.go:11 +0x87
exit status 2
```

修改为下面这样，还有问题吗？：

```go
package main

import "fmt"

func main() {
	// var ch chan int
	ch := make(chan int)
	var count int
	go func() {
		ch <- 1
	}()
	go func() {
		count++
		close(ch)
	}()
	<-ch
	fmt.Println(count)
}
```

同样会panic，典型的channel由非发送者关闭，造成在关闭的channel上写数据。

```
1
panic: send on closed channel

goroutine 4 [running]:
main.main.func1(0xc000070060)
	/Users/shitaibin/Workspace/golang_step_by_step/problems/concurrent/channel1.go:10 +0x37
created by main.main
	/Users/shitaibin/Workspace/golang_step_by_step/problems/concurrent/channel1.go:9 +0x80
exit status 2
```

### Map 1

```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var m sync.Map
	m.LoadOrStore("a", 1)
	m.Delete("a")
	fmt.Println(m.Len())
}
```

无法编译，因为Map没有Len()方法。

### Map 2

```go
package main

import "sync"

type Map struct {
	m map[int]int
	sync.Mutex
}

func (m *Map) Get(key int) (int, bool) {
	m.Lock()
	defer m.Unlock()
	i, ok := m.m[key]
	return i, ok
}

func (m *Map) Put(key, value int) {
	m.Lock()
	defer m.Unlock()
	m.m[key] = value
}

func (m *Map) Len() int {
	return len(m.m)
}

func main() {
	var wg sync.WaitGroup
	wg.Add(2)
	m := Map{m: make(map[int]int)}
	go func() {
		for i := 0; i < 10000000; i++ {
			m.Put(i, i)
		}
		wg.Done()
	}()
	go func() {
		for i := 0; i < 10000000; i++ {
			m.Len()
		}
		wg.Done()
	}()
	wg.Wait()
}
```

能正常编译和运行。map不是协程安全的，需要锁的保护，但Len()的实现并没有加锁，当map写数据时，并且调用Len读长度，则存在map的并发读写问题，因为不是同时读写map所存的内容，所以可以编译和运行，但存在读取的map内存长度不准确问题。map定义和len的声明如下：


```go
// A header for a Go map.
type hmap struct {
	// Note: the format of the hmap is also encoded in cmd/compile/internal/gc/reflect.go.
	// Make sure this stays in sync with the compiler's definition.
	count     int // # live cells == size of map.  Must be first (used by len() builtin)
	flags     uint8
	B         uint8  // log_2 of # of buckets (can hold up to loadFactor * 2^B items)
	noverflow uint16 // approximate number of overflow buckets; see incrnoverflow for details
	hash0     uint32 // hash seed

	buckets    unsafe.Pointer // array of 2^B Buckets. may be nil if count==0.
	oldbuckets unsafe.Pointer // previous bucket array of half the size, non-nil only when growing
	nevacuate  uintptr        // progress counter for evacuation (buckets less than this have been evacuated)

	extra *mapextra // optional fields
}

// The len built-in function returns the length of v, according to its type:
//	Array: the number of elements in v.
//	Pointer to array: the number of elements in *v (even if v is nil).
//	Slice, or map: the number of elements in v; if v is nil, len(v) is zero.
//	String: the number of bytes in v.
//	Channel: the number of elements queued (unread) in the channel buffer;
//	if v is nil, len(v) is zero.
// For some arguments, such as a string literal or a simple array expression, the
// result can be a constant. See the Go language specification's "Length and
// capacity" section for details.
func len(v Type) int
```

### slice

```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var wg sync.WaitGroup
	wg.Add(2)
	var ints = make([]int, 0, 1000)
	go func() {
		for i := 0; i < 1000; i++ {
			ints = append(ints, i)
		}
		wg.Done()
	}()
	go func() {
		for i := 0; i < 1000; i++ {
			ints = append(ints, i)
		}
		wg.Done()
	}()
	wg.Wait()
	fmt.Println(len(ints))
}
```

首先，slice不是协程安全的，自身也又没锁的保护，多协程访问存在并发问题：

```go
type slice struct {
	array unsafe.Pointer
	len   int
	cap   int
}
```

其次，append中有可能还会分配新的内存空间，切片可能指向了新的内存区域：

```go
// The append built-in function appends elements to the end of a slice. If
// it has sufficient capacity, the destination is resliced to accommodate the
// new elements. If it does not, a new underlying array will be allocated.
// Append returns the updated slice. It is therefore necessary to store the
// result of append, often in the variable holding the slice itself:
//	slice = append(slice, elem1, elem2)
//	slice = append(slice, anotherSlice...)
// As a special case, it is legal to append a string to a byte slice, like this:
//	slice = append([]byte("hello "), "world"...)
func append(slice []Type, elems ...Type) []Type
```

所以，两个协程同时写，是不安全的，并且大概率可能存在数据丢失，所以结果可能不是2000。


### 源码

[golang_step_by_step](https://github.com/Shitaibin/golang_step_by_step/tree/master/problems)


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/05/03/go-concurrent-problems1/](http://lessisbetter.site/2019/05/03/go-concurrent-problems1/)

<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="http://img.lessisbetter.site/2019-01-article_qrcode.jpg" style="border:0"  align=center />