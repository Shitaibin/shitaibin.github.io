title: Python单元测试实践
date: 2015-12-22 11:09:25
tags: ['Python', '单元测试']
---

> 本文主要记录使用Python单元测试时，遇到的问题及解决办法。随着使用的增多，将会遇到更多的问题，与更多的单元测试方法。

常用的有：

```Python
assertTrue, assertFalse
assertEqual
```


<!--more-->


### assertRaises引发的错误

某天，我在程序中设置了Raise异常，如何让单元测试捕获异常呢？当然首先查了[Python文档](https://docs.python.org/2/library/unittest.html#unittest.TestCase.assertRaises)，但结果一运行就出现了错误，无法捕获异常，然后求助了[StackOverflow](http://stackoverflow.com/questions/6103825/how-to-properly-use-unit-testings-assertraises-with-nonetype-objects)，呵呵一笑，仍然没有解决，然后求助Google，得到一篇文章：[Python/Unittest: assertRaises raises Error ](http://www.lengrand.fr/2011/12/pythonunittest-assertraises-raises-error/)，**问题描述如博文一致，只是出错问题不同罢了**，也按其中的方法解决了，但是没有给出为何这样使用？

解决方法如下：

```Python
self.assertRaises(TypeError, lambda: test_function(params))
```

### 包的单元测试导入错误

请看文章[Python自定义包下不同目录单元测试的导入错误](/2016/01/08/package-unittest-import-error/)

