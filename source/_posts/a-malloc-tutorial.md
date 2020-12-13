title: malloc的故事
date: 2016-04-14 19:05:37
tags: ['malloc']
---


读了张洋的《如何实现一个malloc》和Marwan Burlle的《A Malloc Turorial》，张洋的博文是对Marwan Burlle的理解、翻译和补充，缺失了一些细节。但读了张洋的文章后，再读《A Malloc Turorial》会快很多。


#A Malloc Tutorial

### 讲了什么

1. 什么是malloc
1. 堆的内存模型
1. 如何通过系统调用操纵堆
1. 什么是块、块的数据结构
1. 结构体的本质（虽然变量data属于结构体，但只是想获取数据区的指针，而数据区不属于meta结构体）
1. 如何实现内存对齐
1. 基本的堆管理需要哪些功能/函数
1. 如何创建、选择、分割块
1. 碎片整理（融合块）
1. free要做什么，如何实现
1. 如何实现calloc
1. 何时把块“还给系统”
1. realloc的原理，及优化


<!-- more -->

### 没讲什么
1. 如果free时，不还块会怎样。
1. BLOCK_SIZE大小是如何确定的。
1. 何时，如何分配大块的内存，mmap。
1. realloc分配超大时，就要与mmap交互。
1. 如何对自己编写的内存管理测试。




# 张洋的博文

与《A Malloc Turorial》重复的项不再列出。

### 讲了什么
1. 虚地址与物理地址、缺页处理
1. 进程的内存布局
1. 堆内存的生长方向

### 没讲什么
1. free中删除最后一个节点





# 我的理解和补充

针对《A Malloc Turorial》和张洋的《如何实现一个malloc》做一些解释和补充：

