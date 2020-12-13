title: "算法设计手册第二版第四章课后习题解答"
date: 2015-05-01 18:39:02
tags: ["TADM", "排序", "搜索", "面试"]
catalog: ["算法设计手册习题"]
toc: true
---

> 列出的解答仅为自己的思路，仅供参考，欢迎指出错误。

## 题目Wiki及参考答案

http://www.algorithm.cs.sunysb.edu/algowiki/index.php/Sorting-searching-TADM2E

## 我的解答

### 面试问题

#### 4-45

题目

Given a search string of three words, find the smallest snippet of the document that contains all three of the search words---i.e., the snippet with smallest number of words in it. You are given the index positions where these words occur in the document, such as word1: (1, 4, 5), word2: (3, 9, 10), and word3: (2, 6, 15). Each of the lists are in sorted order, as above.

解答

每个单词出现的位置列表都是有序的，将它们看做是队列。设定`min_len`保存当前最短的片段的长度，初始化为-1.算法步骤如下：

1. 若各队列不空，将各队列最小元素出队,组成三元组
2. 得三元组`(a1, a2, a3)`
3. 求三元组中的最大值`max`，与最小值`min`，则当前片段长度`len = max-min+1`
4. 如果`min_len`为-1或`min_len`大于`len`，`min_len = len`，保存三元组.
5. 删除三元组中最小者`min`，若`min`对应队列不空，取新元素加入到三元组，执行2，若空，退出循环。

##### 变形及分析

变形

假设输入数据不是3个单词的出现位置，而直接是一个字符串数组，那么如何找到满足要求的最小片段？

分析

设`cur`为访问数组的当前位置，3个变量`l1, l2, l3`，代表`cur`前面离`cur`最近的3个单词(w1, w2, w3)的位置。若cur上的单词为3个单词之一，不妨设为w3，则计算w3与w1,w2的距离即`cur-l1+1`和`cur-l2+1`，取小者为`min`，另`min`与`min_len`比较，若min更小，保存`min`，及当前3个单词的位置。当遍历数组结束时，最后的`min_len`与保存的3元素的位置即满足要求的最小片段。



<!--more-->


#### 4-46

题目

You are given 12 coins. One of them is heavier or lighter than the rest. Identify this coin in just three weighings.
Note - weighings are with a balance, where you can have a greater than, equal to, or less than result. You can't do this with a digital scale.

解答

答案Wiki之中给出的3步解决的办法，但是我想不到这个解决方案。下面讨论一下 **二分搜索**在这里的应用。

题目是不知道是偏重还是偏轻的，如果知道偏重或偏轻，用二分搜索可3步解决。这种情况下，可以使用4步二分搜索。

1. 分为3堆，各4个硬币，记为a, b, c.
2. 比较(a, b) 和 (a, c). a, b, c三者中必有一个是偏大或偏小，从这两次比较重可得谁偏大或偏小。
3. 假设得到的是a偏大，再将a进行两次二分搜索，即可的偏大的那枚硬币。
