---
title: 让Homebrew飞
date: 2019-07-13 11:12:17
tags: ['Mac']
---

## Homebrew源

homebrew默认使用的是Github，虽然已经科学上网了，速度依然是KB级别的，相当的慢。使用国内的源，速度有质的提升，推荐2个国内的：


腾讯：
- 源：https://mirrors.cloud.tencent.com/homebrew/brew.git
- 帮助文档：https://mirrors.cloud.tencent.com/help/homebrew-bottles.html


清华大学：
- 源：git://mirrors.ustc.edu.cn/brew.git
- 帮助文档：https://mirrors.tuna.tsinghua.edu.cn/help/homebrew/


建议ping一下以上2个源，选延时小的。

## 下载和修改安装脚本

下载官方安装脚本：

```
curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install >> brew_install
```

修改官方脚本，把Github源替换为腾讯源：

```
#!/usr/bin/ruby
# This script installs to /usr/local only. To install elsewhere (which is
# unsupported) you can untar https://github.com/Homebrew/brew/tarball/master
# anywhere you like.
HOMEBREW_PREFIX = "/usr/local".freeze
HOMEBREW_REPOSITORY = "/usr/local/Homebrew".freeze
HOMEBREW_CORE_TAP = "/usr/local/Homebrew/Library/Taps/homebrew/homebrew-core".freeze
HOMEBREW_CACHE = "#{ENV["HOME"]}/Library/Caches/Homebrew".freeze
BREW_REPO = "https://github.com/Homebrew/brew.git".freeze
```

把`BREW_REPO = "https://github.com/Homebrew/brew.git".freeze`替换为`BREW_REPO = "https://mirrors.cloud.tencent.com/homebrew/brew.git".freeze`。

## 运行脚本安装

```
/usr/bin/ruby ~/brew_install
```

这个版本的安装脚本已经没有CORE_TAP_REPO了，所以下载homebrew core的时候依然去Github下载，非常慢，可以在brew.git下载完，control-c结束掉。

把仓库`https://mirrors.cloud.tencent.com/homebrew/homebrew-core.git`克隆到`/usr/local/Homebrew/Library/Taps/homebrew/`目录，然后再执行上面的安装脚本。

## 更换brew源

如果brew已经安装了，直接修改源就行了。

1、替换brew.git和homebrew-core.git的源:

```bash
cd "$(brew --repo)"
git remote set-url origin https://mirrors.cloud.tencent.com/homebrew/brew.git


cd "$(brew --repo)/Library/Taps/homebrew/homebrew-core"
git remote set-url origin https://mirrors.cloud.tencent.com/homebrew/homebrew-core.git
```

2、更新 bottles源

对于bash用户：

```bash
echo 'export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.cloud.tencent.com/homebrew-bottles' >> ~/.bash_profile
source ~/.bash_profile
```

对于zsh用户

```bash
echo 'export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.cloud.tencent.com/homebrew-bottles' >> ~/.zshrc
source ~/.zshrc
```
