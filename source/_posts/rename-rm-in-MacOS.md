---
title: 重命名rm命令，防止误删
date: 2018-09-07 08:45:31
tags: ['Mac', 'Bash']
---

Oh Shit！误删数据了。


既然看这篇文章，你必然也有`rm`命令误删数据的经历了，废话少说，解决办法：使用trash-cli覆盖原有的`rm`命令，把`rm`命令更改为`RM`。

需要的软件:
- [trash-cli](https://github.com/andreafrancia/trash-cli)：会把删除的数据，单独放到程序建立的垃圾桶，可以通过自带的命令查询和恢复。

优点：再也不担心数据丢失了。
缺点：需要手动去清空垃圾桶，是否垃圾占用的空间，还好可以搞个定时任务解决。

<!--more-->

1. 安装办法见Github项目的Readme文档。
2. 修改`.bashrc`或`.zshrc`，增加昵称覆盖原有的`rm`命令。
```bash
alias rm='trash-put'        #文件移动到垃圾桶
alias rl='trash-list'       #列出删除的文件
alias ur='trash-restore'    #恢复删除的文件
alias RM='/bin/rm'          #原有的rm命令
```
3. 上述命令用起来，建立临时文件去测试吧。
