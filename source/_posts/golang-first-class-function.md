---
title: First class function in Go
date: 2019-06-09 22:00:26
tags: ['Go']
---


![合照](https://lessisbetter.site/images/2019-06-09-photo.jpeg)

6月2日Go语言中文网在杭州举办了线下的MeetUp活动，这次活动办很成功，感谢站长polaris在杭州举办活动的提议，感谢Seekload的筹备与主持，感谢Aaron提供场地，感谢所有到场者的技术经验分享，没有你们就没有这次精彩的活动。

在活动上，我做了个主题分享，今天把分享整理成文章，分享给学习Go语言的各位朋友。

参加本次活动的朋友，大多是刚接触Go，少数几个朋友把玩Go 2~3年了，所以我把主题定位到能让所有人听懂的主题。另外，大家所处行业各有不同，这就要求专注介绍Go本身的特性，这才是大家通用的地方。

最后选题为First class function in Go，这次没有做中文翻译，避免翻译后有误解。这个特性浅显易懂，但掌握Go语言的思维，才能把它用好。

线下分享后，证明选题选对了，大家都能听懂，所以现在不了解First class function的朋友不用着急，后面我会层层推进的方式介绍，相信你一定能理解，那就进入正文吧。


# First class function in Go

## 概念介绍



![幻灯片04](https://lessisbetter.site/images/2019-06-09-幻灯片04.png)

某个编程语言拥有First class function特性指可以把函数作为变量对待。也就说，函数与变量没有差别，它们是一样的，变量出现的地方都可以替换成函数，并且编译也是可以通过的，没有任何语法问题。

在Go里，变量可以存在于哪些地方？

![幻灯片05](https://lessisbetter.site/images/2019-06-09-幻灯片05.png)

变量可以被声明、定义，可以使用`type`创建变量的类型，可以作为函数的入参和返回值，可以存在`slice`, `array`, `map`等数据结构里，可以被动态的创建。

在Go中，函数也可以被声明、定义，可以使用`type`创建一个函数类型，可以作为其他函数的入参和返回值，可以保存在其他类型的数据结构里，最后，函数是可以被动态创建的。

简要归类一下就是下图的样子，除了上面提到的内容，还有匿名函数和闭包，将按下图顺序介绍每一个小特性。

![幻灯片06](https://lessisbetter.site/images/2019-06-09-幻灯片06.png)

## 定义函数类型

![幻灯片07](https://lessisbetter.site/images/2019-06-09-幻灯片07.png)

使用`type`定义一个函数类型，`type`后是类型名称，本例中是`Operation`，再后面是类型的定义，对于函数而言，被称为signature，即函数签名，这个函数签名表示：Operation类型的函数，它以2个int类型为入参，以1个int为返回值。所有满足该函数签名的函数，都是Operation类型的函数。

![幻灯片08](https://lessisbetter.site/images/2019-06-09-幻灯片08.png)

函数`Add`和`Sub`都符合`Operation`的签名，所以`Add`和`Sub`都是`Operation`类型。

## 声明函数类型的变量和为变量赋值

![幻灯片09](https://lessisbetter.site/images/2019-06-09-幻灯片09.png)

变量`op`是`Operation`类型的，可以把`Add`作为值赋值给变量`op`，执行`op`等价于执行`Add`。

## 高阶函数

高阶函数分为函数作为入参和函数作为返回值2部分。

### 函数作为其他函数入参

![幻灯片10](https://lessisbetter.site/images/2019-06-09-幻灯片10.png)

定义一个`Calculator`结构体，它始终保持计算后的结果。

它有一个方法`Do`，入参为一个`Operation`类型的函数`op`和1个`int`类型的变量a，使用计算器的值`c.v`和`a`作为`op`的入参，进行指定运算，并把结果保存会`c.v`。

`main`中，声明了一个变量`calc`，`calc.v`初始值为0，然后运行了加1和减2的操作，加减法的完成使用的我们之前定义的函数`Add`和`Sub`。操作等价于：

```go
calc.v = Add(calc.v, 1)
calc.v = Sub(calc.v, 2)
```

### 函数作为返回值+动态创建

![幻灯片11](https://lessisbetter.site/images/2019-06-09-幻灯片11.png)

这次，改变`Operation`的定义，修改为接收1个`int`类型的入参，返回1个`int`类型的返回值。

同时修改函数`Add`和`Sub`，它们接收1个`int`类型的入参，返回1个`Operation`类型的函数，这个函数是动态创建出来的。

以`Add`为例介绍，在`Add`里动态创建了一个函数，

```go
func(a int) int {
    return a + b
}
```

该函数实现了在变量a基础上加b的操作，并返回结果，我们把这个函数赋值给**变量`addB`**，把`addB`作为返回值返回。

所以本例实现了以函数作为返回值和动态创建函数。

![幻灯片12](https://lessisbetter.site/images/2019-06-09-幻灯片12.png)

`Operation`，`Add`和`Sub`修改后，`Calculator`也要同步修改，方法`Do`修改为只接收`Operation`类型的函数。

`main`函数里，注意`Do`的入参：`Add(1)`，它实现的效果是，创建了1个函数，该函数接收1个值，然后把这个值+1返回，如果用数学表示就是这样：

```go
// Add(1)
add1(x) = x + 1
```

同理，`Sub(2)`的数学表示如下：

```go
// Sub(2)
sub2(x) = x - 2
```

所以2次`Do`操作等价于：

```go
// calc.Do(Add(1))
calc.v = add1(calc.v)
// calc.Do(Sub(2))
calc.v = sub2(calc.v)
```

## 匿名函数

![幻灯片13](https://lessisbetter.site/images/2019-06-09-幻灯片13.png)

上图左边是普通函数，`func`后为函数名，然后为函数签名。右边只有`func`和函数签名，缺少函数名，右边的情况为匿名函数。

![幻灯片14](https://lessisbetter.site/images/2019-06-09-幻灯片14.png)

以`Add`函数其中定义的函数为例：

```go
func(a int) int {
    return a + b
}
```

这就是1个匿名函数，它没有名字。**`addB`并不是函数的名字，只是1个变量名而已，只不过这个变量名的类型是没有显示定义出来的**。

`Add`通常简写为右边的形式。

## 闭包

![幻灯片15](https://lessisbetter.site/images/2019-06-09-幻灯片15.png)

很多人搞不清什么是匿名函数，什么是闭包，所以这里分开介绍这2个概念。

**闭包指有权访问另一个函数作用域中的变量的函数**。大白话就是，可以创建1个函数，它可以访问其他函数遍历，但不需要传值。

仍然是`Add`函数为例，比如匿名函数里直接使用了变量b，该匿名函数也是闭包函数。

闭包的特性注定了，闭包函数要定义在一个函数里面，定义在一个函数里面又只能是匿名函数。

**那，匿名函数和闭包是不是就等价了？**

**No，一个函数可以是匿名函数，但不是闭包函数，因为闭包有时是有副作用的。**

![幻灯片16](https://lessisbetter.site/images/2019-06-09-幻灯片16.png)

我们想并发的把sl中的值打印出来，结果为何会是右边这样？

因为并发的匿名函数，使用的是`test1`中的`i,v`，即这是闭包函数，所有的goroutine都共享这2个值，并且启动1个goroutine后，这2个值变为下一个位置的值。你运行的结果也许不是9 9 9....，因为这个goroutine的调度有关。

如何才能符合预期的打印？只使用匿名函数进行传值，不使用闭包。

![幻灯片17](https://lessisbetter.site/images/2019-06-09-幻灯片17.png)

# Demo

接下来以一个实际的场景，和3种实现版本看如何用Go的思维去解决问题。

## 场景介绍

![幻灯片19](https://lessisbetter.site/images/2019-06-09-幻灯片19.png)

做Go语言工作，尤其是跟网络打交道的工作，连接管理是逃不开的。我做区块链相关的技术工作，区块链中也有网络管理，所以我就以区块链的网络管理为场景进行介绍，但不涉及具体的技术细节，大家莫慌，只需要理解2个概念就行。

区块链是构建在P2P网络之上，在P2P网络中：

1. 一个节点即可以是服务器也可以是客户端，被称为**Host**，
2. 和本节点连接的所有节点都被称为**Peer**。

**具体的场景是：Host需要保存所有建立连接的Peer，并对这些Peer进行维护：增加和删除Peer，并且提供Peer的查询和向所有Peer广播消息的接口**。

针对这个问题场景，我写了3个版本的Demo，我们依次来介绍，再看的时候，可以思考其中的不同。

## 版本1

![幻灯片20](https://lessisbetter.site/images/2019-06-09-幻灯片20.png)

先看`Peer`定义，`Peer`中保存了`ID`，我们可以通过`ID`来表示全网中所有的节点，`Peer`中还有其他字段，比如网络连接、地址、协议版本等信息，此处已经省略掉。

`Peer`有一个`WriteMsg`的方法，实现向该`Peer`发送消息的功能，例子中使用打印替代。

**Peer的定义在3个版本中都不会发生变化，所以后面就不再展示**。

![幻灯片21](https://lessisbetter.site/images/2019-06-09-幻灯片21.png)

`Host`通过`peers`保存了所有连接的Peer，可以通过`Peer.ID`对Peer进行索引。Peer的管理是并发场景，比如，我们可能同时接收到多个Peer的连接，又同时需要向所有Peer广播消息，需要对`peers`加锁保护。最后，我们省略了`Host`的其他字段。

`NewHost()`用来创建一个`Host`对象，用来代表当前节点。

*友情提醒：`Host`在每一个版本都会不同。*

![幻灯片22](https://lessisbetter.site/images/2019-06-09-幻灯片22.png)

`Host`有4个方法，分别是：

1. `AddPeer`: 增加1个Peer。
2. `RemovePeer`: 删除1个Peer。
3. `GetPeer`: 通过Peer.ID查询1个Peer。
4. `BroadcastMsg`: 向所有Peer发送消息。

每一个方法都需要获取`lock`，然后访问`peers`，如果只读取`peers`则使用读锁。

**第1个版本已经介绍完了，大家可以思考一下版本1的缺点。**

![幻灯片23](https://lessisbetter.site/images/2019-06-09-幻灯片23.png)

第1个版本跟其他语言实现其实没有本质区别，用C++、Java等也能写出上面逻辑的代码，只不过这个是Go语言实现的罢了。

**这个版本是一个communicate by sharing memory的体现**，具体来讲，每个goroutine都是1个实体，它们同时运行，调用`Host`的不同方法来访问`peers`，只有拿到当前`lock`的goroutine才能访问peers，仿佛当前goroutine在同其他goroutine讲：我现在有访问权，你们等一下。本质上就是，通过共享`Host.lock`这块内存，各goroutine进行交流（表明自己拥有访问权）。

## 版本2


![幻灯片24](https://lessisbetter.site/images/2019-06-09-幻灯片24.png)

很多Go老手都听过这句话了，这是Go的“联合创始人”**Rob Pike**某个会议上说的。

**在Go中，推荐使用CSP实现并发，而不是习惯性的使用Lock，使用channel传递数据，达到多goroutine间共享数据的目的，也就是share memory by communicating**。

所以，我们版本2，就使用channel的方式，来实现Peer的管理。

![幻灯片25](https://lessisbetter.site/images/2019-06-09-幻灯片25.png)

在版本1中，`peers`是大家都想访问的，并且Host有4个方法，画到了上面的图中，我们看下怎么用CSP实现。

`peers`需要在单独的goroutine中，其他的4个方法在其他的goroutine中调用，它们之间进行通信。

我对使用CSP有一个好的实践，就是把数据流动画出来，并把要流动的数据标上，然后那些数据流动的线条，就是channel，线条上的数据就是channel要传递的数据，图中也把这些线条和数据标上了。具体的细节，可以识别图片中的二维码，看看这篇老文，还有就是并不是所有的并发场景都适合使用channel，有些用锁更好，这篇文章也有介绍。

![幻灯片26](https://lessisbetter.site/images/2019-06-09-幻灯片26.png)

重新定义Host，增加了4个channel，从上到下分别用于增加Peer、广播消息、删除Peer和停止Host。

![幻灯片27](https://lessisbetter.site/images/2019-06-09-幻灯片27.png)

Host增加了2个方法：

1. `Start()`用于启动1个goroutine运行`loop()`，`loop`保存所有的`peers`。
2. `Stop()`用于关闭Host，让`loop`退出。

![幻灯片28](https://lessisbetter.site/images/2019-06-09-幻灯片28.png)

左边是`loop()`的实现，它从4个channel里接收数据，然后做不同的操作。

右边是`AddPeer`， `RemovePeer`, `BroadcastMsg`的实现。

利用1分钟的事件，左右两边对照着看，理解增加1个Peer的全过程。

这就是版本2的全部实现了，思考一下版本2有什么问题，原因是啥？

![幻灯片29](https://lessisbetter.site/images/2019-06-09-幻灯片29.png)

![幻灯片30](https://lessisbetter.site/images/2019-06-09-幻灯片30.png)

问题就是我们没有实现`GetPeer`这个方法，聪明的你一定在Host的定义就发现了，只有增加、删除和广播消息的channel。

**没能实现`GetPeer`的原因下图中进行了介绍，你有没有解决办法？**

![幻灯片31](https://lessisbetter.site/images/2019-06-09-幻灯片31.png)

![幻灯片32](https://lessisbetter.site/images/2019-06-09-幻灯片32.png)

![幻灯片33](https://lessisbetter.site/images/2019-06-09-幻灯片33.png)

可能会有很多goroutine调用`GetPeer`，我们需要向每一个goroutine发送结果，这就需要每一个goroutine都需要对应的1个接收结果的channel。

所以**我们可以增加1个query channel，channel里传递Peer.ID和接收结果的channel。**

**还有没有其他办法？**我们今天的主题`First class function`还有入场，你有办法用这个特性实现吗？

## 版本3

![幻灯片34](https://lessisbetter.site/images/2019-06-09-幻灯片34.png)

First class function: 函数可以向变量一样使用。那channel里面是不是可以传递函数呢？当然可以。

![幻灯片35](https://lessisbetter.site/images/2019-06-09-幻灯片35.png)

我们可以建立一个channel，用这个channel向`loop`传递操作`peers`的函数，所以函数的入参是`peers map[string]*Peer`，无需返回值，因为函数是在`loop`里面调用的，调用`AddPeer`等函数的goroutine是接收不到返回值的。我们把这个类型的函数定义为`Operation`。

`Host`修改为只有2个channel，`stop`功能如版本2，`opCh`用来传递`Operation`类型的函数。

![幻灯片36](https://lessisbetter.site/images/2019-06-09-幻灯片36.png)

`loop`函数可以简化为左边的形式了，右边是`AddPeer`和`RemovePeer`，以`AddPeer`为例进行介绍，创建了一个匿名函数，向`peers`里增加`p`，然后把函数发送到`opCh`。

![幻灯片37](https://lessisbetter.site/images/2019-06-09-幻灯片37.png)

`BroadcastMsg`与`AddPeer`类似。

![幻灯片38](https://lessisbetter.site/images/2019-06-09-幻灯片38.png)

我们重点看一下`GetPeer`，创建了`retCh`用于接收查询的结果，创建了匿名函数进行查询，并把查询结果发送到`retCh`，然后启动1个goroutine把匿名函数写入到`opCh`，最后等待从`retCh`读取查询结果。

这样就实现了向每个调用`GetPeer`的goroutine发送查询结果。

# 总结

![幻灯片40](https://lessisbetter.site/images/2019-06-09-幻灯片40.png)

总结都在上面了，不多说了。

**友情提醒：这3种方式本身并无优劣之分，具体要用那种实现，要依赖自身的实际场景进行取舍。**

# 源码

识别下图二维码。

![幻灯片41](https://lessisbetter.site/images/2019-06-09-幻灯片41.png)

## PPT下载

下载链接：https://lessisbetter.site/images/Go%E8%AF%AD%E8%A8%80%E6%80%9D%E7%BB%B4First-class-function.pdf

或**阅读原文**下载。

# 云象介绍

广告时间，云象区块链持续招人，欢迎来撩。

![幻灯片42](https://lessisbetter.site/images/2019-06-09-幻灯片42.png)

# 活动总结

最后奉上Seekload关于本次活动的总结：[Gopher杭州线下面基第一期](<https://mp.weixin.qq.com/s/wfDW4cKjzuEE1K94anuImA>)。

