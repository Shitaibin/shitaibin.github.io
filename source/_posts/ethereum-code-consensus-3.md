---
title: 以太坊源码分析：共识（3）PoW
date: 2018-06-22 20:16:01
tags: ['以太坊', '区块链']
---

# 前言

Ethash实现了PoW，PoW的精妙在于通过一个随机数确定，矿工确实做了大量的工作，并且是没有办法作弊的。接下来将介绍：

1. Ethash的挖矿本质。
2. Ethash是如何挖矿的。
3. 如何验证Ethash的随机数。

<!--more-->

# Ethash的挖矿本质

挖矿的本质是找到一个随机数，证明自己做了很多工作（计算）。在Ethash中，该随机数称为`Nonce`，它需要满足一个公式：

`Rand(hash, nonce) ≤ MaxValue / Difficulty`

其中，
- hash：去除区块头中Nonce、MixDigest生成的哈希值，见`HashNoNonce()`。
- nonce：待寻找的符合条件的随机数。
- MaxValue：固定值2^256，生成的哈希值的最大取值。
- Difficulty：挖矿难度。
- Rand()：使用hash和nonce生成一个哈希值，这其中包含了很多哈希运算。

以上参数中，在得到区块头的hash之后，只有nonce是未知的。

**公式的含义是，使用hash和nonce生成的哈希值必须落在合法的区间。**利用下图介绍一下，Rand()函数结果取值范围是[0, MaxValue]，但只有计算出的哈希值在[0, MaxValue / Difficulty]内，才是符合条件的哈希值，进而该Nonce才是符合条件的，否则只能再去寻找下一个Nonce。

