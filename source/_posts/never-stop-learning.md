title: 不要限制学习
date: 2016-01-07 20:40:34
tags: ['思考']
---

> 学无止境，莫限制。



在当初学习Python的时候，对于模块，包并没有细看，当然，书籍上写的也不多，它教会了我：

- 如何使用别人的包、模块。
- 如何写一个模块，然后在相同的目录下，使用这个模块中的类与函数。
- 如果不在同目录下，需要将模块在的目录添加到`sys.path`中。


<!--more-->


但我没有学会，如何创建一个自己的包。当时也用不到，因此也没细究。


半月前，我才使用单元测试，单元测试的教程很简单，相当的简单。同样是在同一个目录下，直接`import`即可。

后来，我需要实践单元测试，在一个项目中，**单元测试**应当放到一个单独的目录中，那么，怎么才能让测试文件搜索到被测试的文件呢？我笨，直接修改了`sys.path`。

```python
import sys

sys.path.append("../source_code_dir/")
```

但是这样也不美观呀，并且还提醒PEP8错误，但我也依然将就着用了两周，用到了现在。


前几日就在观察sklearn在Github上的项目，看到他们import的时候，我惊呆了，怎么还可以这样用。

```python
from ..base import BaseEstimator
from ..base import ClassifierMixin
from ..base import RegressorMixin
```

源自文件 [tree.py](https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/tree/tree.py)。


猜测加验证，意思是，从父目录base模块中导入`BaseEstimator`。

我模仿着，在我自己的源文件目录加入了`__init__.py`文件。这样就构成一个包了，但文件是空的，我不知道该如何组织。到好像依然不管用。


今日，对实验的代码进行重构，并且需要把能够复用的工具放到目录`tools`中，进一步实现模块化，再次回到了这个问题，一点一点搜集资料尝试，终于搞定了。

这期间主要是考SO，以及PEP文档，涉及PEP328，PEP338，PEP366。在之前我只知道PEP8，但我不清楚PEP是何物，在不断的积累中，我们一点点的进步，最终汇聚成解决方案。



