title: JOS中具有写时拷贝的fork设计
date: 2016-05-17 13:44:39
tags: ['JOS', 'fork', '操作系统']
---



如果不高清fork的设计思想，是无法实现正确高效的fork。

# JOS中写时拷贝的fork设计

![JOS中写时拷贝的fork设计](http://img.lessisbetter.site/fork-design.jpg)

<!--more-->


-------------------

# 内核态

##### kern/syscall.c/sys_exofork():
1. 分配新的Env结构体
1. 拷贝父进程的trapframe（主要为寄存器信息）
1. 设置eax寄存器为0（eax存放返回值）
1. 返回新进程的eid

##### kern/syscall.c/sys_env_set_pgfault_upcall():
1. 在Env结构体中设置upcall，本质：
```
env->env_pgfault_upcall = _pgfault_upcall
```

##### kern/trap.c/pgfault_handler():
1. 内核缺页，panic
1. 如果设置了`env_pgfault_upcall`，则调用`_pgfault_upcall`。


---------------------------------------

# 用户态

##### lib/fork.c/fork():
1. set_pgfault_handler()，设置用户态异常栈，以及设置用户态异常入口`_pgfault_upcall`
1. sys_exo_fork()，创建子进程
1. 子进程返回，父进程继续
1. duppage()，复制父进程地址空间到子进程，实现共享内存，设置COW
1. sys_env_set_pgfault_upcall()，为子进程设置户态异常入口`_pgfault_upcall`
1. sys_env_set_status()，修改子进程状态

##### lib/pgfault.c/set_pgfault_handler():
1. 如果没有设置用户态异常栈（异常处理函数运行的地方），设置用户态异常栈
1. 设置用户态异常入口`_pgfault_upcall`
1. 只会被父进程调用

##### lib/fork.c/duppage():
1. 把虚地址页映射到制定进程的地址空间

##### lib/pfentry.S/_pgfault_upcall
1. 调用lib/fork.c/pgfault()

##### lib/fork.c/pgfault():
1. 如果页异常的页是COW属性
1. 创建临时页，属性可读写，原数据拷贝到临时页，临时页映射到页异常进程的该页

