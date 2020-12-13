---
title: 重新安装Hexo博客的流程
date: 2018-06-02 08:45:31
tags: ['Hexo']
---

# 流程

安装：
1. 官网下载最新的node，然后安装。
2. 安装官网安装Hexo： `npm install -g hexo-cli`。
3. 新建文件夹`blog`，然后进入。
4. `hexo init`。


设置博客：
1. 把备份（老博客）的md文件放到新的post的地址：`cp -r old/blogDir/source/* ./source`。
6. 把备份的`_config.yaml`配置文件中**有用的选项**放到新的配置文件中，不要覆盖进新版本的Hexo。
7. 建立`hexo_resource`分支，该分支用来存放hexo的配置和博文等文件。master分支留着给博客使用，存放的是博客的静态文件。
8. 配置Hexo的Next主题：
   a. `cd themes && git clone https://github.com/next-theme/hexo-theme-next`，可以看下[Next主题官网](https://theme-next.org/)最新的操作。
   b. 下载[备份的Next主题配置文件](https://github.com/Shitaibin/hexo-next-theme-for-stb)，有用的项目拷贝到新的配置文件。
9.  安装插件：
    a. pdf插件：`npm install --save hexo-pdf` 。
    b. git插件：`npm install hexo-deployer-git --save` 。
10. `hexo g && hexo s`，本地预览效果。
11. 执行`hexo d`，生成的博客文件会上传到Github。
12. 在`hexo_resource`分支下工作即可，写完文章后，执行`sh deploy_and_backup_hexo_br.sh`，备份好分支，博客推送到远端。


其他信息看老文章：https://lessisbetter.site/2015/05/01/blog-with-hexo/

# 脚本

- deploy_and_backup_hexo_br.sh:

```
hexo clean
git add .
git commit -m 'auto backup'
git push origin hexo_resource
hexo d
```

