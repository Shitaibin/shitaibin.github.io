---
title: k8s hostport
date: 2021-02-21 10:18:46
tags: ['Kubernetes']
---

hostport是一种把host的ip:port绑定到pod的port方法，是端口路由，访问host的ip:port即可访问pod的port。

hostport是一个三元组配置：`<hostIP, hostPort, protocol>` ，hostIP不配置时，默认为`0.0.0.0`，`protocol`默认为`TCP`。

如下的Pod声明文件，指nginx这个Pod使用hostport，使用的是<0.0.0.0, 80, TCP>，即host上所有IP的80端口的TCP连接，都会转发给该nginx Pod。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  containers:
  - image: nginx
    name: nginx
    ports:
    - containerPort: 80
      hostPort: 80
```

特点：
1. host上的任何两个pod不能有相同的hostport。由于端口绑定，host上的某个端口只能被1个Pod所绑定。
2. host的ip和port资源是有限的，所能支持使用hostPort的pod数也是有限的。
3. 灵活性差，需要维护name service。当pod被迁移到新node时，需要使用新node的ip访问pod。


node1的ip为`10.0.13.3`，则：
1. <0.0.0.0, 80, TCP> 和 <10.0.13.3, 80, TCP>是冲突的。
2. <10.0.13.3, TCP> 和 <10.0.13.3, 80, TCP>是冲突的。
3. <0.0.0.0, 80, TCP> 和 <10.0.13.3, 80, UDP>是不冲突的。
4. <10.0.13.3, 80, TCP> 和 <10.0.13.3, 80, UDP>是不冲突的。
5. <0.0.0.0, 80, TCP> 和 <10.0.13.3, 90, TCP>是不冲突的。
