---
title: Docker容器基础1：Cgroup - 资源控制简介
date: 2020-08-27 21:43:52
tags: ['Docker', 'Kubernetes', 'Cgroup']
---


## 什么是Cgroup

Cgroup 是 Control Group 的缩写，提供对一组进程，及未来子进程的资源**限制、控制、统计**能力，包括CPU、内存、磁盘、网络。

- 限制：限制的资源最大使用量阈值。比如不能超过128MB内存，CPU使用率不得超过50%，或者只能是否CPU的某哪几个核。
- 控制：超过资源使用最大阈值时，进程会被控制，不任由它发展。比如cgroup内所有tasks的内存使用量超过阈值的结果就是被KILL，CPU使用率不得超过设定值。
- 统计：统计资源的使用情况等指标。比如cgroup内tasks的内存使用量，占用CPU的时间。

Cgroup 包含3个组件：
- cgroup ：一组进程，可以加上subsystem
- subsystem ：一组资源控制模块，CPU、内存...
- hierarchy ： 把一组cgroup串成树状结构，这样就能实现cgroup的继承。为什么要继承呢？就如同docker镜像的继承，站在前人的基础之上，免去重复的配置

## 为什么需要Cgroup

为什么需要Cgroup的问题等价于：为什么需要限制一组进程的资源？

有多种原因，比如：
1. Linux是一个可以多用户登录的系统，如何限制不同的用户使用不同量的系统资源呢？
2. 某个系统有64核，由于局部性原理，如果一组进程在64个核上调度，效率比较低，但把这些进程只允许在某几个核上调度，就有较好的局部性，提高效率。这类似与在分布式系统中，某个有状态的请求，最好能分配到上一次处理该请求的机器上一样的道理。

cgroup的文档中还提到一个思路：实现资源限制的技术有多种，为什么使用cgroup？

cgroup是内核实现的，它更轻量、更高效、对内核的热点路径影响最小。

## 你的Linux支持哪些Cgroup subsystem

查看当前系统支持的subsystem，共12个子系统。


```
[/sys/fs/cgroup]$ cat /proc/cgroups
#subsys_name	hierarchy	num_cgroups	enabled
cpuset	8	4	1
cpu	2	74	1
cpuacct	2	74	1
memory	11	74	1
devices	6	69	1
freezer	10	4	1
net_cls	4	4	1
blkio	9	69	1
perf_event	5	4	1
hugetlb	7	4	1
pids	3	69	1
net_prio	4	4	1
```

从左到右字段的含义分别是：

1. subsys_name: subsystem的名字
2. hierarchy: subsystem所关联到的cgroup树的ID，如果多个subsystem关联到同一颗cgroup树，那么他们的这个字段将一样，比如这里的cpu和cpuacct就一样，表示他们绑定到了同一颗树。如果出现下面的情况，这个字段将为0：
   - 当前subsystem没有和任何cgroup树绑定
   - 当前subsystem已经和cgroup v2的树绑定
   - 当前subsystem没有被内核开启
3. num_cgroups: subsystem所关联的cgroup树中进程组的个数，也即树上节点的个数
4. enabled: 1表示开启，0表示没有被开启(可以通过设置内核的启动参数“cgroup_disable”来控制subsystem的开启).

