---
title: 为Github博客配置自定义域名
date: 2018-09-26 09:35:04
tags: ['博客']
---

七牛空间的测试域名现在只能使用一个月了，有天突然发现，博客的图片都无法访问了，因此要为七牛配置自定义的域名，顺便也把博客的自定义域名配上。

看了Github Pages帮助文档，来回跳转导致配置成本增加，记录下简要配置过程，帮助打算配置自定义域名的朋友。


## 配置步骤

前提：
1. 已经购买了域名。
2. Github上已经部署了博客。

域名配置步骤，只需3个：
1. 获取托管你的博客的Github Pages服务器。`ping your_name.github.io`，必然是[这里列出的某一个](https://help.github.com/articles/troubleshooting-custom-domains/#dns-record-doesnt-point-to-githubs-server)。
1. 博客Github仓库页增加CNAME文件，CNAME的配置注意事项见[这里](https://help.github.com/articles/troubleshooting-custom-domains/#the-cname-file-isnt-properly-formatted)， 我的仓库示例在[这里](https://github.com/Shitaibin/shitaibin.github.io/blob/master/CNAME)。
1. 为你的域名配置解析，让你的DNS能指到Github Pages的服务器IP地址。如果你是阿里云的，参考[这个](https://jingyan.baidu.com/article/6fb756ec737930241858fba9.html)。其中填写的IP就是步骤1中获取的Github Pages的IP地址。

<!--more-->

## 配置出问题了？

1. Hexo博客Deploy后CNAME文件消失了？
到Hexo本地仓库的`source`目录增加文件CNAME，内容和Github仓库页的CNAME相同。

2. 其他
[这个网页](https://help.github.com/articles/troubleshooting-custom-domains/)，专门帮你解决域名配置错误的疑难杂症。
