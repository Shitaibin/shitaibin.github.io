---
title: 算法设计手册第二版第七章课后习题解答
date: 2015-05-7 20:36:44
tags: ['TADM', '面试']
---


> 列出的解答仅为自己的思路，仅供参考，欢迎指出错误。

题目Wiki及参考答案
-----------

[http://www.algorithm.cs.sunysb.edu/algowiki/index.php/Search-TADM2E](http://www.algorithm.cs.sunysb.edu/algowiki/index.php/Search-TADM2E)

该页面答案，也是由用户编辑的，不确定是完全的正确。

Backtracking
------------

### 7-1 permutations

题目

A derangement is a permutation p of {1,…,n} such that no item is in its proper position, i.e. pi≠i for all 1≤i≤n. derangement Write an efficient backtracking program with pruning that constructs all the derangements of n items.

<!--more-->

解答

剪枝就是构建合适的候选者。只需增加一个限制条件`i != k`。[完整代码](https://github.com/Shitaibin/The-Algorithm-Design-Manual/blob/master/7.11/7_1_permutations.c)。

```
void construct_candidates(int a\[\], int k, int n, int c\[\], int *ncandidates)  
{  
 int i;  
 bool in_perm\[NMAX\];  
  
 for (i=1; i<NMAX; ++i) in_perm\[i\] = FALSE;  
 for (i=1; i<k; ++i) in_perm\[a\[i\]\] = TRUE;  
 *ncandidates = 0;  
 for (i=1; i<=n; ++i)  
 if (i != k && in_perm\[i\] == FALSE) // pruning  
 c\[(*ncandidates)++\] = i;  
}  
```

### 7-2 Multisets

题目

Multisets are allowed to have repeated elements. A multiset of n items may thus have fewer than n! distinct permutations. For example, {1,1,2,2} has only six different permutations: {1,1,2,2}, {1,2,1,2}, {1,2,2,1}, {2,1,1,2}, {2,1,2,1}, and {2,2,1,1}. multiset Design and implement an efficient algorithm for constructing all permutations of a multiset.

解答

在每次选取候选者的时候，重复的候选者，只选择一个，就不会出现同一个数字在同一个位置，出现多次。
```
mulset\[NMAX\]; // Multisets  
a\[\]; // save the indexes of the number in mulset  
void construct_candidates(int a\[\], int k, int n, int c\[\], int *ncandidates)  
{  
 int i;  
 bool in_perm\[NMAX\]; // save the indexes of the number in mulset  
 int uniset\[NMAX\]; // save the first indexes of a number in mulset  
  
 for (i=1; i<NMAX; ++i) in_perm\[i\] = FALSE;  
 for (i=1; i<k; ++i) in_perm\[a\[i\]\] = TRUE;  
  
 get\_unique\_set(in_perm, uniset);   
  
 *ncandidates = 0;  
 for (i=1; i<=n; ++i)  
 if (i != k && uniset\[i\] == FALSE) // pruning  
 c\[(*ncandidates)++\] = i;  
}  
```
### 7-3 图的同构

题目

Design and implement an algorithm for testing whether two graphs are isomorphic to each other. The graph isomorphism problem is discussed in graph-isomorphism. With proper pruning, graphs on hundreds of vertices can be tested reliably.

解答

NP问题。

方法就是进行验证。

以无向图举例。

1. 顶点数量相同。
2. 在图G中任选一点，依次与图H中的点进行匹配。
3. 那么总的配对方式供NxN个。
4. 验证方式是：图G中有的边，图H中也有，图H中有的边图G中也有。

剪枝：仅将H中与G中当前顶点度相同的顶点加入到候选者列表。

### 7-4

题目

Anagrams are rearrangements of the letters of a word or phrase into a different word or phrase. Sometimes the results are quite striking. For example, “MANY VOTED BUSH RETIRED” is an anagram of “TUESDAY NOVEMBER THIRD”, which correctly predicted the result of the 1992 U.S. presidential election. Design and implement an algorithm for finding anagrams using combinatorial search and a dictionary.

解答

1. 根据输入字符串，拆解得到一个字符池。池中字母保持字典顺序。
2. 按照课本构造子集的方式，得到一个子集，即一个“单词”，判断该单词在不在词典中？  
    2.1 在，则从剩下的字符池继续构建单词，直到池为空，得到一个solution；  
    2.2 否，构建下一个单词。