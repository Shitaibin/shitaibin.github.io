---
title: 你滥用log了吗
date: 2019-07-12 18:17:24
tags: ['Go', 'log']
---

代码Review的时候，遇到过一些log滥用的情况，今天聊一聊滥用（过渡使用）日志。


> 好的log能够帮助开发人员快速定位bug，而差的log各有各的不同。

## 你滥用日志了吗？

是什么导致了滥用log？是不是存在这些误解：

**1. 害怕出了问题，现有的log无法定位**，要多加一些log，恨不得每段都有一个log，log数简直越多越好，看日志有一种，每一步都非常清晰的错觉。

**2. 不知道log多了，定位效率更低**，试问你有没有经历过几分钟刷出了G级别日志文件？在这种日志文件里定位bug，简直是大海捞针，这让log的价值非常低。

**3. 不知道log多了会影响性能**，log自身涉及格式化和文件读写，虽然现在各log库都已经比较高效了，但是，这也扛不住“海量”的log啊，积少成多，势必影响程序性能。

**4. 对log级别错误的认知**：日志级别设置为Info，Debug、Trace级别的日志不会打印，Debug、Trace级别日志多没关系。虽然日志不会输出，并不代表相关代码没执行啊。


第4点重点解释一下：

![debug-demo](https://lessisbetter.site/images/2019-07-debug-demo.png)

这是一个打印Debug级别的日志，它还有1项日志信息，是来自`func()`的结果，请问：

1. 日志级别设置为Info，log.Debug会执行吗？`func()`还会执行吗？
2. 如果这行日志频繁被执行，是不是浪费了CPU做无用功？

如果你认为不会执行，看下面的Demo，log使用zap。

![log-test](https://lessisbetter.site/images/2019-07-log-test.png)

结果：

![log-ret](https://lessisbetter.site/images/2019-07-log-ret.png)

事实证明无论限制的日志级别是什么，`log.***`一定会被调用，它入参中的函数也一定会被调用，只不过是日记级别不满足打印时，不会打印而已。被调函数的结果只被这条`log.***`使用，结果这个日志根本不打印，这就浪费了CPU。

日志级别都设置为Info了，Debug级别的日志为何还会打印？

如果你有这个问题，你可能没有理解2个地方。

日志级别设置为Info，不代表`log.Debug`函数不执行。`log.Debug`函数一定会执行，看下图，`log.Info，Error`等接口会调用相同的真实实现函数`log.log`，`log.log`的入参包含了`log.Info`等接口的入参，以及当前的`log_level`，比如以下2种是等价的：

![log-log](https://lessisbetter.site/images/2019-07-log-log.png)

所以，无论设置的是什么日志级别控制，`log.Debug`一定会被执行，至于当前日志是否会打印，会在`log.log`里决定。

![image-20190712072742045](https://lessisbetter.site/images/2019-07-log-call.png)



日志为Warn级别，Debug日志不会打印，`func()`会不会执行？

日志打印本质是函数调用，会先计算入参，再调用函数。比如：

![log-debug](https://lessisbetter.site/images/2019-07-log-debug.png)

所以`func()`一定会被调用。



## 总结

针对滥用日志的情况给几点建议：

1. 1条日志描述清when、where、what，提供有效信息，这就对定位很有帮助了。
2. 只在“可能”出问题的地方打印日志，一些能根据上下文日志推断的地方，就无需再增加日志。
3. 日志打印不要调用函数。

> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/07/12/do-not-abuse-of-log/](http://lessisbetter.site/2019/07/12/do-not-abuse-of-log/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="https://lessisbetter.site/images/2019-01-article_qrcode.jpg" style="border:0"  align=center />