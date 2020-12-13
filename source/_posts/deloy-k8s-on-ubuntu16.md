---
title: Ubuntu 16.04上部署单机Kubernetes
date: 2020-09-06 08:33:55
tags: ['Kubernetes', 'Docker']
---

在公司都是用现成的K8s集群，没自己搭过，想知道搭建集群涉及哪些组件、做了什么，于是自己搭了一下，没想象的顺利，动作做到位了，也就不会有太多问题。

许多资料都是基于Centos7的，包括《Kubernetes权威指南》，手头只有Ubuntu 16.04，刚好也是支持K8s最低Ubuntu版本，就在Ubuntu上面部署。Ubuntu与Centos部署K8s并没有太大区别，唯一区别是安装kubeadm等软件的不同，由于k8s本身也是运行在容器中，其他的过程二者都相同了，这种设计也极大的方便了k8s集群的搭建。

**没有阿里云，搭建一个K8s集群还是挺费劲的**。

## 准备工作

1. `/etc/hosts`中加入：

```
127.0.0.1 k8s-master
```


2. 关闭防火墙：`ufw status`

3. [安装Docker，并设置镜像加速器](https://lessisbetter.site/2020/09/05/docker-proxy-and-registry-mirror/)。

## 安装软件

Ubuntu 16.04上利用阿里云安装kubeadm、kubelet、kubectl

```
sudo apt-get update && sudo apt-get install -y apt-transport-https curl
curl -s http://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | sudo apt-key add -
cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb http://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
EOF
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

centos 7上利用阿里云镜像安装kubeadm、kubelet、kubectl

```
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=http://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=http://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg http://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF

# 将 SELinux 设置为 permissive 模式（相当于将其禁用）
setenforce 0
sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config

yum install -y kubelet kubeadm kubectl --disableexcludes=kubernetes

systemctl enable --now kubelet
```

二进制程序安装位置：

```
[~]$ which kubectl kubeadm kubectl
/usr/bin/kubectl
/usr/bin/kubeadm
/usr/bin/kubectl
```


## 部署Master节点

```
kubeadm init \
  --kubernetes-version=v1.19.0 \
  --image-repository registry.cn-hangzhou.aliyuncs.com/google_containers \
  --pod-network-cidr=10.24.0.0/16 \
  --ignore-preflight-errors=Swap
```

- `--image-repository` ： 由于`k8s.gcr.io`由于网络原因无法访问，使用阿里云提供的k8s镜像仓库，快速下载k8s相关的镜像
- `--ignore-preflight-errors` ： 部署时忽略swap问题
- `--pod-network-cidr` ：设置pod的ip区间

遇到错误需要重置集群：`kubeadm reset`

遇到错误参考：[kubernetes安装过程报错及解决方法](https://www.cnblogs.com/pu20065226/p/10641312.html)

## 拷贝kubectl配置

切回普通用户，拷贝当前集群的配置给kubectl使用：

```
  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

查看集群信息：

```
dabin@ubuntu:~$ kubectl cluster-info
Kubernetes master is running at https://192.168.0.103:6443
KubeDNS is running at https://192.168.0.103:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

## k8s主节点部署后的情况

k8s本身不负责容器之间的通信，集群启动后，集群的Pod直接还不能通信，需要安装网络插件。

```
$ kubectl get node
NAME         STATUS     ROLES    AGE    VERSION
k8s-master   NotReady   master   5m8s   v1.19.0
$ kubectl get pod -n kube-system -owide

NAME                                  READY   STATUS    RESTARTS   AGE   IP         NODE          NOMINATED NODE   READINESS GATES
coredns-6c76c8bb89-9wnfb              0/1     Pending   0          56s   <none>     <none>        <none>           <none>
coredns-6c76c8bb89-glkdx              0/1     Pending   0          56s   <none>     <none>        <none>           <none>
etcd-shitaibin-x                      0/1     Running   0          70s   10.0.0.3   shitaibin-x   <none>           <none>
kube-apiserver-shitaibin-x            1/1     Running   0          70s   10.0.0.3   shitaibin-x   <none>           <none>
kube-controller-manager-shitaibin-x   1/1     Running   0          70s   10.0.0.3   shitaibin-x   <none>           <none>
kube-proxy-7gpjx                      1/1     Running   0          56s   10.0.0.3   shitaibin-x   <none>           <none>
kube-scheduler-shitaibin-x            0/1     Running   0          70s   10.0.0.3   shitaibin-x   <none>           <none>
```

从上面可以看到master节点为 NotReady 状态，coredns 服务也没有分配ip。

从下面的Condition和Events可以看到节点会进行4项检测：
1. 节点内存是否充足
2. 节点磁盘是否有压力
3. 节点Pid是否充足
4. kubelet是否就绪

从Events可以kubelet启动了2次，而内存、磁盘压力、pid条件检查进行了4次。

从Condition的kubelet消息中看到CNI网络插件还未就绪，导致kubelet并没有ready。

```
$ kubectl describe nodes shitaibin-x
Name:               shitaibin-x
Roles:              master
...
Conditions:
  Type             Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message
  ----             ------  -----------------                 ------------------                ------                       -------
  MemoryPressure   False   Wed, 28 Oct 2020 08:40:18 +0000   Wed, 28 Oct 2020 08:40:07 +0000   KubeletHasSufficientMemory   kubelet has sufficient memory available
  DiskPressure     False   Wed, 28 Oct 2020 08:40:18 +0000   Wed, 28 Oct 2020 08:40:07 +0000   KubeletHasNoDiskPressure     kubelet has no disk pressure
  PIDPressure      False   Wed, 28 Oct 2020 08:40:18 +0000   Wed, 28 Oct 2020 08:40:07 +0000   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready            False   Wed, 28 Oct 2020 08:40:18 +0000   Wed, 28 Oct 2020 08:40:07 +0000   KubeletNotReady              runtime network not ready: NetworkReady=false reason:NetworkPluginNotReady message:docker: network plugin is not ready: cni config uninitialized
....
Events:
  Type    Reason                   Age                  From        Message
  ----    ------                   ----                 ----        -------
  Normal  Starting                 111s                 kubelet     Starting kubelet.
  Normal  NodeHasSufficientMemory  110s (x3 over 110s)  kubelet     Node shitaibin-x status is now: NodeHasSufficientMemory
  Normal  NodeHasNoDiskPressure    110s (x3 over 110s)  kubelet     Node shitaibin-x status is now: NodeHasNoDiskPressure
  Normal  NodeHasSufficientPID     110s (x3 over 110s)  kubelet     Node shitaibin-x status is now: NodeHasSufficientPID
  Normal  NodeAllocatableEnforced  110s                 kubelet     Updated Node Allocatable limit across pods
  Normal  Starting                 88s                  kubelet     Starting kubelet.
  Normal  NodeHasSufficientMemory  88s                  kubelet     Node shitaibin-x status is now: NodeHasSufficientMemory
  Normal  NodeHasNoDiskPressure    88s                  kubelet     Node shitaibin-x status is now: NodeHasNoDiskPressure
  Normal  NodeHasSufficientPID     88s                  kubelet     Node shitaibin-x status is now: NodeHasSufficientPID
  Normal  NodeAllocatableEnforced  87s                  kubelet     Updated Node Allocatable limit across pods
  Normal  Starting                 66s                  kube-proxy  Starting kube-proxy.
```

查看kubelet进程启动配置：
```
$ ps -ef | grep kubelet
root      5549     1  2 08:40 ?        00:00:07 /usr/bin/kubelet --bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --kubeconfig=/etc/kubernetes/kubelet.conf --config=/var/lib/kubelet/config.yaml --network-plugin=cni --pod-infra-container-image=registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.2
```

通过`--network-plugin=cni`可以看到默认使用CNI作为网络插件。

主机`/etc/cni/net.d`目录保存CNI的配置，发现目前为空。`/opt/cni/bin`目录为CNI插件程序所在的位置，可以看到已经有flannel等插件。

```
$ ls /etc/cni/net.d
ls: cannot access '/etc/cni/net.d': No such file or directory
$ ls /opt/cni/bin
bandwidth  bridge  dhcp  firewall  flannel  host-device  host-local  ipvlan  loopback  macvlan  portmap  ptp  sbr  static  tuning  vlan
```

接下来安装CNI网络插件。

## 安装CNI网络插件


k8s的[文档](https://kubernetes.io/zh/docs/concepts/cluster-administration/addons/)列举了多种选择，这里提供2种：

较为简便的weave，它提供overlay network:

```
kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')"
```

flannel，也是overlay network模型:

```
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

本机选择了weave：

```
dabin@ubuntu:~$ kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')"
serviceaccount/weave-net created
clusterrole.rbac.authorization.k8s.io/weave-net created
clusterrolebinding.rbac.authorization.k8s.io/weave-net created
role.rbac.authorization.k8s.io/weave-net created
rolebinding.rbac.authorization.k8s.io/weave-net created
daemonset.apps/weave-net created
```

查看weave的配置和可执行程序：
```
$ ls /etc/cni/net.d
10-weave.conflist
$ ls /opt/cni/bin
bandwidth  dhcp      flannel      host-local  loopback  portmap  sbr     tuning  weave-ipam  weave-plugin-2.7.0
bridge     firewall  host-device  ipvlan      macvlan   ptp      static  vlan    weave-net
$
$ cat /etc/cni/net.d/10-weave.conflist
{
    "cniVersion": "0.3.0",
    "name": "weave",
    "plugins": [
        {
            "name": "weave",
            "type": "weave-net",
            "hairpinMode": true
        },
        {
            "type": "portmap",
            "capabilities": {"portMappings": true},
            "snat": true
        }
    ]
}
```

安装之后节点变为Ready，coredns也拥有了ip：

```
$ kubectl get node
NAME         STATUS   ROLES    AGE   VERSION
k8s-master   Ready    master   10m   v1.19.0

$ kubectl get pod -n kube-system -owide
NAME                                  READY   STATUS    RESTARTS   AGE     IP          NODE          NOMINATED NODE   READINESS GATES
coredns-6c76c8bb89-9wnfb              1/1     Running   0          19m     10.32.0.9   shitaibin-x   <none>           <none>
coredns-6c76c8bb89-glkdx              1/1     Running   0          19m     10.32.0.8   shitaibin-x   <none>           <none>
etcd-shitaibin-x                      1/1     Running   0          20m     10.0.0.3    shitaibin-x   <none>           <none>
kube-apiserver-shitaibin-x            1/1     Running   0          20m     10.0.0.3    shitaibin-x   <none>           <none>
kube-controller-manager-shitaibin-x   1/1     Running   0          20m     10.0.0.3    shitaibin-x   <none>           <none>
kube-proxy-7gpjx                      1/1     Running   0          19m     10.0.0.3    shitaibin-x   <none>           <none>
kube-scheduler-shitaibin-x            1/1     Running   0          20m     10.0.0.3    shitaibin-x   <none>           <none>
weave-net-72p6p                       2/2     Running   0          2m36s   10.0.0.3    shitaibin-x   <none>           <none>
```

## 开启master调度

master节点默认是不可被调度的，不可在master上部署任务，在单节点下，只有master一个节点，部署资源后会出现以下错误：

```
$ kubectl describe pod mysql
Events:
  Type     Reason            Age                From               Message
  ----     ------            ----               ----               -------
  Warning  FailedScheduling  22s (x2 over 22s)  default-scheduler  0/1 nodes are available: 1 node(s) had taint {node-role.kubernetes.io/master: }, that the pod didn't tolerate.
```

Event的告警信息提示，当前节点存在一个污点`node-role.kubernetes.io/master:`，而pod却不容忍这个污点。

查看master节点的信息，确实可以看到一个不允许调度的污点。

```
$ kubectl get nodes shitaibin-x -o yaml | grep -10 taint
...
spec:
  podCIDR: 10.24.0.0/24
  podCIDRs:
  - 10.24.0.0/24
  taints:
  - effect: NoSchedule
    key: node-role.kubernetes.io/master
```

有2个办法解决这个问题，让资源可以调度到master节点上：
1. 所有的资源声明文件中，都设置容忍这个污点，
2. master节点上删除这个污点

我们是一个测试环境，采取第2种办法更简单：

```
# --all为所有节点上的污点
# 最后的-代表移除污点
kubectl taint nodes --all node-role.kubernetes.io/master-
```

移除污点记录：

```
[~]$ kubectl taint nodes shitaibin-x node-role.kubernetes.io/master-
node/shitaibin-x untainted
[~]$
[~]$ kubectl get nodes shitaibin-x -o yaml | grep -10 taint
[~]$
[~]$ kubectl describe pod | grep -10 Events
...
Events:
  Type     Reason            Age                  From               Message
  ----     ------            ----                 ----               -------
  Warning  FailedScheduling  27s (x7 over 7m38s)  default-scheduler  0/1 nodes are available: 1 node(s) had taint {node-role.kubernetes.io/master: }, that the pod didn't tolerate.
  Normal   Scheduled         17s                  default-scheduler  Successfully assigned default/mysql-0 to shitaibin-x
  Normal   Pulled            15s                  kubelet            Container image "mysql:5.6" already present on machine
  Normal   Created           14s                  kubelet            Created container mysql
  Normal   Started           14s                  kubelet            Started container mysql
```

## 测试集群

部署一个Pod进行测试，Pod能Running，代表Docker、K8s的配置基本没问题了：

声明文件为`twocontainers.yaml`:

```
apiVersion: v1 #指定当前描述文件遵循v1版本的Kubernetes API
kind: Pod #我们在描述一个pod
metadata:
  name: twocontainers #指定pod的名称
  namespace: default #指定当前描述的pod所在的命名空间
  labels: #指定pod标签
    app: twocontainers
  annotations: #指定pod注释
    version: v0.5.0
    releasedBy: david
    purpose: demo
spec:
  containers:
    - name: sise #容器的名称
      image: quay.io/openshiftlabs/simpleservice:0.5.0 #创建容器所使用的镜像
      ports:
        - containerPort: 9876 #应用监听的端口
    - name: shell #容器的名称
      image: centos:7 #创建容器所使用的镜像
      command: #容器启动命令
        - "bin/bash"
        - "-c"
        - "sleep 10000"
```

部署Pod：

```
kubectl apply -f twocontainers.yaml
```

几分钟后可以看pod状态是否为running。

```
dabin@k8s-master:~/workspace/notes/kubernetes/examples$ kubectl get pods
NAME            READY   STATUS    RESTARTS   AGE
twocontainers   2/2     Running   2          83m
```

如果不是，查看Pod部署遇到的问题：

```
kubectl describe pod twocontainers
```

## 清空k8s环境

```
// remove_k8s.sh
# 重置k8s
sudo kubeadm reset -f
# 删除kubectl配置文件
sudo rm -rf ~/.kube
# 卸载和清理程序配置文件
sudo apt-get -y purge kubeadm kubectl kubelet kubernetes-cni
# 卸载自安装依赖
sudo apt-get -y autoremove

# 删除遗留的文件
sudo rm -rf ~/.kube/
sudo rm -rf /etc/kubernetes/
sudo rm -rf /etc/systemd/system/kubelet.service.d
sudo rm -rf /etc/systemd/system/kubelet.service
sudo rm -rf /etc/cni
sudo rm -rf /opt/cni
sudo rm -rf /var/lib/etcd
sudo rm -rf /var/etcd
```

## 更快的部署方法？

利用[kind](https://github.com/kubernetes-sigs/kind)，使用Docker快速部署一个**本地测试、开发**k8s环境。

```
GO111MODULE="on" go get sigs.k8s.io/kind@v0.9.0 && kind create cluster
```

## 资料

1. 人人必备的神书《Kuerbenetes权威指南》
2. [K8S中文文档](https://kubernetes.io/zh/docs/setup/independent/create-cluster-kubeadm/)
3. [kubernetes安装过程报错及解决方法](https://www.cnblogs.com/pu20065226/p/10641312.html)