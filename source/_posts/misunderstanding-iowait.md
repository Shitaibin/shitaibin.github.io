---
title: 被误解的iowait
date: 2020-09-28 16:57:19
tags: ['Linux', 'IO', '性能优化']
---

有一个cpu指标叫`iowait`或者`wa`，在top、iostat、vmstat命令中都可以看到这一项。


```
[~]$ top
top - 08:58:06 up 26 days, 23:20,  1 user,  load average: 0.07, 0.23, 0.26
Tasks: 164 total,   1 running, 111 sleeping,   0 stopped,   0 zombie
%Cpu(s):  2.5 us,  1.2 sy,  0.0 ni, 96.2 id,  0.1 wa,  0.0 hi,  0.1 si,  0.0 st
KiB Mem :  8167548 total,   698220 free,   996640 used,  6472688 buff/cache
KiB Swap:        0 total,        0 free,        0 used.  7061988 avail Mem

[~]$ iostat
Linux 4.15.0-112-generic (shitaibin-x) 	09/28/20 	_x86_64_	(4 CPU)

avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           1.02    0.00    0.55    0.86    0.00   97.56

Device             tps    kB_read/s    kB_wrtn/s    kB_read    kB_wrtn
loop0             0.00         0.00         0.00          5          0
vda              13.32         2.65        84.15    6182326  196098973

[~]$
[~]$
[~]$ vmstat
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 0  0      0 685616 177356 6306652    0    0     1    21    5    3  1  1 98  1  0
```

这个指标的字面含义是等待IO的时间（百分比），很多人会认为这个指标暗示这IO瓶颈，然而这是有一定无解的，iowait高不一定有IO瓶颈。

```
iowait = CPU空闲时间 / CPU总时间 ，前提CPU在等待至少一项IO操作完成
```

所以它真正的含义是有未完成的IO操作时，CPU空闲的时间。

这2个资料都把iowait讲解的很清晰，并且举例iowait和IO瓶颈无关的例子。
- [理解iowait](http://linuxperf.com/?p=33)
- [浪潮：CPU iowait详解](https://www.inspurpower.com/upload/file/1583309942.pdf)

例子：
- 低iowait，高IO的例子：IO高同时CPU计算也高，这样CPU的空闲时间少，造成iowait比较低，CPU密集掩盖了IO密集。
- 高iowait，低IO的例子：CPU计算很少，CPU基本空闲，但也有1个进程在IO，所以iowait高，但实际IO根本没任何瓶颈。