1. malloc的返回值类型是void*代表了，返回的是一个指针，但不确定是什么类型，所以使用前要强制转换。
1. `man malloc`指出：
    1. malloc申请的大小大于MMAP_THRESHOLD(128KB)时，内存的分配会自动使用`mmap。
    1. glibc为了支持多线程应用，使用了互斥信号量，来避免内存管理冲突。
    1. glibc为了提高多线程应用的性能，使用了[Arena allocation](https://en.wikipedia.org/w/index.php?title=Arena_allocation&redirect=no).
    1. 如果malloc，calloc，realloc失败，应当设置`errno`为`ENOMEM`，否则和errno相关的某个库程序会挂掉。
    1. malloc，calloc，realloc崩溃，多半是由heap冲突引起的，比如溢出了分配的chunk(块)，或同一个指针释放两次。
1. [MSDN](https://msdn.microsoft.com/en-us/library/ms810603.aspx)指出：在Windows中，一个进程可以有多个heap，最初的那个被称为默认堆。






### block是什么？

*在glibc中被称为chunk，其中的实现与这里的不太一样，嗯……相似不大。关于chunk更详细的解释就在源码里[时光机](http://repo.or.cz/w/glibc.git/blob/HEAD:/malloc/malloc.c)。*

为了管理堆内存，我们把内存分成很多大块，这些大块大小不一定相等。一个大块分成两部分，一个是块头（block），一个是块尾（data）。块尾就是我们要分配给用户用的空间，即malloc返回的空间。块头存放的是描述信息（meta data），描述的是块尾的信息，比如，它的大小，状态（可用性、读写性），开始位置，为了管理所有的块，让块都连起来，所以还需要链表的指针（如果使用链表管理的话），为了让块头满足内存对齐，我们还需要一些填充位。




块中有个字段叫data，它记录了块尾的起始位置，但实际上它不能占用块头的大小，听起来是不是矛盾，理解了结构体的内存布局，和指针的访问方式，这个问题就迎刃而解了。既然它不属于块头，那为什么把它定义到结构体里呢？
1. 为了方便访问块尾。如果没有data字段，每次访问一个块的块尾大致需要这样：`b + BLOCK_SIZE`，其中b为块头的指针，每次都这样去访问块尾，不是很闹心吗？！（*glic用宏实现*）
2. 为了方便移动指针和计算指针间的距离。内存是按字节分配地址的，而char类型刚好占一个字节，所以把data声明为char，所以在上面做运算可以得到正确的内存地址。b是`s_block`类型的，那么`b + BLOCK_SIZE`也是`s_block`类型的，每次还需要强制转化为`char*`才能移动指针或计算，不是很折腾吗！？


*但这也带来了一个问题：不能使用sizeof获取BLOCK_SIZE。*

sizeof返回的实际占用的内存大小，因此在计算过程中，会执行内存对齐的计算。而在block的定义中，包含了字段data，内存对齐后，会多出一些。所以，需要手动设置BLOCK_SIZE。

至于什么时候建造一个块，不同的管理方案，自然不同。在这里，当前的块不足以满足要求时，就从未用的堆内存中，建造一个块。

另外，你如何实现sizeof呢？
```C
#define sizeof(obj) ((char*)(&obj + 1) - (char*)(&obj))
```

### 为什么BLOCK_SIZE 是 24？

注意BLOCK_SIZE块头的大小，前面提到，data其实不属于block，而又为了能够让block的指针访问它，所以把他加到了block里的定义。block占用的内存空间是size，next，free，padding占用的内存空间，size_t占用8B，指针占用8B，int占用4B，共24B，所以BLOCK_SIZE 是 24。

### 为什么需要padding？不浪费内存吗？

关键还在内存对齐。块头和块尾都需要各自对齐，因此，block的data字段应该在一个对齐单元的开始位置，而不应当处于block所占用的内存区，所以如果block的成员不能刚好对齐，那么需要设置填充位，而padding就是这个填充位。

如果因为不使用padding而造成block和data区有重叠，就更不能愉快的使用内存了。 CPU读内存时一次读对齐的8个字节，data的开始位置，在中间，还怎么愉快的读？一次能读出来的数据，现在要分两次，CPU的时间，远比内存的时间金贵，所以，以空间换时间，这不是浪费。


### 为什么分裂的最低阀值是BLOCK_SIZE+8?

需要BLOCK_SIZE的必要block，剩下的为data区，data区又要字节对齐，在以8字节对齐的机器上，所以剩余的空间至少是BLOCK__SIZE+8。

### free如何确定是已经分配过的指针

块头（meta区）设置一个magic ptr，指向data，根据用户传入的指针p，得到block的指针，如果block->ptr刚好等于p，那么是我们曾经分配的，否则不是。

BLOCK_SIZE应当改为32。

### free碎片如何处理？

改成双向链表，如果相邻的空间为free，那么合并（fusion）。如果不是双链表，我们只能向后合并，造成仍然有大量碎片。


### 代码汇总


<!--
<script src="https://gist.github.com/Shitaibin/8f8d80c45c9c4d23e4a2f264c49349a4.js"></script>
-->

[Gist](https://gist.github.com/Shitaibin/8f8d80c45c9c4d23e4a2f264c49349a4)








# 参考资料

1. 原始资料：[A Malloc Tutorial](
http://www.inf.udec.cl/~leo/Malloc_tutorial.pdf)
1. 张洋博文，如何实现一个malloc：
http://blog.codinglabs.org/articles/a-malloc-tutorial.html
1. 没有A Malloc Tutorial简洁，也是简单示例：《C标准库》
1. glic malloc源码，就算读注释，也会豁然开朗：
[1]. http://repo.or.cz/w/glibc.git/blob/HEAD:/malloc/malloc.h
[2]. http://repo.or.cz/w/glibc.git/blob/HEAD:/malloc/malloc.c
1. malloc和free仍然存在较多问题的，所以另许多程序员头疼，《C语言接口与实现》讲述了如何进一步封装。PS，高级部分使用了arena。
1. Windows堆内存管理：https://msdn.microsoft.com/en-us/library/ms810603.aspx

未看

1. 扩展阅读：
    - Linux 内存管理：内存映射，主要讲mmap： http://blog.jobbole.com/91891/
    - 什么是堆和栈（翻译自SO）：http://blog.jobbole.com/75321/
    - Linux内存点滴，用户进程内存空间。结合将了malloc和操作系统层面的内存管理，但文中也是有错误的，比如L4，L5（访问free的指针）执行，free后，那段空间可能并没有还给OS，因此页表中还存在映射，不会出现段错误，但如果还给了OS，页表中映射被取消，再去访问，才出现错误。：http://blog.jobbole.com/45733/
    - 那些数据结构与算法在Linux内核中的使用：http://blog.jobbole.com/52669/