[Cgroup的内核文档](https://www.kernel.org/doc/Documentation/cgroup-v1/)对各 cgroup 和 subsystem 有详细的介绍，以下是每个 subsystem 功能简记：
1. cpu ：用来**限制**cgroup的CPU使用率
2. cpuacct ：用来**统计**cgroup的CPU的使用率
3. cpuset ： 用来绑定cgroup到指定CPU哪个核上和NUMA节点
4. memory ：限制和统计cgroup的内存的使用率，包括process memory, kernel memory, 和swap
5. devices ： 限制cgroup创建(mknod)和访问设备的权限
6. freezer ： suspend和restore一个cgroup中的所有进程
7. net_cls ： 将一个cgroup中进程创建的所有网络包加上一个classid标记，用于tc和iptables。 只对发出去的网络包生效，对收到的网络包不起作用
8. blkio ： 限制cgroup访问块设备的IO速度
9. perf_event ： 对cgroup进行性能监控
10. net_prio ： 针对每个网络接口设置cgroup的访问优先级
11. hugetlb ： 限制cgroup的huge pages的使用量
12. pids ：限制一个cgroup及其子孙cgroup中的总进程数

这些子系统的排列顺序，就是引入Linux内核顺序，最早的是cpu subsystem ，引入自Linux 2.6.24，最晚的是pid subsystem ，引入自 Linux 4.3。

## 查看子系统和cgroup的挂载

cgroup是通过文件系统实现的，每个目录都是一个cgroup节点，目录中的子目录都是子cgroup节点，这样就形成了 cgroup的 hierarchy 特性。

cgroup会挂载到 `/sys/fs/cgroup/`目录，该目录下的目录基本都是subsystem，`systemd`目录除外（它是 systemd 自建在cgroup下的目录，但不是子系统）：

```
[/sys/fs/cgroup]$ ll
total 0
dr-xr-xr-x 6 root root  0 Aug 30 09:30 blkio
lrwxrwxrwx 1 root root 11 Aug 30 09:30 cpu -> cpu,cpuacct
lrwxrwxrwx 1 root root 11 Aug 30 09:30 cpuacct -> cpu,cpuacct
dr-xr-xr-x 7 root root  0 Aug 30 09:30 cpu,cpuacct
dr-xr-xr-x 3 root root  0 Aug 30 09:30 cpuset
dr-xr-xr-x 6 root root  0 Aug 30 09:30 devices
dr-xr-xr-x 3 root root  0 Aug 30 09:30 freezer
dr-xr-xr-x 3 root root  0 Aug 30 09:30 hugetlb
dr-xr-xr-x 6 root root  0 Aug 30 09:30 memory
lrwxrwxrwx 1 root root 16 Aug 30 09:30 net_cls -> net_cls,net_prio
dr-xr-xr-x 3 root root  0 Aug 30 09:30 net_cls,net_prio
lrwxrwxrwx 1 root root 16 Aug 30 09:30 net_prio -> net_cls,net_prio
dr-xr-xr-x 3 root root  0 Aug 30 09:30 perf_event
dr-xr-xr-x 6 root root  0 Aug 30 09:30 pids
dr-xr-xr-x 6 root root  0 Aug 30 09:30 systemd
```

发现cpu、cpuacct都指向了 `cpu,cpuacct` 目录，把它们合成了1个cgroup节点。另外 net_cls 和 net_prio 也都合到了 `net_cls,net_prio` 节点，也就形成了下面这幅图的样子，并把资源控制分成了5个类别：CPU、内存、网络、进程控制、设备，另外的`perf_event`是cgroup对自身的监控，不归于资源控制。

![](https://lessisbetter.site/images/2020-08-30-cgroup-subsystem.png)

子系统挂载到cgroup的虚拟文件系统是通过mount命令实现的，系统启动时自动挂载subsystem到cgroup，查看已经挂载的Cgroup：

```
[~]$ mount -t cgroup
cgroup on /sys/fs/cgroup/systemd type cgroup (rw,nosuid,nodev,noexec,relatime,xattr,release_agent=/lib/systemd/systemd-cgroups-agent,name=systemd)
cgroup on /sys/fs/cgroup/memory type cgroup (rw,nosuid,nodev,noexec,relatime,memory)
cgroup on /sys/fs/cgroup/pids type cgroup (rw,nosuid,nodev,noexec,relatime,pids)
cgroup on /sys/fs/cgroup/cpu,cpuacct type cgroup (rw,nosuid,nodev,noexec,relatime,cpu,cpuacct)
cgroup on /sys/fs/cgroup/freezer type cgroup (rw,nosuid,nodev,noexec,relatime,freezer)
cgroup on /sys/fs/cgroup/net_cls,net_prio type cgroup (rw,nosuid,nodev,noexec,relatime,net_cls,net_prio)
cgroup on /sys/fs/cgroup/devices type cgroup (rw,nosuid,nodev,noexec,relatime,devices)
cgroup on /sys/fs/cgroup/cpuset type cgroup (rw,nosuid,nodev,noexec,relatime,cpuset)
cgroup on /sys/fs/cgroup/blkio type cgroup (rw,nosuid,nodev,noexec,relatime,blkio)
cgroup on /sys/fs/cgroup/hugetlb type cgroup (rw,nosuid,nodev,noexec,relatime,hugetlb)
cgroup on /sys/fs/cgroup/perf_event type cgroup (rw,nosuid,nodev,noexec,relatime,perf_event)
```

查看某个进程所属的cgroup：

```
[/sys/fs/cgroup]$ # $$代表当前进程
[/sys/fs/cgroup]$ cat /proc/$$/cgroup
11:memory:/user.slice/user-1000.slice/session-269.scope
10:freezer:/
9:blkio:/user.slice
8:cpuset:/
7:hugetlb:/
6:devices:/user.slice
5:perf_event:/
4:net_prio,net_cls:/
3:pids:/user.slice
2:cpuacct,cpu:/user.slice/user-1000.slice/session-269.scope
1:name=systemd:/user.slice/user-1000.slice/session-269.scope
```

每一行从左到右，用`:`分割依次是：
- `11`： cgroup继承树的节点的ID
- `memory`: 当前节点上挂载的子系统
- `/user.slice/user-1000.slice/session-269.scope`: cgroup节点相对于cgroup根目录下子系统的相对路径，转换成绝对路径就是：`/sys/fs/cgroup/memory/user.slice/user-1000.slice/session-269.scope`



## 再聊cgroup hierarchy

在 cpu,cpuacct 子系统下创建一个测试cgroup节点：

```sh
[/sys/fs/cgroup/cpu,cpuacct]$ sudo mkdir dabin_test_cpu_cgroup
[/sys/fs/cgroup/cpu,cpuacct]$ cd dabin_test_cpu_cgroup
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ ls
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ ls cgroup.*
cgroup.clone_children  cgroup.event_control  cgroup.procs
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ cat cgroup.clone_children
0
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ cat cgroup.procs
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ ls notify_on_release tasks
notify_on_release  tasks
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ cat tasks
[/sys/fs/cgroup/cpu,cpuacct/dabin_test_cpu_cgroup]$ cat notify_on_release
0
```

cgroup hierarchy (继承树)结构，每个cgroup节点都包含以下几个文件：

- cgroup.clone_children : 被cpuset控制器使用，值为1时子cgroup初始化时拷贝父cgroup的配置
- cgroup.procs : cgroup中的线程组id
- tasks : 当前cgroup包含的进程列表
- notify_on_release : 值为0或1，1代表当cgroup中的最后1个task退出，并且子cgroup移除时，内核会在继承树根目录运行`release_agent`文件

## 总结

cgroup对一组进程的资源进行控制，包括但不限于CPU、内存、网络、磁盘等资源，共12种资源，通过12个subsystem去进行限制、控制。

cgroup由内核使用文件系统实现，文件系统的层级结构实现了cgroup的层级结构，它默认挂载到 `/sys/fs/cgroup` 目录。

## 参考资料


1. [Linux Kernel Cgroup的文档](https://kernel.googlesource.com/pub/scm/linux/kernel/git/glommer/memcg/+/cpu_stat/Documentation/cgroups)
2. [阿里同学的书《自己动手写Docker》](https://union-click.jd.com/jdc?e=&p=AyIGZRtSFwsWB1EcXhUyFQ5WEloVCxMBURxrUV1KWQorAlBHU0VeBUVNR0ZbSkdETlcNVQtHRVNSUVNLXANBRA1XB14DS10cQQVYD21XHgBcGFIUAhsGUx9cJQEbBTJbEmFdcHkRSANGBhBDCnkmEVQeC2UaaxUDEwVWEl8RBhM3ZRtcJUN8B1QaUxMCFAFlGmsVBhoOUx9fFwESB1IfaxICGzeDtdnBl4nT2YZrJTIRN2UrWyUBIkU7HQxBABEGBhILHVdGAgcaXB0DQARWHQ4QVhFVVhkLEVciBVQaXxw%3D)