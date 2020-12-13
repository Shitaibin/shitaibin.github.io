---
title: Go依赖包管理工具，3分钟掌握govendor
date: 2018-11-17 20:25:34
tags: ['Go', 'govendor']
---



网上写govendor的博文不少，但从安装到介绍，总看上去有些**沉重**，下面奉上一篇简单的教程，3分钟入门。

# 第1部分 简明教程

2步走，3分钟轻松搞定Go项目的依赖。

## 第1步 安装

```bash
go get -u github.com/kardianos/govendor
```

<!--more-->

## 第2步 为项目增加依赖

1. 进入到项目目录
2. 使用`govendor init`命令初始化项目的依赖
3. 运行`govendor fetch`命令增加依赖
4. 打开`./vendor/vendor.json`查看依赖的包

步骤：

```bash
cd path/to/project
govendor init
govendor fetch project_url_with_out_http
cat vendor/vendor.json
```

举个例子：项目awesome依赖`github.com/go-clang/bootstrap`，过程是这样的：

```
cd awesome
govendor init
govendor fetch github.com/go-clang/bootstrap
cat vendor/vendor.json
```

# 第2部分 授之以渔

## 第1个 遇到govendor问题

govendor当然还有其他丰富功能，比如：

1. 依赖的包更新了，怎么更新依赖？
2. 不依赖这个包， 怎么移除？
3. 怎么快速查看已经依赖的包？
4. 怎么知道哪些包过期了，或者丢失了？

你可能想到时候遇到**再百度或者Google**一下，看看别人的博客或教程，这种方法太弱了，**浪费自己的时间，不能专心工作**。

**正确的姿势**：

1. 使用`govendor --help`列出各种命令。
2. 使用Ctrl+F开启终端搜索，寻找要使用的命令。

比如：

1. 增加包，搜add，会得到add和fetch这2个命令。
2. 更新包，搜update，会得到update和fetch这2个命令。
3. 删除包，搜remove，得到remove这个命令。
4. 查看已经依赖的包，搜list，得到list、status、license命令，而符合你的是list，并且知道了status能列出过期的包。

```bash
➜  project_name git:(develop) govendor --help
govendor (v1.0.9): record dependencies and copy into vendor folder
	-govendor-licenses    Show govendor's licenses.
	-version              Show govendor version
	-cpuprofile 'file'    Writes a CPU profile to 'file' for debugging.
	-memprofile 'file'    Writes a heap profile to 'file' for debugging.

Sub-Commands

	init     Create the "vendor" folder and the "vendor.json" file.
	list     List and filter existing dependencies and packages.
	add      Add packages from $GOPATH.
	update   Update packages from $GOPATH.
	remove   Remove packages from the vendor folder.
	status   Lists any packages missing, out-of-date, or modified locally.
	fetch    Add new or update vendor folder packages from remote repository.
	sync     Pull packages into vendor folder from remote repository with revisions
  	             from vendor.json file.
	migrate  Move packages from a legacy tool to the vendor folder with metadata.
	get      Like "go get" but copies dependencies into a "vendor" folder.
	license  List discovered licenses for the given status or import paths.
	shell    Run a "shell" to make multiple sub-commands more efficient for large
	             projects.

	go tool commands that are wrapped:
	  "+status" package selection may be used with them
	fmt, build, install, clean, test, vet, generate, tool

Status Types

	+local    (l) packages in your project
	+external (e) referenced packages in GOPATH but not in current project
	+vendor   (v) packages in the vendor folder
	+std      (s) packages in the standard library

	+excluded (x) external packages explicitly excluded from vendoring
	+unused   (u) packages in the vendor folder, but unused
	+missing  (m) referenced packages but not found

	+program  (p) package is a main package

	+outside  +external +missing
	+all      +all packages

	Status can be referenced by their initial letters.

Package specifier
	<path>[::<origin>][{/...|/^}][@[<version-spec>]]

Ignoring files with build tags, or excluding packages from being vendored:
	The "vendor.json" file contains a string field named "ignore".
	It may contain a space separated list of build tags to ignore when
	listing and copying files.
	This list may also contain package prefixes (containing a "/", possibly
	as last character) to exclude when copying files in the vendor folder.
	If "foo/" appears in this field, then package "foo" and all its sub-packages
	("foo/bar", …) will be excluded (but package "bar/foo" will not).
	By default the init command adds the "test" tag to the ignore list.

If using go1.5, ensure GO15VENDOREXPERIMENT=1 is set.
```

## 第2个 govendor做了啥

govendor“安装”软件包的时候做了啥呢？其实就是把依赖的包下载到`project_dir/vendor`目录，这个目录结构和`$GOPATH/src`下的相同，但如果下载一些比较大的会发现，govendor并不会下载依赖包的所有文件，而是上层的部分文件。想深入了解govendor？入门后再研究吧。

```bash
➜  awesome git:(master) ✗ tree .
.
├── awesome
├── hi.go
└── vendor
    ├── github.com
    │   └── go-clang
    │       └── bootstrap
    │           ├── AUTHORS
    │           ├── CONTRIBUTORS
    │           ├── LICENSE
    │           ├── Makefile
    │           └── README.md
    └── vendor.json
```

# govendor进阶

## 指定package版本、分支：`@`

```
govendor fetch path/to/package@version1
```

## 下载完整的package包：`/^`

govendor默认不下载完整的包，编译过程可能提示某文件不存在，尝试下载完整的package。

```
govendor fetch path/to/package/^
```

