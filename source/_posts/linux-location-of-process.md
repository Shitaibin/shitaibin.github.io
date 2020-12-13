---
title: 查看Linux运行程序的文件路径
date: 2019-03-01 19:15:29
tags: ['Linux']
---

通过ps及top命令查看进程信息时，看不到进程的绝对路径，可以使用：`sudo ls -l /proc/PID`查看。

Linux在启动一个进程时，系统会在/proc下创建一个以PID命名的文件夹，在该文件夹下会有该进程的信息，其中包括一个名为exe的文件即记录了绝对路径。


![](https://lessisbetter.site/images/2019-03-proc_path.png)



## 解决的问题

发现服务器上并没有运行耗CPU的服务，但top查看时，总存在占用CPU 60%的进程，kill一段时间后，又会出现新进程，名字变化而已，并且名字类似系统服务的名字，怀疑是恶意程序（挖矿木马）。


找到创建该进程的父进程，杀死父进程后，再杀死此恶意程序，最后从磁盘删除。

在top中，按f选择要显示的列，通过向下箭头找到PPID，按空格选中，按q退出，看到恶意进程的父进程。

![](https://lessisbetter.site/images/2019-03-top_f.png)


或使用`ps -ef | grep 进程号/程序名`，第3列为父进程。

![](https://lessisbetter.site/images/2019-03-ps_ef.png)
