---
title: 以太坊有用的命令和标记
date: 2019-02-01 14:57:55
tags: ['以太坊', '区块链']
---


`--debug`：日志显示文件和行数
```
geth --debug --datadir node0 [其他参数]

INFO [02-01|14:59:47|miner/worker.go:539]              Commit new mining work                   number=1 txs=0 elapsed=628.966µs
```

`--pprof`：节点开启http服务用来显示prof信息，网址和端口可以通过`--pprofaddr, --pprofport`指定，默认是`127.0.0.1:6060`。
```
geth --pprof --datadir node0 [其他参数]
```
打开网址：`http://127.0.0.1:6060/debug/pprof/`
