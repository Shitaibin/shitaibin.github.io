---
title: 利用JSONPath提取Kubernetes资源信息
date: 2020-11-16 16:52:00
tags: ['Kubernetes']
---


### JSONPath基础

XML有一个非常强大的解析工具是XPath，用于提取XML中的内容。之后也出现了一种高效提取JSON内容的工具，它被称为JSONPath。

JSONPath现在有很多不同的实现，不同的实现支持的提取语法略有不同，比如Goessner的JSONPath如下：

![goessner jsonpath](http://img.lessisbetter.site/2020-11-goessner-jsonpath.png)



[fastjson的JSONPath](https://github.com/alibaba/fastjson/wiki/JSONPath#3-%E6%94%AF%E6%8C%81%E8%AF%AD%E6%B3%95)支持的更加丰富。



示例JSON内容：

```json
{
    "store": {
        "book": [
            {
                "category": "reference",
                "author": "Nigel Rees",
                "title": "Sayings of the Century",
                "price": 8.95
            },
            {
                "category": "fiction",
                "author": "Evelyn Waugh",
                "title": "Sword of Honour",
                "price": 12.99
            },
            {
                "category": "fiction",
                "author": "Herman Melville",
                "title": "Moby Dick",
                "isbn": "0-553-21311-3",
                "price": 8.99
            },
            {
                "category": "fiction",
                "author": "J. R. R. Tolkien",
                "title": "The Lord of the Rings",
                "isbn": "0-395-19395-8",
                "price": 22.99
            }
        ],
        "bicycle": {
            "color": "red",
            "price": 19.95
        }
    },
    "expensive": 10
}
```



以例子讲解几个最常用的语法：



| 语法              | 语法含义                                                                                   | 例子                                        | 例子含义                                                                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| $                 | JSON内容的根对象，所有的JSONPath都是以`$`为开头。                                          | `$`                                         | [JSON内容本身](http://jsonpath.herokuapp.com/?path=$)。                                                                                   |
| .                 | 后面跟子对象。                                                                             | `$.expensive`                               | [提取根对象的expensive字段的值](http://jsonpath.herokuapp.com/?path=$.expensive)。                                                        |
| ..                | 递归扫描子对象。                                                                           | `$..price`                                  | [提取对象中所有price字段的值，结果会包含所有book和bicycle中的价格](http://jsonpath.herokuapp.com/?path=$..price)。                        |
| [num]             | 以下标访问数组。语法类似Python，num为负数时，代表倒数。                                    | `$.store.book[0]`                           | [获取第一本书](http://jsonpath.herokuapp.com/?path=$.store.book[0])。                                                                     |
| [num1, num2,num3] | 以下标获取数据中多个数据。                                                                 | `$.store.book[0,2]`                         | [获取第1、3本书](http://jsonpath.herokuapp.com/?path=$.store.book[0,2])。                                                                 |
| [start:end]       | 获取数组区间[start, end)的数据。                                                           | `$.store.book[0:2]`                         | [获取前2本书](http://jsonpath.herokuapp.com/?path=$.store.book[0:2])。                                                                    |
| [start:end:step]  | 获取数组区间[start, end)的数据，但以step为步长提取数据。**但不是所有JSONPath实现都支持**。 | `$.store.book[0:3:2]`                       | 获取第1~3本书，以步长为2提取，也即是第1、3本书。                                                                                          |
| [*]               | 通配符，匹配所有子对象。                                                                   | `$.store.*.price`                           | [匹配store子对象中的价格，因为book的价格，是更下一级，所以只能匹配到bicycle的价格](http://jsonpath.herokuapp.com/?path=$.store.*.price)。 |
| ?()               | 过滤符，可以理解成SQL的Where。                                                             | `$.store.[?(@.category=="fiction")].author` | [获取类别为fiction的书籍作者列表](http://jsonpath.herokuapp.com/?path=$.store.[?(@.category==%22fiction%22).author])。                    |
| @                 | 当前对象，配合`?()`很好用。                                                                |                                             |                                                                                                                                           |




### k8s使用jsonpath

kubectl没有提供查看Pod内容器的名称，怎么办呢？可以利用jsonpath或者go template实现。

json格式输出结果通常是嵌套多层，使用jsonpath可以忽略中间层次，而go template不行，这是jsonpath比go template好用的地方。

看一个略微复杂k8s使用jsonpath列出所有pod的所有容器名称和镜像的样例：

```
kubectl get pods --all-namespaces -o=jsonpath='{range .items[*]}{"pod: "}{.metadata.name} {"\n"}{range .spec.containers[*]}{"\tcontainer: "}{.name}{"\n\timage: "}{.image}{"\n"}{end}{end}'
```

发现`jsonpath=''`与标准的jsonpath并不一样：

- 没有`$`
- 一堆`{}`
- 还有`range, {"\n"}`等

那是因为[k8s对jsonpath的支持](https://kubernetes.io/docs/reference/kubectl/jsonpath/)有以下特性：

1. 在jsonpath中使用`""`包含文本，这样在输出的结果可以显示自定义的字符串，还能进行换行、Tab等。
2. 支持使用`range .. end`迭代数组，原生的jsonpath没有办法提取数组元素中的多个子对象，使用range达成效果，比如想获得容器的名称镜像。
3. 支持`-num`获取数组的倒数位置的元素
4. 可以省略`$`，太好了
5. 每一段jsonpath使用`{}`连接

刚开始使用jsonpath时，有种眼花缭乱的感觉，我们就拆解下上面的样例jsonpath。

```
kubectl get pods --all-namespaces -o=jsonpath='{.items[*].metadata.name}'
```

![](http://img.lessisbetter.site/2020-11-1-pod-name.png)

先提取每个pod的名称，这个还和原生的jsonpath一样。

```
kubectl get pods --all-namespaces -o=jsonpath='{range .items[*]}{"pod: "}{.metadata.name}{"\n"}{end}'
```

![](http://img.lessisbetter.site/2020-11-2-pod-name-range.png)

因为每个pod还要取容器名称和镜像，所以最好每个pod占一行，我们需要使用`range .. end`处理每一个pod，列pod所含的容器。

```
kubectl get pods --all-namespaces -o=jsonpath='{range .items[*]}{"pod: "}{.metadata.name}{"\n"}{"\tcontainer: "}{.spec.containers[*].name}, {.spec.containers[*].image}{"\n"}{end}'

```

![](http://img.lessisbetter.site/2020-11-3-pod-containers.png)

可以看到每个pod内可能包含多个容器，所以也得用`range .. end`去处理pod的每一个container。

```
kubectl get pods --all-namespaces -o=jsonpath='{range .items[*]}{"pod: "}{.metadata.name} {"\n"}{range .spec.containers[*]}{"\tcontainer: "}{.name}{"\n\timage: "}{.image}{"\n"}{end}{end}'

```

![](http://img.lessisbetter.site/2020-11-4-pod-contianers-image.png)

上面提到使用jsonpath可以简化层级，因为`containers`这个名词在层级中是独有的，不像`name`可能是存在于多个层级，所以可以使用`..`简化：

```
kubectl get pods --all-namespaces -o=jsonpath='{range .items[*]}{"pod: "}{.metadata.name} {"\n"}{range ..containers[*]}{"\tcontainer: "}{.name}{"\n\timage: "}{.image}{"\n"}{end}{end}'
```

![](http://img.lessisbetter.site/2020-11-5-simplify-pod-containers.png)

最后看一下过滤的使用，只想列出`weave`的pod的容器和镜像：

```
kubectl get pods --all-namespaces -o=jsonpath='{range .items[?(@.metadata.name=="weave-net-sqjzh")]}{"pod: "}{.metadata.name} {"\n"}{range ..containers[*]}{"\tcontainer: "}{.name}{"\n\timage: "}{.image}{"\n"}{end}{end}'
```

![](http://img.lessisbetter.site/2020-11-6-pod-filter.png)

### 练习

使用JSONPath获取：
1. Pod的名称和IP
2. Pod退出原因

### 参考资料

- [goessner: JSONPath - XPath for JSON](https://goessner.net/articles/JsonPath/)
- [Kubernetes JSONPath Support](https://kubernetes.io/docs/reference/kubectl/jsonpath/)，[一个中文版本](http://docs.kubernetes.org.cn/67.html)


