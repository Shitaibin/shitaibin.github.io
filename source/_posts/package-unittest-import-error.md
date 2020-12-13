title: Python自定义包下不同目录单元测试的导入错误
date: 2016-01-08 21:51:23
tags: ["Python", "Package", "单元测试"]
---

> 需求驱动学习。

# 前言

嗯，很绕口的标题

最近的项目需要把编写的工具放到tools目录，把单元测试放到test目录，造成了不同目录下导入（import）的错误。**基础原因很简单，Python无法找到要导入的文件，而解决这个问题的根本方法，是向`sys.path`中添加搜索路径，如果手动添加，太俗了不是么。**


<!--more-->

所以，本文内容为包（Package）和单元测试的结合笔记。从基本的单元测试，到多目录级的单元测试。单元测试使用PyUnit和nose。


所以，假设你已经有编写过单元测试的基础经历，但nose可以不了解，只需要知道如何安装和运行即可，若不了解，可参考[本页面](https://nose.readthedocs.org/en/latest/)。


# 实验


为了方便些笔记，该实验都是在Window上进行的，实验4为了使用nose，nose部分在Ubuntu上进行。


## 1. 基础导入测试

当前文件结构如下：

```
foo
	./bar.py
	./test_bar.py
```

`bar.py`内容如下：

```python
def dumb_true():
	return True
```

`test_bar.py`内容如下：

```python
import unittest

import bar

```

运行命令：

```shell
cd foo
python test_bar.py
```

**`python`命令会将运行文件所在目录加到`sys.path`中**，因此python可以搜索到模块`bar.py`，所以导入成功。

运行结果：无错误提示， 能导入模块bar。


## 2. 基础单元测试

修改`test_bar.py`内容为：

```python
import unittest

import bar

class TestBar(unittest.TestCase):
    def test_bar_true(self):
        self.assertTrue(bar.dumb_true())


if __name__ == "__main__":
    unittest.main()
```

或者

```python
import unittest

from bar import dumb_true

class TestBar(unittest.TestCase):
    def test_bar_true(self):
        self.assertTrue(dumb_true())


if __name__ == "__main__":
    unittest.main()
```

运行命令：

```
cd foo
python test_bar.py
```

运行结果：单元测试成功，说明可以从`test_bar.py`内调用`bar.dumb_true`函数。




## 3. 不同目录下的单元测试

这起源于构建package后，通常把单元测试放到单独的`tests`目录。**tests在包的外面，和包在相同的目录。**

目录结构如下：

```
my_project
	./foo
		./__init__.py
		./bar.py
	./tests
        ./__init__.py
		./test_foo.py
		./test_bar.py
```

其中，`my_project`是你的项目目录，`foo`是包目录。`tests`目录存放了对工程的单元测试。`foo`目录下的`__init__.py`使得，foo是一个包，也就说目录下有`__init__.py`的目录都是包。

在本实验中单元测试的对象是包`foo`下的`bar.py`文件。

`bar.py`文件内容如实验1与实验2，在本系列实验中，`bar.py`的内容始终保持不变。

`__init__.py`和`test_foo.py`内容全部为空。



修改`test_bar.py`内容为：

```python
import unittest

from foo import bar

class TestBar(unittest.TestCase):
    def test_bar_true(self):
        self.assertTrue(bar.dumb_true())


if __name__ == "__main__":
    unittest.main()
```

运行命令：

```
cd my_project
python -m unittest discover #自动发现测试文件，并测试
```

**unittest的命令行接口，会把当前的路径(运行`python -m unittest`命令的路径，关于该验证，可以看本文末尾)加入到`sys.path`中**，因此Python可以搜索到包`foo`，所以在`test_bar.py`中，可以直接使用

```python
from foo import bar
```

运行结果：单元测试成功，说明可以从`test_bar.py`内调用`foo.bar.dumb_true`函数。

但是当我把`test_bar.py`修改为如下时：直接导入dumb_true函数，出现了一个错误。

```python
import unittest

from foo.bar import dumb_tree  # look here

class TestBar(unittest.TestCase):
    def test_bar_true(self):
        self.assertTrue(dumb_true())  # and here


if __name__ == "__main__":
    unittest.main()
```

错误是：

```
E
======================================================================
ERROR: tests.test_bar (unittest.loader.ModuleImportFailure)
----------------------------------------------------------------------
ImportError: Failed to import test module: tests.test_bar
Traceback (most recent call last):
  File "C:\Anaconda\lib\unittest\loader.py", line 254, in _find_tests
    module = self._get_module_from_name(name)
  File "C:\Anaconda\lib\unittest\loader.py", line 232, in _get_module_from_name
    __import__(name)
  File "C:\Users\Brave\PycharmProjects\learn-python\py2\my_project\tests\test_bar.py", line 3, in <module>
    from foo.bar import dumb_tree
ImportError: cannot import name dumb_tree


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

从`ImportError: cannot import name dumb_tree`可以看出，是我的拼写错误，但是我找了几次才发现这个错误的，错误总是发生在意想不到的地方。

也许你认为这个错误很Silly，但我认为，拼写错误是常见的，但看了几次才发现错误，确实很Silly。

将`dumb_tree`改为`dumb_true`后，单元测试成功。



## 4. 如果my_project是一个包呢

如果我将my_project改为一个包，**tests是包的一部分。**为了理解，我将my_project改为my_package。

目录结构如下：

```
my_package
	./__init__.py
	./foo
		./__init__.py
		./bar.py
	./tests
        ./__init__.py
		./test_foo.py
		./test_bar.py
```

这些my_package下多了一个`./__init__.py`，它变成包了。

现在不修改任何内容，我们重新运行单元测试命令，看会得到什么结果。

**单元测试成功，因为依然遵循了unittest的命令行接口，会把当前的路径加入到`sys.path`中**的原则。


假若我将`test_bar.py`修改为：

```python
import unittest

from my_package.foo.bar import dumb_true  # look here

class TestBar(unittest.TestCase):
    def test_bar_true(self):
        self.assertTrue(dumb_true())  


if __name__ == "__main__":
    unittest.main()
```

我们重新运行单元测试命令，得到了错误：

```
E
======================================================================
ERROR: tests.test_bar (unittest.loader.ModuleImportFailure)
----------------------------------------------------------------------
ImportError: Failed to import test module: tests.test_bar
Traceback (most recent call last):
  File "C:\Anaconda\lib\unittest\loader.py", line 254, in _find_tests
    module = self._get_module_from_name(name)
  File "C:\Anaconda\lib\unittest\loader.py", line 232, in _get_module_from_name
    __import__(name)
  File "C:\Users\Brave\PycharmProjects\learn-python\py2\my_package\tests\test_bar.py", line 3, in <module>
    from my_package.foo.bar import dumb_true  # here
ImportError: No module named my_package.foo.bar


----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)
```

错误显示，没有被命名为`my_package.foo.bar`的模块，说白了，是他没找到这个模块。那么怎么才能成功运行单元测试呢？既然本质是没有在搜索路径中，那么只要能让my_package在搜索路径中即可。

**猜测解决方案1：**在my_package的父目录运行单元测试命令。经测试成功。
**猜测解决方案2：**修改文件，手动将`my_package`的父目录添加到`sys.path`中。

在`test_bar.py`行首添加：

```python
import sys
sys.path.append("../../")  # 相对路径：相对于test_bar.py的路径
```

然后

```
cd tests
python test_bar.py
```

单元测试成功。

#### 为什么我不是这样做呢？

```
cd my_package
python test_bar.py
```

这样本错误依然存在。在实验1中提到，python会搜索文件所在的路径，而不是添加到`sys.path`中，如今，我使用的是相对于`test_bar.py`的路径，必须在tests目录运行，python才会搜索`test_bar.py`的祖父目录，这样才能找到`my_package.foo.bar`。在my_packge目录中运行，my_package的祖父目录找不到`my_package.foo.bar`。

**猜测解决方案3：**使用nose，nose很人性化，它会将运行nosetests的目录，及其子目录下所有测试文件，所引用到的模块，自动加入到`sys.path`中，使用nose通常很少遇到导入问题。*该方案是在Ubuntu下实验的**。



## 附件测试：unittest命令行接口会改变`sys.path`

目录结构如下：

```
outter_dir
	./inner_dir
		./__init__.py
		./test.py
