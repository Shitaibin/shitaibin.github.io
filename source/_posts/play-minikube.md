---
title: 玩转minikube
date: 2020-08-27 21:30:41
tags: ['Docker', 'Kubernetes']
---

minikube很好，但某些原因造成国内用起来比较慢，要各种挂代理、Docker镜像加速。

## minikube原理

![](https://lessisbetter.site/images/2020-08-minikube.jpeg)

kubectl和kube-apiserver是CS架构，kubectl是操作k8s集群的客户端，kube-apiserver是服务端。

minikube是创建了一个虚拟机`minikube vm`，然后在虚拟机里创建了1个单机的k8s集群，并把集群部署信息写到`~/.kube/config`文件，它是kubectl默认使用的配置文件。

```
[~]$ ls ~/.kube/config
/Users/shitaibin/.kube/config
[~]$ cat ~/.kube/config
apiVersion: v1
clusters:
- cluster:
    certificate-authority: /Users/shitaibin/.minikube/ca.crt
    server: https://192.168.99.103:8443
  name: minikube
contexts:
- context:
    cluster: minikube
    user: minikube
  name: minikube
current-context: minikube
kind: Config
preferences: {}
users:
- name: minikube
  user:
    client-certificate: /Users/shitaibin/.minikube/profiles/minikube/client.crt
    client-key: /Users/shitaibin/.minikube/profiles/minikube/client.key
```

文件内容也可以使用 `kubectl config view` 命令查看。

```
[~]$ kubectl config view
apiVersion: v1
clusters:
- cluster:
    certificate-authority: /Users/shitaibin/.minikube/ca.crt
    server: https://192.168.99.103:8443
  name: minikube
contexts:
- context:
    cluster: minikube
    user: minikube
  name: minikube
current-context: minikube
kind: Config
preferences: {}
users:
- name: minikube
  user:
    client-certificate: /Users/shitaibin/.minikube/profiles/minikube/client.crt
    client-key: /Users/shitaibin/.minikube/profiles/minikube/client.key
[~]$
```

## 安装软件

1. 安装minikube，1分钟，如果提供的命令行下载不下来，就浏览器下载下来，放到增加可执行，然后放到bin目录即可：
https://yq.aliyun.com/articles/691500

1. centos安装virtualbox，2分钟安装完成:
https://wiki.centos.org/zh/HowTos/Virtualization/VirtualBox

3. 安装kubectl：
https://blog.csdn.net/yuanjunlai141/article/details/79469071


## 首次启动

启动命令
```
minikube start --image-mirror-country cn \
    --iso-url=https://kubernetes.oss-cn-hangzhou.aliyuncs.com/minikube/iso/minikube-v1.7.3.iso \
    --registry-mirror="https://a90tkz28.mirror.aliyuncs.com" \
    --image-repository="registry.cn-hangzhou.aliyuncs.com/google_containers" \
    --kubernetes-version=v1.18.3
```

使用minikube可以查看帮助flag帮助信息：

- `--image-mirror-country`: 需要使用的镜像镜像的国家/地区代码。留空以使用全球代码。对于中国大陆用户，请将其设置为
cn
- `--registry-mirror`: 传递给 Docker 守护进程的注册表镜像。效果最好的镜像加速器：`--registry-mirror="https://a90tkz28.mirror.aliyuncs.com"` 。使用加速器的原理是，docker deamon会先去加速器寻找镜像，如果找不到才从docker官方仓库拉镜像。如果指定拉某个镜像仓库的镜像，镜像加速器是用不上的。
- `--image-repository` : 如果不能从gcr.io拉镜像，配置minikube中docker拉镜像的地方
- `--kubernetes-version`： 指定要部署的k8s版本，可以省略

minikube内拉不到镜像的报错:

```
$ kubectl describe pod
  Type     Reason     Age                    From               Message
  ----     ------     ----                   ----               -------
  Warning  Failed     2m59s (x4 over 4m36s)  kubelet, minikube  Failed to pull image "kubeguide/redis-master": rpc error: code = Unknown desc = Error response from daemon: Get https://registry-1.docker.io/v2/: proxyconnect tcp: dial tcp 192.168.0.104:1087: connect: connection refused
```

启动日志：

```
$ minikube start --image-mirror-country cn \
    --iso-url=https://kubernetes.oss-cn-hangzhou.aliyuncs.com/minikube/iso/minikube-v1.7.3.iso \
    --registry-mirror="https://a90tkz28.mirror.aliyuncs.com" \
    --image-repository="registry.cn-hangzhou.aliyuncs.com/google_containers"
😄  Darwin 10.15.3 上的 minikube v1.12.3
✨  根据用户配置使用 virtualbox 驱动程序
✅  正在使用镜像存储库 registry.cn-hangzhou.aliyuncs.com/google_containers
👍  Starting control plane node minikube in cluster minikube
🔥  Creating virtualbox VM (CPUs=2, Memory=4000MB, Disk=20000MB) ...
💡  Existing disk is missing new features (lz4). To upgrade, run 'minikube delete'
🐳  正在 Docker 19.03.6 中准备 Kubernetes v1.18.3…
🔎  Verifying Kubernetes components...
🌟  Enabled addons: default-storageclass, storage-provisioner
🏄  完成！kubectl 已经配置至 "minikube"
```

做哪些事？
1. 创建虚拟机"minikube"
2. 生成kubectl使用的配置文件，使用该配置连接集群：~/.kube/config
3. 在虚拟机里的容器上启动k8s

```
$ minikube ssh
                         _             _
            _         _ ( )           ( )
  ___ ___  (_)  ___  (_)| |/')  _   _ | |_      __
/' _ ` _ `\| |/' _ `\| || , <  ( ) ( )| '_`\  /'__`\
| ( ) ( ) || || ( ) || || |\`\ | (_) || |_) )(  ___/
(_) (_) (_)(_)(_) (_)(_)(_) (_)`\___/'(_,__/'`\____)

$
$ docker info
Client:
 Debug Mode: false

Server:
 Containers: 18
  Running: 15
  Paused: 0
  Stopped: 3
 Images: 11
 Server Version: 19.03.6
 Storage Driver: overlay2
  Backing Filesystem: extfs
  Supports d_type: true
  Native Overlay Diff: true
 Logging Driver: json-file
 Cgroup Driver: cgroupfs
 Plugins:
  Volume: local
  Network: bridge host ipvlan macvlan null overlay
  Log: awslogs fluentd gcplogs gelf journald json-file local logentries splunk syslog
 Swarm: inactive
 Runtimes: runc
 Default Runtime: runc
 Init Binary: docker-init
 containerd version: 35bd7a5f69c13e1563af8a93431411cd9ecf5021
 runc version: dc9208a3303feef5b3839f4323d9beb36df0a9dd
 init version: fec3683
 Security Options:
  seccomp
   Profile: default
 Kernel Version: 4.19.94
 Operating System: Buildroot 2019.02.9
 OSType: linux
 Architecture: x86_64
 CPUs: 2
 Total Memory: 3.754GiB
 Name: minikube
 ID: 6GOT:L6SH:NPBW:ZM44:PVKY:LSEZ:MXW7:LWOB:GB4N:CNXU:S6NJ:KASG
 Docker Root Dir: /var/lib/docker
 Debug Mode: false
 Registry: https://index.docker.io/v1/
 Labels:
  provider=virtualbox
 Experimental: false
 Insecure Registries:
  10.96.0.0/12
  127.0.0.0/8
 Registry Mirrors:
  https://a90tkz28.mirror.aliyuncs.com/
 Live Restore Enabled: false
 Product License: Community Engine

$ exit
logout
```

Registry Mirrors对应的是阿里云镜像加速，HTTP proxy也配置上了，如果启动后，发现没有改变，需要删除过去创建的minikube，全部清理一遍。

## minikube常用命令



- 集群状态： minikube status
- 暂停和恢复集群，不用的时候把它暂停掉，节约主机的CPU和内存： minikube pause， minikube unpause
- 停止集群： minikube stop
- 删除集群，遇到问题时，清理一波数据： minikube delete
- 查看集群IP，kubectl就是连这个IP： minikube ip
- 进入minikube虚拟机，整个k8s集群跑在这里面： minikube ssh

## kubectl自动补全

zsh在配置文件 `~/.zshrc` 中增加：

```
source <(kubectl completion zsh)  # 在 zsh 中设置当前 shell 的自动补全
echo "if [ $commands[kubectl] ]; then source <(kubectl completion zsh); fi" >> ~/.zshrc # 在您的 zsh shell 中永久的添加自动补全
```

bash 在 `~/.bashrc` 中增加:

```
source <(kubectl completion bash) # 在 bash 中设置当前 shell 的自动补全，要先安装 bash-completion 包。
echo "source <(kubectl completion bash)" >> ~/.bashrc # 在您的 bash shell 中永久的添加自动补全
```