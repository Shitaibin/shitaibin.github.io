---
title: Docker容器基础3：Cgroup - cpu, cpuacct, cpuset子系统
date: 2020-09-01 23:00:24
tags: ['Docker', 'Kubernetes', 'Cgroup']
---



## 测试环境

Ubuntu 18.04，内核版本4.15，机器拥有4核。

```
[~]$ cat /proc/version
Linux version 4.15.0-112-generic (buildd@lcy01-amd64-027) (gcc version 7.5.0 (Ubuntu 7.5.0-3ubuntu1~18.04)) #113-Ubuntu SMP Thu Jul 9 23:41:39 UTC 2020
[~]$
[~]$ cat /etc/os-release
NAME="Ubuntu"
VERSION="18.04.3 LTS (Bionic Beaver)"
...
[~]$ cat /proc/cpuinfo | grep "processor" | wc -l
4
```

## CPU相关子系统简介

有关CPU的cgroup subsystem有3个：
- cpu : 用来**限制**cgroup的CPU使用率
- cpuacct : 用来**统计**cgroup的CPU的使用率
- cpuset : 用来绑定cgroup到指定CPU的哪个核上和NUMA节点

每个子系统都有多个配置项和指标文件，主要介绍下图常用的配置项：

![cpu、cpuacct、cpuset的指标](https://lessisbetter.site/images/2020-09-cgroup-cpux.png)

### cpu

cpu子系统用来限制cgroup如何使用CPU的时间，也就是调度，它提供了3种调度办法，并且这3种调度办法都可以在启动容器时进行配置，分别是：
- share ：相对权重的CPU调度
- cfs ：完全公平调度
- rt ：实时调度

share调度的配置项和原理如下：

![cpu share调度](https://lessisbetter.site/images/2020-09-cgroup-cpu-share.png)

cfs 是Completely Fair Scheduler的缩写，代表完全公平调度，它利用 `cpu.cfs_quota_us` 和 `cpu.cfs_period_us` 实现公平调度，这两个文件内容组合使用可以限制进程在长度为 `cfs_period_us` 的时间内，只能被分配到总量为 `cfs_quota_us` 的 CPU 时间。CFS的指标如下：

![cpu cfs调度](https://lessisbetter.site/images/2020-09-cgroup-cpu-cfs.png)

**注意**： 
1. `cfs_period_us` 取值范围1000~1000000：1ms ~ 1s，`cfs_quota_us`的最小值为1000，当设置的值不在取值范围时，会报 `write xxx: invalid argument` 的错误。
2. 只有这2个参数都有意义时，才能把任务写入到 tasks 文件。

rt 是RealTime的缩写，它是实时调度，它与cfs调度的区别是cfs不会保证进程的CPU使用率一定要达到设置的比率，而rt会严格保证，让进程的占用率达到这个比率，适合实时性较强的任务，它包含 `cpu.rt_period_us` 和 `cpu.rt_runtime_us` 2个配置项。

### cpuacct

cpuacct包含非常多的统计指标，常用的有以下4个文件：

![cpuacct常用指标文件](https://lessisbetter.site/images/2020-09-cgroup-cpuacct.png)




### cpuset

为啥需要cpuset？

比如：
1. 多核可以提高并发、并行，但是核太多了，会影响进程执行的局部性，降低效率。
2. 一个服务器上部署多种应用，不同的应用不同的核。

cpuset也包含居多的配置项，主要是分为cpu和mem 2类，mem与NUMA有关，其常用的配置项如下图:

![cpuset常用配置项](https://lessisbetter.site/images/2020-09-cgroup-cpuset.png)


## 利用Docker演示Cgroup CPU限制

### cpu 

#### 不限制cpu的情况

stress为基于ubuntu:16.04安装stress做出来的镜像，利用stress来测试cpu限制。

Dockerfile如下：

```Dockerfile
From ubuntu:16.04
# Using Aliyun mirror
RUN mv /etc/apt/sources.list /root/sources.list.bak
RUN sed -e s/security.ubuntu/mirrors.aliyun/ -e s/archive.ubuntu/mirrors.aliyun/ -e s/archive.canonical/mirrors.aliyun/ -e s/esm.ubuntu/mirrors.aliyun/ /root/sources.list.bak > /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y stress
WORKDIR /root
```

启动容器不做任何cpu限制，利用 `stress -c 2` 开启另外2个stress线程，共3个：

```
[/sys/fs/cgroup/cpu]$ docker run --rm -it stress:16.04
root@5fad38726740:/# stress -c 2
stress: info: [12] dispatching hogs: 2 cpu, 0 io, 1 vm, 0 hdd
```

在`cgroup/cpu,cpuacct`下，找到该容器对应的目录，查看 `cfs_period_us` 和 `cfs_quota_us` 的默认值：

```
[/sys/fs/cgroup/cpu,cpuacct/system.slice/docker-5fad38726740b90b93c06972fe4a9f11391a38aaeb3e922f10c3269fa32e1873.scope]$ cat cpu.cfs_period_us
100000
[/sys/fs/cgroup/cpu,cpuacct/system.slice/docker-5fad38726740b90b93c06972fe4a9f11391a38aaeb3e922f10c3269fa32e1873.scope]$ cat cpu.cfs_quota_us
-1
```

查看主机CPU利用率，为3个stress进程，每1个都100%，它们属于同一个cgroup：

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 5616 root      20   0  109872 102336     36 R 100.0  1.3   0:07.46 stress
 5617 root      20   0    7468     88      0 R 100.0  0.0   0:07.45 stress
 5615 root      20   0    7468     88      0 R 100.0  0.0   0:07.45 stress
```


#### 限制cpu的情况

`--cpu-quota`设置5000，开stress分配到另外2个核。

[/sys/fs/cgroup/cpu]$ docker run --rm -it --cpu-quota=5000 stress:16.04
root@7e79005d7ca1:/#
root@7e79005d7ca1:/# stress  -c 2
stress: info: [13] dispatching hogs: 2 cpu, 0 io, 1 vm, 0 hdd

查看 `cfs_period_us` 和 `cfs_quota_us` 的设置，`5000/100000 = 5%` ， 即限制该容器的CPU使用率不得超过5%。

```
[/sys/fs/cgroup/cpu,cpuacct/system.slice/docker-7e79005d7ca1b338d870d3dc79af3f1cd38ace195ebd685a09575f6acee36a07.scope]$ cat cpu.cfs_quota_us
5000
[/sys/fs/cgroup/cpu,cpuacct/system.slice/docker-7e79005d7ca1b338d870d3dc79af3f1cd38ace195ebd685a09575f6acee36a07.scope]$ cat cpu.cfs_period_us
100000
```

利用top可以看到3个进程总cpu使用率5.1%。

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 5411 root      20   0    7468     92      0 R   1.7  0.0   0:00.53 stress
 5412 root      20   0  109872 102500     36 R   1.7  1.3   0:00.30 stress
 5413 root      20   0    7468     92      0 R   1.7  0.0   0:00.35 stress
```

### cpuacct

查看`cpuacct.stat, cpuacct.usage, cpuacct.usage_percpu`，一定要同时输出这几个文件，不然可能有时间差，利用python可以计算每个核上的时间之和为`usage`，即该容器占用的cpu总时间。

```
[/sys/fs/cgroup/cpu,cpuacct]$ cat cpuacct.*
user 20244450 // cpuacct.stat
system 52361  // cpuacct.stat
204310768947624  // cpuacct.usage
61143521333219 32616883199042 73804985004267 36745379411096 // cpuacct.usage_percpu

[/sys/fs/cgroup/cpu,cpuacct]$ python
Python 2.7.5 (default, Apr 11 2018, 07:36:10)
[GCC 4.8.5 20150623 (Red Hat 4.8.5-28)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> sum = 61143521333219+32616883199042+73804985004267+36745379411096
>>> dist = sum - 204310768947624
>>> dist
0
>>> sum
204310768947624
>>> sum2 = 20244450+52361
>>> sum2
20296811
```

### cpuset

启动容器，然后使用stress占用1个核：

```
[/sys/fs/cgroup/cpu]$ docker run --rm -it stress:16.04
root@a907df624697:~#
root@a907df624697:~# stress -c 1
stress: info: [12] dispatching hogs: 1 cpu, 0 io, 0 vm, 0 hdd
```

top显示占用100%CPU。

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 6633 root      20   0    7480     92      0 R 100.0  0.0   0:12.13 stress
```
 



cpuset 能看到可使用的核为： 0~3。

```
[/sys/fs/cgroup/cpuset/docker/a907df624697a19631929c1e9e971d2893afddbf6befb0dd44be3cf0024a3e0d]$ cat cpuset.cpus
0-3
```

使用cpuacct查看CPU情况使用统计，可以看到用了4个核上的使用时间。

```
[/sys/fs/cgroup/cpu/docker/a907df624697a19631929c1e9e971d2893afddbf6befb0dd44be3cf0024a3e0d]$ cat cpuacct.usage cpuacct.usage_all
153015464879
cpu user system
0 45900415963 0
1 4675002 0
2 63537634967 0
3 43572738947 0
```

现在创建一个新容器，限制只能用1，3这2个核：

```
[/sys/fs/cgroup/cpu]$ docker run --rm -it --cpuset-cpus 1,3 stress:16.04
root@0ce61a38e7c9:~# stress -c 1
stress: info: [10] dispatching hogs: 1 cpu, 0 io, 0 vm, 0 hdd
```

查看可以使用的核：

```
[/sys/fs/cgroup/cpuset/docker/0ce61a38e7c9621334871ab40d5b7d287d89a1e994148833ddf3ca4941a39c89]$ cat cpuset.cpus
1,3
```

`cpuacct.usage_all` 显示只有1、3两个核的数据在使用：

```
[/sys/fs/cgroup/cpu/docker/0ce61a38e7c9621334871ab40d5b7d287d89a1e994148833ddf3ca4941a39c89]$ cat cpuacct.usage_all
cpu user system
0 0 0
1 37322884717 0
2 0 0
3 21332956940 0
```

现在切换到root账号，把 `sched_load_balance` 标记设置为0，不进行核间的负载均衡，然后利用 `cpuacct.usage_all` 查看每个核上的时间，隔几秒前后查询2次，可以发现3号核的cpu使用时间停留在`21332956940`，而核1的cpu使用时间从`185084024837` 增加到 `221479683602`， 说明设置之后stress线程一致在核1上运行，不再进行负载均衡。

```
[/sys/fs/cgroup/cpuset/docker/0ce61a38e7c9621334871ab40d5b7d287d89a1e994148833ddf3ca4941a39c89]$ echo 0 > cpuset.sched_load_balance

[/sys/fs/cgroup/cpu/docker/0ce61a38e7c9621334871ab40d5b7d287d89a1e994148833ddf3ca4941a39c89]$ cat cpuacct.usage_all
cpu user system
0 0 0
1 185084024837 0
2 0 0
3 21332956940 0

[/sys/fs/cgroup/cpu/docker/0ce61a38e7c9621334871ab40d5b7d287d89a1e994148833ddf3ca4941a39c89]$ cat cpuacct.usage_all
cpu user system
0 0 0
1 221479683602 0
2 0 0
3 21332956940 0
```
## 利用Go演示Cgroup CPU限制

测试程序：[02.2.cgroup_cpu.go](https://github.com/Shitaibin/notes/blob/master/docker/codes/02.2.cgroup_cpu.go) 。

该程序接受1个入参，代表测试类型：
- 空或`nolimit`: 无限制
- `cpu` : 执行cpu限制，利用cfs把cpu使用率控制在5%
- `cpuset` : 限制只使用核1和核3

测试程序的执行动作如下：
1. 程序首先在cpu和cpuset中创建2个cgroup，
2. 按传入的参数设置限制或不设置限制
3. 利用`/proc/self/exe`启动进程
4. 把进程加入到2个cgroup的tasks，即加入cgroup
5. 进程会创建3个goroutine不断的去消耗cpu，它们会占用3个线程
   
当CPU使用率不限制时，3个线程会分配到3个核上执行，所以进程的CPU使用率应当达到300%。

利用测试程序分3组实验，然后利用 `top`、`cpuacct.usage_all`、`cpuset.cpu` 3个角度查看CPU限制和使用情况。

### 不限制CPU

1. 启动测试程序，进程id为4805，进入Namespace后进程id变为1，可以看到启动了3个worker协程。

```
[/home/ubuntu/workspace/notes/docker/codes]$ go run 02.2.cgroup_cpu.go
---------- 1 ------------
Test type: No limit
cmdPid: 4805
---------- 2 ------------
Current pid: 1
worker 2 start
worker 0 start
worker 1 start
```

2. top查看进程的CPU占用率为300%，符合预期。

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 4805 root      20   0    3376   1004    836 R 300.0  0.0   4:41.09 exe
```

3. 利用cpuacct查看每个核上的使用时间：

```
[/sys/fs/cgroup/cpuacct]$ cat test_cpu_limit/cpuacct.usage_all
cpu user system
0 8046597390 0
1 34269979109 0
2 26597651949 0
3 33886705168 0
```

4. 利用cpuset.cpus查看使用的cpu核：

```
[/sys/fs/cgroup/cpuset]$ cat test_cpuset_limit/cpuset.cpus
0-3
```


### 使用cpu限制CPU使用率

1. 启动测试程序：

```
[/home/ubuntu/workspace/notes/docker/codes]$ go run 02.2.cgroup_cpu.go cpu
---------- 1 ------------
Test type: Cpu limit
cmdPid: 4937
---------- 2 ------------
Current pid: 1
worker 2 start
worker 1 start
worker 0 start
```

2. top查看进程的CPU占用率为5.0%，符合预期。

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 4937 root      20   0    3376   1004    836 R   5.3  0.0   0:08.40 exe
```

3. 利用cpuacct查看每个核上的使用时间，由于没有限制使用的cpu核，所以每个核上都还有运行时间

```
[/sys/fs/cgroup/cpuacct]$ cat test_cpu_limit/cpuacct.usage_all
cpu user system
0 2036903414 0
1 44170 0
2 4428266075 0
3 4356927661 0
```

4. 利用cpuset.cpus查看使用的cpu核

```
[/sys/fs/cgroup/cpuset]$ cat test_cpuset_limit/cpuset.cpus
0-3
```

### 使用cpuset限制CPU占用的核


1. 启动测试程序，这次与前面的不同，看到只起来了2个worker协程在运行，因为机器上的Go版本是go1.10，还不支持抢占，当协程为for循环时，2个协程都持续运行，不让出cpu，只有2个核时，第3个协程无法运行。

```
[/home/ubuntu/workspace/notes/docker/codes]$ go run 02.2.cgroup_cpu.go cpuset
---------- 1 ------------
Test type: Cpuset limit
cmdPid: 5063
---------- 2 ------------
Current pid: 1
worker 2 start
worker 0 start
```

2. top查看进程的CPU占用率为200%，符合只使用2个核的预期。

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 5063 root      20   0    3376   1004    836 R 199.7  0.0   4:21.49 exe
```

3. 利用cpuacct查看每个核上的使用时间，只有核1和3上有时间统计，说明只使用了核1和3

```
[/sys/fs/cgroup/cpuacct]$ cat test_cpu_limit/cpuacct.usage_all
cpu user system
0 0 0
1 24172994458 0
2 0 0
3 24213057511 0
```

4. 利用cpuset.cpus查看使用的cpu核

```
[/sys/fs/cgroup/cpuset]$ cat test_cpuset_limit/cpuset.cpus
1,3
```

## 推荐资料


1. [Linux Kernel关于cgroup cpu、cpuset的文档](https://kernel.googlesource.com/pub/scm/linux/kernel/git/glommer/memcg/+/cpu_stat/Documentation/cgroups/)
2. [阿里同学的书《自己动手写Docker》](https://union-click.jd.com/jdc?e=&p=AyIGZRtSFwsWB1EcXhUyFQ5WEloVCxMBURxrUV1KWQorAlBHU0VeBUVNR0ZbSkdETlcNVQtHRVNSUVNLXANBRA1XB14DS10cQQVYD21XHgBcGFIUAhsGUx9cJQEbBTJbEmFdcHkRSANGBhBDCnkmEVQeC2UaaxUDEwVWEl8RBhM3ZRtcJUN8B1QaUxMCFAFlGmsVBhoOUx9fFwESB1IfaxICGzeDtdnBl4nT2YZrJTIRN2UrWyUBIkU7HQxBABEGBhILHVdGAgcaXB0DQARWHQ4QVhFVVhkLEVciBVQaXxw%3D)
3. [解决写 cpu.cfs_quota_us `invalid argument`问题](https://my.oschina.net/xiaominmin/blog/3068364)
4. [解决写 cpuset.tasks `No space` 问题](https://blog.csdn.net/xftony/article/details/80536562)
5. [cgroup使用踩坑](https://www.cnblogs.com/raymondshiquan/articles/2727037.html)