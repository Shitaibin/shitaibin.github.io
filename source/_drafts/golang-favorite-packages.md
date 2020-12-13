---
title: golang-favorite-packages
tags: ['Go']
---



## log

> 日志级别怎么选？看[Dave大神的文章](https://dave.cheney.net/2015/11/05/lets-talk-about-logging)

### zap

[zap](https://github.com/uber-go/zap)由Uber开源，收藏量第二，号称最快的logger，可以看项目Readme的benchmark。

下载zap：
```bash
go get go.uber.org/zap
```

样例：
```go
func main() {
	sugar := zap.NewExample().Sugar()
	defer sugar.Sync()
	sugar.Infow("failed to fetch URL",
		"url", "http://example.com",
		"attempt", 3,
		"backoff", time.Second,
	)
	sugar.Infof("failed to fetch URL: %s", "http://example.com")
}
```

默认Json格式化结果：
```json
{"level":"info","msg":"failed to fetch URL","url":"http://example.com","attempt":3,"backoff":"1s"}
{"level":"info","msg":"failed to fetch URL: http://example.com"}
```

样例2，`NewProduction()`，打印Info及以上的日志，格式是Json：
```go
func main() {
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("can't initialize zap logger: %v", err)
	}
	defer logger.Sync()

	sugar := logger.Sugar()
	sugar.Infow("msg title", "name", "value", "error code", -1)
}
```

结果：
```json
{"level":"info","ts":1552972483.9980822,"caller":"gos/x.go:17","msg":"msg title","name":"value","error code":404}
```

样例3，`NewDevelopment()`，打印Debug及以上日志，并且是容易看的格式:
```go
func main() {
	logger, err := zap.NewDevelopment()
	if err != nil {
		log.Fatalf("can't initialize zap logger: %v", err)
	}
	defer logger.Sync()

	sugar := logger.Sugar()
	sugar.Infow("msg title", "name", "value", "error code", -1)
}
```

结果：
```json
2019-03-19T13:18:24.309+0800	INFO	gos/x.go:17	msg title	{"name": "value", "error code": -1}
```

更多zap资料请看[文档](godoc.org/go.uber.org/zap)。

### logrus

[logrus](https://github.com/Sirupsen/logrus)收藏最高的Go logger，好看，支持Json格式的日志。




