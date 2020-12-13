title: 对自定义包的引用
date: 2016-01-09 10:31:52
tags: ["Python", "Package", "单元测试"]
---


> 需求驱动学习。


# 前言

这篇文章是包和单元测试的姊妹篇，内容是如何在自己的工程中导入自定义包，而不出现导入错误。


在文章：[包和单元测试](/2016/01/08/package-unittest-import-error/)中，已经叙述了如何单元测试的导入问题，本质上讲，只要导入的模块在搜索路径中，python就可以发现该模块。也验证了`python`命令会将运行文件所在目录加到`sys.path`中，而`python -m unittest`命令，将运行命令所在目录加入到`sys.path`中。


<!--more-->


# 实验


为了写笔记，该系列实验仍然在Windows上进行，使用Python 2.7。


## 1. 同级目录引用自定义包


#### 目录结构

如下：

```
my_project
	./foo
		./__init__.py
		./bar.py
	./tests
		./__init__.py
		./test_foo.py
		./test_bar.py
	./reference_foo_bar.py
```

- `my_project`是项目目录
- `foo`是包目录
- `tests`是对包的单元测试
- `reference_foo_bar.py`是与包目录同级的工程文件，即同在`my_project `下。


#### 各文件内容

- 两个`__init__.py`文件、`test_foo.py`都为空

- `bar.py`内容：

```python
def dumb_true():
	return True
```

- `test_bar.py`内容如下，但今天的实验中不会用到单元测试。

```
import unittest

from foo import bar

class TestBar(unittest.TestCase):
    def test_bar_true(self):
        self.assertTrue(bar.dumb_true())


if __name__ == "__main__":
    unittest.main()
```

- `reference_foo_bar.py`内容如下：

```python
from foo import bar

if bar.dumb_true():
	print "Hi, we can import foo and use it."
else :
	print "Hi, we also imported foo but something wrong."
```

#### 运行测试

测试命令如下：

```
cd new_project
python reference_foo_bar.py
```

测试结果如下：

```
Hi, we can import foo and use it.
```

太棒了，这是一个好的征兆，我们成功引用了模块`foo.bar`下的`dumb_true`函数，如果不明白原理，请看姊妹篇文章：[包和单元测试](/2016/01/08/package-unittest-import-error/)


## 2. 不同目录引用自定义包

我们使用的标准库和第三方库，都是这种情况，因为这些包都不在我们工程的目录下。本质上讲，他们也都是自定义的，只不过在安装他们的时候，将他们所在的目录，放到了Python的搜索路径中，即`sys.path`。

我们本实验中自定义的包，指我们自己写的工具包，这样我们可以在自己项目中的各处都可以使用。

#### 目录结构

本实验目录结构如下，

```
my_project
	./foo
		./__init__.py
		./bar.py
	./tests
		./__init__.py
		./test_foo.py
		./test_bar.py
	./sub_project
		./reference_foo_bar.py
```

建立新目录`sub_project`，并将`reference_foo_bar.py`移至此目录。

#### 运行测试

```
cd my_project
python subproject\reference_foo_bar.py   #linux 下用： python subproject/reference_foo_bar.py 
```

得错误信息：找不到模块foo


```
Traceback (most recent call last):
  File "sub_project\reference_foo_bar.py", line 1, in <module>
    from foo import bar
ImportError: No module named foo
```

#### 问题来了

当前的搜索路径中包含`...\sub_project`，在本目录下是找不到`foo`的。

怎样才能让Python搜索到，我们自定义的包`foo`呢，

#### 方案1：安装我们自定义的包

模仿我们安装的标准库，与第三方的包，我们可以为`foo`写一个`setup.py`，然后安装它，这样Python永远都能找到它，任何工程也都能导入它，但是我们的包不完善，需要经常修改，并且我们这个包，也仅仅适用于我们当前的工程，所以这并不是一个理想的选择。

打包的教程在此：[有兴趣者，请戳](https://python-packaging.readthedocs.org/en/latest/)。


#### 方案2：在每个文件中，修改`sys.path`

在每个文件中，都将`foo`所在的目录的绝对路径添加到`sys.path`。

```
import sys
sys.path.append(absolute_path)
```

但这样也存在明显的缺陷，丑陋而繁琐。


#### 方案3：使用相对导入

**这是一个馊主意。**

相对导入只在包下才能工作，所以把`my_project`变成包，然后使用相对导入。

在`py_project`下加入`__init__.py`，

修改`reference_foo_bar .py`的内容为：

```
from ..foo import bar

if bar.dumb_true():
	print "Hi, we can import foo and use it."
else :
	print "Hi, we also imported foo but something wrong."
```

运行相对导入要掌握正确的姿势，不然，蛋碎。

**在new_project的父目录运行：**

```
python -m new_project.sub_project.reference_foo_bar  
```

运行成功。。。**但这是一个馊主意，我们总不能把我们所有的项目都搞成包吧。**包可以是项目，但项目不是包。

所以，放弃该方法。



# 参考资料

1. 导入原理：
http://docs.python-guide.org/en/latest/writing/structure/

2. -m 原理
- http://stackoverflow.com/questions/11536764/attempted-relative-import-in-non-package-even-with-init-py
- https://www.quora.com/What-is-the-core-reason-for-this-error-Attempted-relative-import-in-non-package-in-Python




