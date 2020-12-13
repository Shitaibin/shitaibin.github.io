---
title: VSCode利用SFTP上传代码到服务器
date: 2020-08-27 20:24:00
tags: ['VSCode', 'SFTP']
---

VSCode已经支持远程开发，可以把代码自动从本地和服务器进行同步。

为了某些实验搞了一条Ubuntu 14.04的服务器，结果VSCode说远程服务器不支持，就只能另谋它路了，利用SFTP实现本地和服务器端的代码同步。

## 步骤

1. VSCode应用市场安装SFTP插件
2. 在项目目录下建立SFTP的配置文件：`.vscode/sftp.json`，内容如下

```json
{
    "name": "root",
    "host": "192.168.9.xxx",
    "protocol": "sftp",
    "port": 22,
    "username": "centos",
    "privateKeyPath": "/Users/shitaibin/.ssh/id_xxx",
    "remotePath": "/home/centos/workspace/docker/notes",
    "uploadOnSave": true,
    "ignore": [".vscode", ".git", ".DS_Store", "node_modules", "vendor"],
    "localPath":"."
}
```

登录服务器可以使用密码或者私钥，上面文件的示例使用私钥，如果使用密码，增加一项`password`即可。

`uploadOnSave`配置项设置为true，能够确保文件保存时，自动上传到服务器，无需手动上传。

3. 初次上传到服务器

    a. Ctrl + Shift + P，输入`SFTP`，选择`Sync Local -> Remote`即可
    b. VSCode底部状态栏，会显示SFTP，如果在动态变化，说明在上传文件

