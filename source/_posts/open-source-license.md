---
title: 如何选择开源协议
date: 2020-05-05 14:37:26
tags: ['开源']
---

当基于开源项目发布新的开源项目时，我们需要说明项目所使用的License，同样也需要考虑你基于开源项目所做的事情，是否满足该项目的License。

下面这2幅图摘自 [开源许可证都有什么区别,一般开源项目用什么许可证? - 知乎](https://www.zhihu.com/question/28292322)，足以帮助我们判断：
1. 要做的事情，是否满足开源项目的License。
2. 开源一个项目，该如何选择License。

![](https://lessisbetter.site/images/2020-05-license-choose.jpg)
来源：https://www.zhihu.com/question/28292322/answer/656121132

![](https://lessisbetter.site/images/2020-05-license-2.jpg)
来源：https://www.zhihu.com/question/28292322/answer/840556759
从左到右，是从宽松到严格。

举例：
1. 以太坊采License用的是LGPLv3，修改源码后如果提供给外部使用必须开源，不要求新增代码采用相同的License，也不要求对新增代码进行文档说明，后来我们项目同样采用了LGPLv3。
2. Fabric采用Apache 2.0，基于Fabric项目原有代码都必须放置Fabric原有版权声明，但可以选择不开源。