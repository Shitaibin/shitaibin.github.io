---
title: 算法设计手册第二版第六章课后习题解答
date: 2015-05-7 20:36:44
tags: ['TADM', '面试']
---


> 列出的解答仅为自己的思路，仅供参考，欢迎指出错误。

题目Wiki及参考答案
-----------

[http://www.algorithm.cs.sunysb.edu/algowiki/index.php/Weighted-graphs-TADM2E](http://www.algorithm.cs.sunysb.edu/algowiki/index.php/Weighted-graphs-TADM2E)

该页面答案，也是由用户编辑的，不确定是完全的正确。

MST
---

### 6-2 最短路径与MST

题目

Is the path between two vertices in a minimum spanning tree necessarily a shortest path between the two vertices in the full graph? Give a proof or a counterexample.

<!--more-->

解答

MST中两点间的路径不是该两点在整个图中的最短路径。

**反例：**使用习题5-1的图，使用Kruskal得到的MST是：


路径A->I：A->D->G->J->I。路径长度为13，而在整个图中，路劲为A->I，长度为9。结果已显然。

### 6-3 最短路径与MST

题目

Assume that all edges in the graph have distinct edge weights (i.e., no pair of edges have the same weight). Is the path between a pair of vertices in a minimum spanning tree necessarily a shortest path between the two vertices in the full graph? Give a proof or a counterexample.

解答

否。


考虑B到D的路径，在图中路径长度为6，而在MST中路径长度为7。

### 6-4 Prim和Kruskal得到MST是否相同

题目

Can Prim’s and Kruskal’s algorithm yield different minimum spanning trees? Explain why or why not.

解答

在6-1中，Prim与Kruskal就可以产生不同MST。只有当MST本身唯一的时候，由Prim与Kruskal得到的MST才是相同的。

MST唯一的条件：所有边的权值都不相同。

### 6-5 Prim和Kruskal边权值是否可为负

题目

Does either Prim’s and Kruskal’s algorithm work if there are negative edge weights? Explain why or why not.

解答

思考得到的想法和Wiki页面的想法是类似的，但我还不会严谨的证明。

每条边都会被访问一次，并且只是比较边的大小，既然是仅仅比较大小，那么与正负是没有关系的。不会像Dijkstra那样对边的权值有加法操作，会影响整体的结果。

### 6-6 添加边，获得新的MST

题目

Suppose we are given the minimum spanning tree T of a given graph G (with n vertices and m edges) and a new edge e=(u,v) of weight w that we will add to G. Give an efficient algorithm to find the minimum spanning tree of the graph G+e. Your algorithm should run in O(n) time to receive full credit.

解答

向MST中添加一条边会怎样？对，出现环路。如果增加的边的权值w比从u到v的路径上最大边的权值要小，那么就需要删除掉该最大的边。

从u开始对MST进行DFS可以得到最大的边，时间O(n)。

Google了这道题目，得到了一份考卷，对该问题进行了扩展。题目及答案如下：

Suppose you are given a graph G=(V,E) with edge weights w(e) and a minimum spanning tree T of G. Now, suppose a new edge {u,v} is added to G. Describe (in words) a method for determining if T is still a minimum spanning tree for G.

_Examine the path in T from u to v. If any vertex on this path has weight larger than that of the new edge, then T is no longer an MST. We can modify T to obtain a new MST by removing the max weight edge on this path and replacing it with the new edge._

Explain how your method can be implemented to run in O(n) time if both G and T are provided as instances of the wgraph data structure.

_Using the wgraph for T, we can do a recursive tree traversal in T, starting at vertex u. Once the traversal reaches v, we “unwind” the recursion, and as we do so, we look for the max weight edge along the u,v path. The runtime for a tree traversal is O(n) and the required changes to T can be done in constant time._

Suppose that instead of a single edge, you are given a set of k new edges to add to G. For small enough k it makes sense to apply your algorithm repeatedly in order to update the MST, but if k is “too large”, it’s more efficient to re-compute the MST from scratch. How big does k have to be (as a function of m and n) in order for this to be a better choice? Assume that the MST is computed using Prim’s algorithm with a d-heap, where d=2.

_When d=2, the running time for Prim’s algorithm is O(m log n), so if kn grows faster than this, it makes sense to recompute from scratch. So, if k>(m/n) log n, it makes sense to recompute the MST._

### 6-7 改变权值，MST是否改变，最短路径是否改变

题目

(a) Let T be a minimum spanning tree of a weighted graph G. Construct a new graph G′ by adding a weight of k to every edge of G. Do the edges of T form a minimum spanning tree of G′? Prove the statement or give a counterexample.

(b) Let P={s,…,t} describe a shortest weighted path between vertices s and t of a weighted graph G. Construct a new graph G′ by adding a weight of k to every edge of G. Does P describe a shortest path from s to t in G′? Prove the statement or give a counterexample.

解答

(a) 是的。

6-5中提到了，MST与权值的具体数值无关，只要能比较边的大小即可。每条边的权值都增加了k，它们依然是可以比较大小的，并且它们的相对大小并没有变化，因此T会是G’的一个MST。

_这点我同答案wiki页面是不同的，那里面的回答是“可能是”。_

(b) 答案不确定。

Dijkstra算法：只能处理非负权值的边。  
Floyd-Warshall算法：能处理包含负边的图，但不能处理存在负边构成环的图。

1. 只要不存在负权值的边，答案是肯定的，依然是P。
2. 存在负边时，我不确定。

### 6-8 已最小的代价改变MST

题目

Devise and analyze an algorithm that takes a weighted graph G and finds the smallest change in the cost to a non-MST edge that would cause a change in the minimum spanning tree of G. Your algorithm must be correct and run in polynomial time.

解答

polynomial time：2O(log n), eg. n, nlogn, n10。

什么样的边会影响最小生成树？

在图的某个环中，除了这条边e，其他边都是MST中的边，那么只要e小于其中任何一条边的值就可以改变MST。

再详细一点，边e是环中最大的边，边x是该环剩下的边在MST中最大的边。只要使得边e的值略小于边x的值即可，这样可以保证最小的代价改变MST。

以6-2中的图为例，边(I,G)、(E,G)是符合条件的，减1即可，其他非MST边减的都大于1才能改变MST。

假设n个点，m条边，则非MST边有(m-n+1)，根据MST找到每条边所在换，并计算最小变化需要O(n)，则时间复杂度为O(n(m-n))。

_我相信这不是最好的解决方案。_

### 6-9 最小连通子集

题目

Consider the problem of finding a minimum weight connected subset T of edges from a weighted connected graph G. The weight of T is the sum of all the edge weights in T.

(a) Why is this problem not just the minimum spanning tree problem? Hint: think negative weight edges.  
(b) Give an efficient algorithm to compute the minimum weight connected subset T.

解答

若保证子图是连通的，那么T至少包含MST。向MST上添加一条边会怎样？

1. 正边：增加T的权值，不要。
2. 0：不改变权值，不要。
3. 负边：减小T的权值，要。

因此，所有的负边都不能放过。问题来了，是先生成MST，再把所有的负边添加到MST中构成T，还是先得到所有的负边，再使用Kruskal让图连通得到T呢？

无论哪种方法，**最后T的权值都是一样的**。

1. 前面证明了，在MST的边与非MST边e构成的环中，边e之所以不在MST中，就是因为它是环里面最大的，虽然现在边e的权值是负的，但仍然是最大的，因此把e添加进来，不会造成要删除其他MST边。最后得到的T的权值必然是最小的。
2. 先得所有负边，在Kruskal得到的T的权值必然也是最小的，因为它一直都在选最小的边。

### 6-10 feedback-edge set

题目

Let G=(V,E) be an undirected graph. A set F⊆E of edges is called a feedback-edge set if every cycle of G has at least one edge in F.

(a) Suppose that G is unweighted. Design an efficient algorithm to find a minimum-size feedback-edge set.  
(b) Suppose that G is a weighted undirected graph with positive edge weights. Design an efficient algorithm to find a minimum-weight feedback-edge set.

解答

(a)

1. 记录每条边属于哪些环。
2. 拥有最多环的那条边e加入F。
3. 更新每条边，删除它们e中拥有的边，此时e拥有的边变为了0个。
4. 重复2-3，直到所有边不拥有环。

时间复杂度嘛，看样子还是不小的。要找到么一个环，然后标记每条边在几个环内，还要排序，删除，不是一个高效的方案。

(b)

并查集
---

### 6-12 设计并查集及算法

题目

Devise an efficient data structure to handle the following operations on a weighted directed graph:

(a) Merge two given components.  
(b) Locate which component contains a given vertex v.  
(c) Retrieve a minimum edge from a given component.

解答

在课本的并查集操作，得到的并查集是这样的。  

要想确定两个顶点在不在一个集合内，需要找到代表这个集合的根节点，find的效率并不高，他需要多次递归才能得到根节点。

如果能提高find的效率，并查集的操作也将提高很多。常见的做法是，[路径压缩](https://en.wikipedia.org/wiki/Disjoint-set_data_structure)

```
int find(set_union *s, int x)  
{  
 if (s->p\[x\] != x)  
 s->p\[x\] = find(s, s->p\[x\]);  
  
 return s->p\[x\];  
}  
```

最短路径
----

### 6-14 单目的最短路径

题目

The _single-destination shortest path_ problem for a **directed graph** seeks the shortest path from every vertex to a specified vertex v. Give an efficient algorithm to solve the single-destination shortest paths problem.

解答

如果是无向图的话，执行Dijkstra算法即可，然后倒转所有的路径。但是，题目指明是基于有向图的问题。

另外，Kruskal算法是All-Pairs最短路径，如果想到的算法时间复杂度大于O(n3)，那还不如直接使用Kruskal。


如上图,假设要求从s到t的最短路径，并且已经求得c1,c2,c3到t的最短路径，那么s到t的最短路径应当为 `W[s,t] = min(W[s,c1]+W[c1,t], W[s,c2]+W[c2,t], W[s,c3]+W[c3,t])`。

自然而然，应当想到了递归解法。Oh，接下来貌似你要考虑一下这些问题：

1. 从哪个点开始递归，可以向dfs中那样使用for循环
2. 怎么处理环


再回首想想：**图的解决方案，是对图进行建模，使用已有的算法，而不是设计新的算法**

使用Dijkstra算法。反向建立图G’ = (V’,E’), V = V’, {u,v}∈E, {v,u}属于E’。对G’使用Dijkstra算法得到从v到任意节点的最短路径，倒转所有路径即从所有节点到v的最短路径。

### 6-16 MST与SPT

题目

Answer all of the following:

(a) Give an example of a weighted connected graph G=(V,E) and a vertex v, such that the minimum spanning tree of G is the same as the shortest-path spanning tree rooted at v.  
(b) Give an example of a weighted connected directed graph G=(V,E) and a vertex v, such that the _minimum-cost spanning tree_ of G is very different from the shortest-path spanning tree rooted at v.  
(c) Can the two trees be completely disjointed?

解答

(a) 图G、MST、SP构成的树都是下图：


(b) minimum-cost spanning tree就是MST，看到这个刚开始还觉得这是不是一个新东西。


(c) What is ‘completely disjointed’?

### 6-17 MST的边与SP的边

题目

Either prove the following or give a counterexample:

(a) Is the path between a pair of vertices in a minimum spanning tree of an undirected graph necessarily the shortest (minimum weight) path?  
(b) Suppose that the minimum spanning tree of the graph is unique. Is the path between a pair of vertices in a minimum spanning tree of an undirected graph necessarily the shortest (minimum weight) path?

解答

(a) 否。见上题(b)。边(A,C)就不在最短路径中。

(b) 否。见上题(b)。图G的MST是唯一的，那么现在又回到了题(a)。

### 6-18 顶点有权值

题目

In certain graph problems, vertices have can have weights instead of or in addition to the weights of edges. Let Cv be the cost of vertex v, and C(x,y) the cost of the edge (x,y). This problem is concerned with finding the cheapest path between vertices a and b in a graph G. The cost of a path is the sum of the costs of the edges and vertices encountered on the path.

(a) Suppose that each edge in the graph has a weight of zero (while non-edges have a cost of ∞). Assume that Cv=1 for all vertices 1≤v≤n (i.e., all vertices have the same cost). Give an efficient algorithm to find the cheapest path from a to b and its time complexity.  
(b) Now suppose that the vertex costs are not constant (but are all positive) and the edge costs remain as above. Give an efficient algorithm to find the cheapest path from a to b and its time complexity.  
(c) Now suppose that both the edge and vertex costs are not constant (but are all positive). Give an efficient algorithm to find the cheapest path from a to b and its time complexity.

解答

> 6.3.1 Stop and Think  
> Set the weight of each directed edge{i,j} in the input graph to the cost of vertex j. Dijkstra’s algorithm now does the job.

我的解决方案：

设边{i,j}的权值为W\[i,j\]。则将其改为W\[i,j\] = W\[i,j\] + Cj，然后使用Dijkstra。

W\[i,j\]初始化：  
(a) W\[i,j\] = 0.  
(b) W\[i,j\] = k(常数).  
(c) W\[i,j\] 原本值。

### 6-19 最小有向环

题目

Let G be a weighted directed graph with n vertices and m edges, where all edges have positive weight. A directed cycle is a directed path that starts and ends at the same vertex and contains at least one edge. Give an O(n3) algorithm to find a directed cycle in G of minimum total weight. Partial credit will be given for an O(n2m) algorithm.

解答

如果对Floyd的过程比较了解，这个真的很简单，因为Floyd得到的是All-pairs，包括了i到i的最短距离，即`g->weight[i][i]`。遍历便可的最小值。

我在做Floyd的时候，对有向图做了测试，[github传送门](https://github.com/Shitaibin/The-Algorithm-Design-Manual/blob/master/floyd.c)。

### 6-20 最长路径

题目

Can we modify Dijkstra’s algorithm to solve the single-source longest path problem by changing {\\em minimum} to maximum? If so, then prove your algorithm correct. If not, then provide a counterexample.

解答

Longest path is basically the _Hamiltonian Cycle problem_ or the _Traveling Salesman Problem_, and it is NP-hard. So no, and if you find a way, then P=NP.

The existence or non-existence of an algorithm to find the largest path, in polynomial time, is essentially part of the largest open problem in all of CS (and probably in math).

[参考资料1](http://cs.stackexchange.com/questions/17980/is-it-possible-to-modify-dijkstra-algorithm-in-order-to-get-the-longest-path)  
[参考资料2](http://cs.stackexchange.com/questions/10732/how-to-prove-np-hardness-of-a-longest-path-problem)

### 6-21 SSSP 线性时间

题目

Let G=(V,E) be a weighted acyclic directed graph with possibly negative edge weights. Design a linear-time algorithm to solve the single-source shortest-path problem from a given source v.

解答

1. 使用拓扑排序：O(E+V)  
    [参考资料](http://en.wikipedia.org/wiki/Topological_sorting#Application_to_shortest_path_finding)
    
2. Google: linear-time algorithm to solve the single-source shortest-path, 会搜到几篇论文，解决方案是修改Dijkstra算法。
    

### 6-22 长度为k的最短路径

题目

Let G=(V,E) be a directed weighted graph such that all the weights are positive. Let v and w be two vertices in G and k≤|V| be an integer. Design an algorithm to find the shortest path from v to w that contains exactly k edges. Note that the path need not be simple.

解答

注意最后一句：意味着图可能存在环的，并且路径中也可以存在环。

比如图为：A<->B，v=A, w=B.  
k=1时，A->B;  
k=2时，不存在。  
k=3时，A->B->A->B。