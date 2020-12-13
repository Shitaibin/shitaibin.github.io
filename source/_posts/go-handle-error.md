---
title: 如何优雅的处理Golang错误
date: 2018-10-24 14:38:41
tags: ['Go']
---


在看《Go入门指南》的[一种用闭包处理错误的模式](https://www.kancloud.cn/kancloud/the-way-to-go/81402)时，里面提到了一种错误的优雅处理方式，减少我们重复写`if err:=f(); err !=  nil{}`式的代码，感觉很心动，做了下测试，结论如下：
1. 能减少`if err`式的代码，代码可以变清新整洁。
1. 使用存在限制：只有当错误需要结束调用时才可以使用这种方法，如果被调用函数返回错误，但调用者函数需处理错误后，向下继续执行，则不能采用这种方法。



<!--more-->

# 经常的写法

我们在设计函数时，错误处理要遵循以下2个规则：
1. 被调用函数如果有错误，需要传递给调用者，一定要返回
1. 调用者收到返回的错误，一定不可忽视，忽视就是埋bug。如果调用者不处理，被调函数就需要设计成无错误返回。

我们都有这种感受，一个函数需要调用许多函数，然后处理他们的错误，光`if err`就写了一堆，比如下面的`test()`函数。

```go
package main

import (
	"errors"
	"log"
)

func main() {
	test()
}

func test() {
	if err := a(); err != nil {
		log.Println(err)
	}

	if err := b(); err != nil {
		log.Println(err)
	}

	if _, err := c(1, 0); err != nil {
		log.Println(err)
	}

	if _, err := d(1, 0); err != nil {
		log.Println(err)
	}
}

func a() error {
	return errors.New("error in a")
}

func b() error {
	return errors.New("error in b")
}

func c(x, y int) (int, error) {
	return x + y, errors.New("error in c")
}

func d(x, y int) (int, error) {
	if y == 0 {
		return 0, errors.New("error in d, divided by 0")
	}
	return x / y, nil
}
```

测试输出：
```sh
2018/10/24 14:42:40 error in a
2018/10/24 14:42:40 error in b
2018/10/24 14:42:40 error in c
2018/10/24 14:42:40 error in d, divided by 0
```

# 优雅的方式
借用2个小工具：
1. check函数，把错误转化为panic
2. 函数在defer中增加错误处理，从panic中恢复错误，并打印

我们对`test()`函数进行小小的改造。
```go
package main

import (
	"errors"
	"fmt"
)

func main() {
	test()
}

func test() {
	defer func() {
		if r := recover(); r != nil {
			log.Println("got error: ", r)
		}
	}()

	var err error
	err = a()
	check(err)

	err = b()
	check(err)

	_, err = c(1, 2)
	check(err)

	_, err = d(1, 0)
	check(err)
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}

func a() error {
	return errors.New("error in a")
}

func b() error {
	return errors.New("error in b")
}

func c(x, y int) (int, error) {
	return x + y, errors.New("error in c")
}

func d(x, y int) (int, error) {
	if y == 0 {
		return 0, errors.New("error in d, divided by 0")
	}
	return x / y, nil
}
```

输出结果：
```
2018/10/24 17:29:35 got error:  error in a
```

`test()`函数是清爽了不少，也不用一直if然后处理err了，但是这种处理把错误转化为panic，导致`test()`后续的代码无法再继续执行，`b(), c(), d()`几个函数就没法执行了。

所以如果`test()`函数，遇到错误后就返回，就很适合这种优雅的方式。

# 还可以更优雅吗

`test()`函数中的defer看着挺碍眼的，我们还能让`test()`更简洁点吗，代码再优雅点？

采用文章中介绍的办法，增加`errorHandler()`函数，实现对被调用函数的封装，为它增加defer函数，恢复panic报的错误，看代码。

```go
package main

import (
	"errors"
	"log"
)

func main() {
	errorHandler(test)()
}

func test() {
	var err error
	err = a()
	check(err)

	err = b()
	check(err)

	_, err = c(1, 2)
	check(err)

	_, err = d(1, 0)
	check(err)
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}

// 封装f：为传入的函数增加defer
func errorHandler(f func()) func() {
	return func() {
		defer func() {
			if r := recover(); r != nil {
				log.Println("got error: ", r)
			}
		}()

		f()
	}
}

func a() error {
	return errors.New("error in a")
}

func b() error {
	return errors.New("error in b")
}

func c(x, y int) (int, error) {
	return x + y, errors.New("error in c")
}

func d(x, y int) (int, error) {
	if y == 0 {
		return 0, errors.New("error in d, divided by 0")
	}
	return x / y, nil
}
```

结果：
```sh
2018/10/24 17:36:41 got error:  error in a
```

# 还能再一次优雅吗

`errorHandler()`函数不够通用，它只接受无入参，无返回的函数。

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/10/24/go-handle-error/](http://lessisbetter.site/2018/10/24/go-handle-error/)