![随机值的判断](http://img.lessisbetter.site/2018-06-22-121846.jpg-own)

以太坊可以通过调整Difficulty来调节当前挖矿的难度，Difficulty越大，挖矿的难度越大。当Difficulty越大时， `MaxValue / Difficulty`越小，合法的哈希值范围越小，造成挖矿难度增加。

哈希值满足条件的概率是 `p = (MaxValue / Difficulty) / MaxValue = 1 / Difficulty`，矿工需要进行`1 / p = Difficulty`次的判断，才有可能找到一个符合条件的Nonce，当前以太坊难度为3241847139727150。

为什么PoW需要做那么多的运算，而不是通过公式反推，计算出满足条件的结果(Nonce)？

PoW可以表示为许多数学公式的合集，每次运算的入参：前一个区块头的哈希，当前高度的DataSet，目标值Nonce，这些数学公式都是哈希函数，哈希函数的特性就是不可逆性，不能通过摘要获得输入数据。虽然，前一个区块头的哈希和当前高度的DataSet是固定的，但由于哈希函数的不可逆性，依然无法倒推出Nonce，只能随机的产生Nonce，或累加Nonce，并不断的重试，直到找到符合条件的Nonce。

# 如何挖矿

Ethash挖矿的主要思想是，开启多个线程去寻找符合条件的Nonce，给每个线程分配一个随机数，作为本线程的Nonce的初始值，然后每个线程判断当前的Nonce是否符合上面的公式，如果不符合，则把Nonce加1，再次进行判断，这样不定的迭代下去，直到找到一个符合条件的Nonce，或者挖矿被叫停。

接下来介绍挖矿的几个主要函数的实现，它们是：

1. 挖矿的入口Seal函数。
2. 挖矿函数mine函数。
3. 挖矿需要的数据cache和dataset。
4. Rand()函数的实现hashimotoFull和hashimoto。

## 挖矿入口Seal()

`Seal`是引擎的挖矿入口函数，它是管理岗位，负责管理挖矿的线程。它发起多个线程执行`Ethash.mine`进行并行挖矿，当要更新或者停止的时候，重新启动或停止这些线程。 
![Seal函数：发布挖矿任务](http://img.lessisbetter.site/2018-06-22-121843.jpg-own)

## 挖矿函数mine()

`mine`函数负责挖矿。`Seal`在启动每一个`mine`的时候，给它分配了一个`seed`，`mine`会把它作为`Nonce`的初始值，然后生成本高度使用的`dataset`，然后把`dataset, hash, nonce`传递给`hashimotoFull`函数，这个函数可以认为是原理介绍中的`Rand`随机函数，他会生成哈希值`Result`，当`Result <= Target`的时候，说明哈希值落在符合条件的区间了，**mine找到了符合条件的Nonce**，使用Digest和nonce组成新的区块后，发送给`Seal`，否则验证下一个Nonce是否是符合条件的。

![Miner函数](http://img.lessisbetter.site/2018-06-22-121841.jpg-own)

## 挖矿需要的数据cache和dataset

`dataset`用来生成`Result`，而`cache`用来生成`dataset`。至于如何使用`dataset`生成`Result`在`hashimoto()`中讲述，本节介绍如何生成dataset。

dataset和cache中存放的都是伪随机数，每个epoch的区块使用相同的cache和dataset，并且dataset需要暂用大量的内存。刚开始时cache是16MB，dataset是1GB，但每个epoch它们就会增大一次，它们的大小分别定义在`datasetSizes`和`cacheSizes`，dataset每次增长8MB，最大能达到16GB，所以挖矿的节点必须有足够大的内存。

使用cache生成dataset。使用cache的部分数据，进行哈希和异或运算，就能生成一组dataset的item，比如下图中的cache中黄色块，能生成dataset中的黄色块，最后把这些Item拼起来就生成了完整的Dataset，完成该功能的函数是`generateDataset`。

![cache和Dataset](http://img.lessisbetter.site/2018-06-22-121842.jpg-own)

`dataset.generate()`是dataset的生成函数，该函数只执行一次，先使用`generateCache()`生成cache，再将cache作为`generateDataset()`的入参生成dataset，其中需要重点关注的是`generateDatasetItem()`，该函数是根据部分cache，生成一组dataset item，验证PoW的nonce的时候，也需要使用该函数。

![Dataset的生成](http://img.lessisbetter.site/2018-06-22-121840.jpg-own)

## Rand()的实现hashimotoFull()和hashimoto()

`hashimotoFull`功能是使用dataset、hash和nonce生成Digest和Result。它创建一个获取dataset部分数据的lookup函数，该函数能够返回连续的64字节dataset中的数据，然后把lookup函数、hash和nonce传递给`hashimoto`。 
![hashimotoFull](http://img.lessisbetter.site/2018-06-22-121839.jpg-own)

`hashimoto`的功能是根据hash和nonce，以及lookup函数生成`Digest`和`Result`，lookup函数能够返回64字节的数据就行。它把hash和nonce合成种子，然后根据种子生成混合的数据mix，然后进入一个循环，使用mix和seed获得dataset的行号，使用lookup获取指定行的数据，然后把数据混合到mix中，混合的方式是使用**哈希和异或运算**，循环结束后再使用哈希和异或函数把mix压缩为64字节，把mix转为小端模式就得到了Digest，把seed和mix进行hash运算得到Result。

![hashimoto](http://img.lessisbetter.site/2018-06-22-121838.jpg-own)

# 如何验证

PoW的验证是证明出块人确实进行了大量的哈希计算。Ethash验证区块头中的`Nonce`和`MixDigest`是否合法，如果验证通过，则认为出块人确实进行了大量的哈希运算。验证方式是确定区块头中的`Nonce`是否符合公式，并且区块头中的`MixDigest`是否与使用此`Nonce`计算出的是否相同。

验证与挖矿相比，简直是毫不费力，因为：

1. 时间节省。验证只进行1次`hashimoto`运算，而挖矿进行大约Difficulty次。
2. 空间节省。验证只需要cache，不需要dataset，也就不需要计算庞大的dataset，因此不挖矿的验证节点，不需要很高的配置。

接下来介绍验证函数`VerifySeal()`，以及根据cache生成`Digest`和`Result`的`hashimotoLight()`。

## 验证函数VerifySeal

`Ethash.VerifySeal`实现PoW验证功能。首先先判断区块中的Difficulty是否匹配，然后生成（获取）当前区块高度的cache，把cache和nonce传递给`hashimotoLight`，该函数能根据`cache, hash, nonce`生成Digest和Result，然后校验Digest是否匹配以及Result是否符合条件。

![VerifySeal](http://img.lessisbetter.site/2018-06-22-121844.jpg-own)

## hashimotoLight函数

`hashimotoLight`使用`cache, hash, nonce`生成`Digest`和`Result`。**生成Digest和Result只需要部分的dataset数据，而这些部分dataset数据时可以通过cache生成，因此也就不需要完整的dataset**。它把`generateDatasetItem`函数封装成了获取部分dataset数据的lookup函数，然后传递给`hashimoto`计算出Digest和Result。

![hashimotoLight](http://img.lessisbetter.site/2018-06-22-121845.jpg-own)

# FAQ

- Q：每30000个块使用同一个dataset，那可以提前挖出一些合法的Nonce？ 
  A：不行。提前挖去Nonce，意味着还不知道区块头的hash，因此无法生成合法的Nonce。
- Q：能否根据符合条件的哈希值，反推出Nonce呢？ 
  A：不行。因为哈希运算具有不可逆性，不能根据摘要反推出明文，同理根据哈希值也无法推出Nonce。


> 1. 如果这篇文章对你有帮助，不妨关注下我的Github，有文章会收到通知。
> 2. 本文作者：[大彬](http://lessisbetter.site/about/)
> 3. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2018/06/22/ethereum-code-consensus-3/](http://lessisbetter.site/2018/06/22/ethereum-code-consensus-3/)