```

`test.py`内容如下：

```python
from pprint import pprint
import sys
pprint(sys.path)
```

**1. python命令:**

```
cd outter_dir
python inner_dir\test.py  # in linux is :python inner_dir/test.py
```

结果中包含的是

```
C:\\Users\\Brave\\PycharmProjects\\learn-python\\py2\\test\\outter_dir\\inner_dir
```

**1. python -m unittest命令:**

```
cd outter_dir
python  -m unittest discover
```

结果中包含的是

```
C:\\Users\\Brave\\PycharmProjects\\learn-python\\py2\\test\\outter_dir
```

本实验证明了，`python`命令会将运行文件所在目录加到`sys.path`中，而`python -m unittest`命令，将运行命令所在目录加入到`sys.path`中。


## 包与单元测试的实验终结

到目前的实验为止，已经知道相同目录下的单元测试，单元测试在包外，单元测试在包内的三种情况，及相应的单元测试方法。

其实，本质上讲，还是要让导入的包处于搜索路径内，所以，无论是如何放置单元测试，一定要让他们在搜索路径内。实验3与实验4是两种常用的目录组织方式，实验4需要稍作处理，sklearn使用的即实验4的组织方式，它的解决方案是修改了顶层`__init__.py`做了处理，但我还没有搞懂，有兴趣的可访问：
https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/__init__.py 。


相关文章：[对自定义包的引用](#)


# 参考资料

1. StackOverflow：http://stackoverflow.com/questions/1896918/running-unittest-with-typical-test-directory-structure
2. A simple instance: https://schettino72.wordpress.com/2008/01/19/11/