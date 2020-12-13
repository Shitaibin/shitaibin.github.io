---
title: Oh my zsh
date: 2020-11-18 20:09:49
tags: ['Terminal']
---


### 配置文件

选择oh my zsh的原因在于它提供了很多插件和主题。

zsh的配置文件为：`~/.zshrc`，oh my zsh的许多配置也在此添加。

### 主题

习惯使用[gallois主题](https://github.com/ohmyzsh/ohmyzsh/blob/master/themes/gallois.zsh-theme)，但发现它有一个现在无法忍受的缺点，如果当前目录是git仓库，它会在右边显示分支名称和clean状态。当从终端复制文本出来时，分支名称和左边命令的空白，全是空格填充，复制出来就得手动删除。

![](http://img.lessisbetter.site/2020-11-old-gallois.png)

oh my zsh的所有主题配置都在`.oh-my-zsh/themes/`目录，文件名称同主题名称，可以对这些主题的一些配置进行修改。

注释掉配置文件中关于git的设置，打开新终端后，就可以不显示git分支信息了。

![](http://img.lessisbetter.site/2020-11-new-gallois.png)


从此复制出的代码，在也没有多余文本。

### 插件

插件目录在：`~/.oh-my-zsh/plugins`，从中可以浏览自己需要的插件。

比如我常用的插件为：`plugins=(git autojump docker kubectl extract)`，添加到`~/.zshrc`即可。