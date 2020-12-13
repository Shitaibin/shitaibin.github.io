---
title: Golang defer的陷阱
date: 2018-11-10 20:23:37
tags: ['Go']
---

你是不是觉得defer很简单、很好用，但也许你掉坑里了都不知道！

这篇文章不介绍defer的常用功能，而是介绍你在用defer时，也许会踩的坑。

defer允许我们进行一些函数执行完成后的收尾工作，并且代码更加简洁，例如： 

1. 关闭文件流： 

   ```go
   // open a file
   defer file.Close()
   ```

<!--more-->

2. 解锁一个加锁的资源 

   ```go
   mu.Lock()
   defer mu.Unlock()
   ```

3. 打印最终报告 

   ```go
   printHeader()
   defer printFooter()
   ```

4. 关闭数据库链接 

   ```go
   // open a database connection
   defer disconnectFromDB() 
   ```

但是：

- 你知道defer和defer后的函数什么时候执行吗？
- 你知道defer后函数里的变量值是什么时候计算的吗？


我曾经在[Stack Overflow](https://stackoverflow.com/questions/52718143/is-golang-defer-statement-execute-before-or-after-return-statement/53219947#53219947)讨论过这个问题，有兴趣的可以看下，本打算在周末写个文章分享给大家defer的坑，今天不小心浏览到一个[**有误解的文章**](# 误解文章截图)，决定现在就写下来，希望大家不要踩坑。



# defer陷阱测试

如果下面这段代码的结果你都知道，恭喜你，你已经了解defer的执行原理，没有必要再看这篇文章了。

```go
func test1() (x int) {
	defer fmt.Printf("in defer: x = %d\n", x)
	x = 7
	return 9
}

func test2() (x int) {
	x = 7
	defer fmt.Printf("in defer: x = %d\n", x)
	return 9
}

func test3() (x int) {
	defer func() {
		fmt.Printf("in defer: x = %d\n", x)
	}()

	x = 7
	return 9
}

func test4() (x int) {
	defer func(n int) {
		fmt.Printf("in defer x as parameter: x = %d\n", n)
		fmt.Printf("in defer x after return: x = %d\n", x)
	}(x)

	x = 7
	return 9
}

func main() {
	fmt.Println("test1")
	fmt.Printf("in main: x = %d\n", test1())
	fmt.Println("test2")
	fmt.Printf("in main: x = %d\n", test2())
	fmt.Println("test3")
	fmt.Printf("in main: x = %d\n", test3())
	fmt.Println("test4")
	fmt.Printf("in main: x = %d\n", test4())
}
```

你已经计算出结果了吗？看看和运行结果是不是一样的，如果不一样继续阅读本文吧：

```log
test1
in defer: x = 0
in main: x = 9
test2
in defer: x = 7
in main: x = 9
test3
in defer: x = 9
in main: x = 9
test4
in defer x as parameter: x = 0
in defer x after return: x = 9
in main: x = 9
```

# defer执行原理

要想知道为何是这个结果，就得先回答前面的2个问题：

1. defer和defer后的函数什么时候执行吗？
2. defer后函数里的变量值是什么时候计算的吗？

依次来回答，这2个问题。



问题1：**defer在defer语句处执行，defer的执行结果是把defer后的函数压入到栈，等待return或者函数panic后，再按先进后出的顺序执行被defer的函数。**

问题2：**defer的函数的参数是在执行defer时计算的，defer的函数中的变量的值是在函数执行时计算的。**



defer及defer函数的执行顺序分2步：

1. 执行defer，计算函数的入参的值，并传递给函数，但不执行函数，而是将函数压入栈。
2. 函数return语句后，或panic后，执行压入栈的函数，函数中变量的值，此时会被计算。



# defer测试解析

这4个测试函数中，都是`return 9`并且没有对返回值进行修改，所以main中都是`in main: x = 9`，我相信这个大家应该是没有疑问的。接下来看每个测试函数defer的打印。

**test1**：defer执行时，对`Printf`的入参x进行计算，它的值是0，并且传递给函数，`return 9`后执行`Printf`，所以结果是`in defer: x = 0`。

**test2**：与test1类似，不同仅是，defer执行是在`x=7`之后，所以x的值是7，并且传递给`Printf`，所以结果是：`in defer: x = 7`。

**test3**：defer后跟的是一个匿名函数，匿名函数能访问外部函数的变量，这里访问的是test3的x，defer执行时，匿名函数没有入参，所以把`func()()`压入到栈，return语句之后，执行`func()()`，此时匿名函数获得x的值是9，所以结果是`in defer: x = 9`。

**test4**：与test3的不同是，匿名函数有一个入参n，我们把x作为入参打印，还有就是匿名函数访问外部打印x。defer执行时，`x=0`，所以入栈的函数是`func(int)(0)`，return语句之后执行`func(int)(0)`，即`n=0`，x在匿名函数内没有定义，依然访问test4中的x，此时`x=9`，所以结果为：`in defer x as parameter: x = 0, in defer x after return: x = 9`。



# 误解文章截图

最后，看下误解读者文章的截图，看看你能不能发现那篇文章作者的思路问题。

![截图1.png](https://lessisbetter.site/images/2018-12-misleading-defer-1.png
)

![截图2.png](https://lessisbetter.site/images/2018-12-misleading-defer-2.png
)

![截图3.png](https://lessisbetter.site/images/2018-12-misleading-defer-3.png
)


上文的作者的目的想知道defer是在return之前，还是之后执行，所以做了这么个测试，他把上面的代码和修改成下面的代码，发现等效后，就给出了错误结论：defer确实是在return之前调用的。

**等效的能证明，顺序吗？**请各位自行思考吧。

# defer的核心

[Golang对于defer的介绍]((https://golang.org/ref/spec#Defer_statements))很精简，但是把上面提到的问题都说清楚了，我也是读了几遍和其他人交流，才完全理解透，不妨好好读读，最核心的一句：

> Each time a "defer" statement executes, the function value and parameters to the call are [evaluated as usual](https://golang.org/ref/spec#Calls)and saved anew but the actual function is not invoked. 



# 参考资料

- [Defer statements](https://golang.org/ref/spec#Defer_statements)
- [Is golang defer statement execute before or after return statement?](https://stackoverflow.com/questions/52718143/is-golang-defer-statement-execute-before-or-after-return-statement)

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/11/10/Golang-trap-of-defer/](http://lessisbetter.site/2018/11/10/Golang-trap-of-defer/)