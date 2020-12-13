title: Go的map中删除子map，内存会自动释放吗？
date: 2018-09-29 20:06:39
tags: ['Go', 'map']
-----

结论
--------
在Go中，map中存放map，上层map执行delete，子层map占用的内存会释放，无需手动先释放子map内存，再在上层map执行删除。

实验
--------

在C++中，如果使用了map包含map的数据结构，当要释放上层map的某一项时，需要手动释放对应的子map占用的内存，而在Go中，垃圾回收让内存管理变得如此简单。

做2个对比实验，
实验1：普通的map，map保存到是int到int的映射，会执行delete删除map的每一项，执行垃圾回收，看内存是否被回收，map设置为nil，再看是否被回收。
实验2：map套子map，顶层map是int到子map的映射，子map是int到int的映射，同样先执行delete，再设置为nil，分别看垃圾回收情况。

### 实验1
```go
package main

import (
	"log"
	"runtime"
)

var lastTotalFreed uint64
var intMap map[int]int
var cnt = 8192

func main() {
	printMemStats()

	initMap()
	runtime.GC()
	printMemStats()

	log.Println(len(intMap))
	for i := 0; i < cnt; i++ {
		delete(intMap, i)
	}
	log.Println(len(intMap))

	runtime.GC()
	printMemStats()

	intMap = nil
	runtime.GC()
	printMemStats()
}

func initMap() {
	intMap = make(map[int]int, cnt)

	for i := 0; i < cnt; i++ {
		intMap[i] = i
	}
}

func printMemStats() {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	log.Printf("Alloc = %v TotalAlloc = %v  Just Freed = %v Sys = %v NumGC = %v\n",
		m.Alloc/1024, m.TotalAlloc/1024, ((m.TotalAlloc-m.Alloc)-lastTotalFreed)/1024, m.Sys/1024, m.NumGC)

	lastTotalFreed = m.TotalAlloc - m.Alloc
}
```

看结果前，解释下几个字段：
- Alloc：当前堆上对象占用的内存大小。
- TotalAlloc：堆上总共分配出的内存大小。
- Sys：程序从操作系统总共申请的内存大小。
- NumGC：垃圾回收运行的次数。

结果如下：
```
2018/09/29 20:09:25 Alloc = 65 TotalAlloc = 65  Just Freed = 0 Sys = 1700 NumGC = 0
2018/09/29 20:09:25 Alloc = 387 TotalAlloc = 391  Just Freed = 3 Sys = 3076 NumGC = 1
2018/09/29 20:09:25 8192
2018/09/29 20:09:25 0
2018/09/29 20:09:25 Alloc = 387 TotalAlloc = 392  Just Freed = 1 Sys = 3140 NumGC = 2
2018/09/29 20:09:25 Alloc = 74 TotalAlloc = 394  Just Freed = 314 Sys = 3140 NumGC = 3
```

Alloc代表了map占用的内存大小，这个结果表明，执行完delete后，map占用的内存并没有变小，Alloc依然是387，代表map的key和value占用的空间仍在map里.执行完map设置为nil，Alloc变为74，与刚创建的map大小基本是约等于。

### 实验2

```go
package main

import (
	"log"
	"runtime"
)

var intMapMap map[int]map[int]int

var cnt = 1024
var lastTotalFreed uint64 // size of last memory has been freed

func main() {
	// 1
	printMemStats()

	// 2
	initMapMap()
	runtime.GC()
	printMemStats()

	// 3
	fillMapMap()
	runtime.GC()
	printMemStats()

	// 4
	log.Println(len(intMapMap))
	for i := 0; i < cnt; i++ {
		delete(intMapMap, i)
	}
	log.Println(len(intMapMap))
	runtime.GC()
	printMemStats()

	// 5
	intMapMap = nil
	runtime.GC()
	printMemStats()
}

func initMapMap() {
	intMapMap = make(map[int]map[int]int, cnt)
	for i := 0; i < cnt; i++ {
		intMapMap[i] = make(map[int]int, cnt)
	}
}

func fillMapMap() {
	for i := 0; i < cnt; i++ {
		for j := 0; j < cnt; j++ {
			intMapMap[i][j] = j
		}
	}
}

func printMemStats() {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	log.Printf("Alloc = %v TotalAlloc = %v  Just Freed = %v Sys = %v NumGC = %v\n",
		m.Alloc/1024, m.TotalAlloc/1024, ((m.TotalAlloc-m.Alloc)-lastTotalFreed)/1024, m.Sys/1024, m.NumGC)

	lastTotalFreed = m.TotalAlloc - m.Alloc
}
```
结果
```
2018/09/29 20:10:27 Alloc = 64 TotalAlloc = 64  Just Freed = 0 Sys = 1700 NumGC = 0
2018/09/29 20:10:27 Alloc = 41154 TotalAlloc = 41157  Just Freed = 3 Sys = 46026 NumGC = 5
2018/09/29 20:10:27 Alloc = 41241 TotalAlloc = 41293  Just Freed = 48 Sys = 47082 NumGC = 6
2018/09/29 20:10:27 1024
2018/09/29 20:10:27 0
2018/09/29 20:10:27 Alloc = 114 TotalAlloc = 41295  Just Freed = 41128 Sys = 47082 NumGC = 7
2018/09/29 20:10:27 Alloc = 74 TotalAlloc = 41296  Just Freed = 41 Sys = 47082 NumGC = 8
```

这个结果表明，在执行完delete后，顶层map占用的内存从41241降到了114，子层map占用的空间肯定是被GC回收了，不然占用内存不会下降这么显著。但依然比初始化的顶层map占用的内存64多出不少，那是因为delete操作，顶层map的key占用的空间依然在map里，当把顶层map设置为nil时，大小变为74吗，顶层map占用那些空间被释放了.


参考资料 
---------------
- http://blog.cyeam.com/json/2017/11/02/go-map-delete

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/09/29/go-map-delete/](http://lessisbetter.site/2018/09/29/go-map-delete/)