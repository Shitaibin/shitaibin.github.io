---
title: 为什么PBFT的节点数量是3f+1?
date: 2019-01-23 17:15:06
tags: ['区块链','一致性','共识算法', 'PBFT']
---

问题：为什么PBFT的节点数量是3f+1?


pbft的论文提到这样**2**段话，可以很好的解决这个问题：



![](https://lessisbetter.site/images/2019-02-pbft-paper1.png)
*page3*


**在存在f个faulty节点的情况下，`3f+1`是保证系统安全性和活跃性的最小的总节点数量**。当存在f个节点不响应的情况下，需要`n-f`个正常节点达成共识需要保障`n-f > f`。另外一种情况：f个响应的节点是错误的（响应错误数据），f个节点没有响应，但他们不是faulty的，所以要保证`好的响应的节点 - 好的未响应的节点 - 坏的响应的节点 > 坏的节点`，即需要`n - f -f > f`，`n > 3f`。但n只能是整数，所以`n >= 3f + 1`。

![](https://lessisbetter.site/images/2019-02-pbft-paper2.png)
*page3*

副本节点的数量设为`R`，为了**简便**使`R = 3f + 1`。尽管存在副本节点数量多于`3f+1`的情况，比如`3f+2, 3f+3`，**但多出来的节点没有带来任何改善，反而降低了系统的性能，因为需要更多的通信量**。

为什么这样说呢？

`3f+2, 3f+3`的实际能容错的节点数量与`3f+1`是相同的，即只能容忍`f`个faulty的节点。

根据论文，当`n = 3f+1`时，
- 在Prepare进入Commit阶段，需要`2f`个Prepare消息，即需要`n - 1 - f`条Prepare消息。
- 在Commit阶段完成，需要`2f+1`条Commit消息，即需要`n - f`条Commit消息。

请思考，当`n = 3f+2`时，
- 在Prepare进入Commit阶段，需要`n - 1 - f`个Prepare消息，即`2f+1`需要条Prepare消息。
- 在Commit阶段完成，需要`n - 1 - f`条Commit消息，即需要`2f+1`条Commit消息。


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/01/23/why-pbft-using-3f-plus-1/](http://lessisbetter.site/2019/01/23/why-pbft-using-3f-plus-1/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="https://lessisbetter.site/images/2019-01-article_qrcode.jpg" style="border:0"  align=center />
