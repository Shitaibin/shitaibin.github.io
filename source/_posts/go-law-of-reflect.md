---
title: Go高级实践：反射3定律
date: 2019-02-24 18:28:52
tags: ['Go']
---



各位学习Go语言的朋友，周末好，这次跟大家聊一聊Go语言的一个高级话题：反射。

这篇文章是从我过去的学习笔记修改来的，内容主要来自Go Blog的一篇文章《The law of reflection》。

**这篇文章主要介绍反射和接口的关系，解释内在的关系和原理**。

反射来自元编程，指通过类型检查变量本身数据结构的方式，只有部分编程语言支持反射。

## 类型
反射构建在类型系统之上，Go是静态类型语言，每一个变量都有**静态类型**，在编译时就确定下来了。

比如：
```go
type MyInt int

var i int
var j MyInt
```

i和j的**底层类型**都是`int`，但i的静态类型是`int`，j的静态类型是`MyInt`，这两个是不同类型，是不能直接赋值的，需要类型强制转换。

接口类型比较特殊，接口类型的变量被多种对象类型赋值，看起来像动态语言的特性，但变量类型始终是接口类型，Go是静态的。举例：

```go
var r io.Reader
r = os.Stdin
r = bufio.NewReader(r)
r = new(bytes.Buffer)
// and so on
```

虽然r被3种类型的变量赋值，但r的类型始终是`io.Reader`。

> 最特别：空接口`interface{}`的变量可以被任何类型的值赋值，但类型一直都是`interface{}`。

## 接口的表示

Russ Cox（Go语言创始人）在他的[博客详细介绍了Go语言接口](https://research.swtch.com/2009/12/go-data-structures-interfaces.html)，结论是：

接口类型的变量存储的是**一对数据**：
1. 变量实际的值
2. 变量的静态类型

例子：
```go
var r io.Reader
tty, err := os.OpenFile("/dev/tty", os.O_RDWR, 0)
if err != nil {
    return nil, err
}
r = tty
```

r是接口类型变量，保存了**值tty和tty的类型**`*os.File`，所以才能使用**类型断言**判断r保存的值的静态类型：
```go
var w io.Writer
w = r.(io.Writer)
```

虽然r中包含了tty和它的类型，包含了tty的所有函数，但r是接口类型，决定了r只能调用接口`io.Reader`中包含的函数。

记住：**接口变量保存的不是接口类型的值，还是英语说起来更方便：Interfaces do not hold interface values.**


## 反射的3条定律

### 定律1：从接口值到反射对象

反射是一种检测存储在接口变量中值和类型的机制。通过`reflect`包的一些函数，可以把接口转换为反射定义的对象。

掌握`reflect`包的以下函数：
1. `reflect.ValueOf({}interface) reflect.Value`：获取某个变量的值，但值是通过`reflect.Value`对象描述的。
1. `reflect.TypeOf({}interface) reflect.Type`：获取某个变量的静态类型，但值是通过`reflect.Type`对象描述的，是可以直接使用`Println`打印的。
1. `reflect.Value.Kind() Kind`：获取变量值的底层类型（类别），注意不是类型，是Int、Float，还是Struct，还是Slice，[具体见此](https://golang.org/src/reflect/type.go?s=8302:8316#L217)。
1. `reflect.Value.Type() reflect.Type`：获取变量值的类型，效果等同于`reflect.TypeOf`。

再解释下Kind和Type的区别，比如：
```go
type MyInt int
var x MyInt = 7
v := reflect.ValueOf(x)
```

v.Kind()得到的是Int，而Type得到是`MyInt`。


### 定律2：从反射对象到接口值

定律2是定律1的逆向过程，上面我们学了：`普通变量 -> 接口变量 -> 反射对象`的过程，这是从`反射对象 -> 接口变量`的过程，使用的是`Value`的`Interface`函数，是把实际的值赋值给空接口变量，它的声明如下：
```go
func (v Value) Interface() (i interface{})
```

回忆一下：接口变量存储了实际的值和值的类型，`Println`可以根据接口变量实际存储的类型自动识别其值并打印。

注意事项：如果Value是结构体的非导出字段，调用该函数会导致panic。

### 定律3：当反射对象所存的值是可设置时，反射对象才可修改

从定律1入手理解，定律3就不再那么难懂。

Settability is a property of a reflection Value, and not all reflection Values have it.

可设置指的是，可以通过Value设置原始变量的值。

通过函数的例子思考一下可设置：
```go
func f(x int)
```
在调用f的时候，传入了参数x，从函数内部修改x的值，外部的变量的值并不会发生改变，因为这种是传值，是拷贝的传递方式。

```go
func f(p *int)
```
函数f的入参是指针类型，在函数内部的修改变量的值，函数外部变量的值也会跟着变化。

使用反射也是这个原理，如果创建Value时传递的是变量，则Value是不可设置的。如果创建Value时传递的是变量地址，则Value是可设置的。

可以使用`Value.CanSet()`检测是否可以通过此Value修改原始变量的值。

```go
x := 10
v1 := reflect.ValueOf(x)
fmt.Println("setable:", v1.CanSet())
p := reflect.ValueOf(&x)
fmt.Println("setable:", p.CanSet())
v2 := p.Elem()
fmt.Println("setable:", v2.CanSet())
```

如何通过Value设置原始对象值呢？

`Value.SetXXX()`系列函数可设置Value中原始对象的值。

系列函数有：
- Value.SetInt()
- Value.SetUint()
- Value.SetBool()
- Value.SetBytes()
- Value.SetFloat()
- Value.SetString()
- ...

**设置函数这么多，到底该选用哪个Set函数？**
根据`Value.Kind()`的结果去获得变量的底层类型，然后选用该类别的Set函数。


## 参考资料
1. [https://blog.golang.org/laws-of-reflection](https://blog.golang.org/laws-of-reflection)


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/02/24/go-law-of-reflect/](http://lessisbetter.site/2019/02/24/go-law-of-reflect/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="https://lessisbetter.site/images/2019-01-article_qrcode.jpg" style="border:0"  align=center />