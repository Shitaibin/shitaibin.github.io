---
title: 通过Fabric 1.4 的Makefile，轻松掌握Fabric构建
date: 2019-07-10 07:18:48
tags: ['Fabric', 'Makefile', '区块链']
---


初次接触fabric会遇到各种构建问题，坑很多，网上有各种规避办法，但规避不是解决办法，所以决定把fabric的Makefile扫一遍。

fabric的Makefile包含了fabric所有的构建信息，掌握了这个Makefile，遇到任何构建问题，我相信你都能找到问题的根源，并从根上解决问题。而不是遇到问题，就网上找资料，结果做了很多无用功，也无法解决问题。

Makefile文件就在fabric的根目录下，该文件还引入了另外2个Makefile文件：

1. docker-env.mk，这个文件描述了Docker构建先关的信息
2. gotools.mk，这个文件描述了go tools相关的构建信息

我们先介绍Makefile文件，然后介绍另外2个文件，如果想在Makefile遇到这2个文件的时候查看，可随时使用目录跳转去查看即可。

即使掌握了Makefile，仍然会遇到一些问题，所以最后会给出一些建议，让你少踩一些坑。

> 本文基于fabric 1.4，commit id：9dce73，不同版本可能有细微差别，但不影响掌握构建过程。

# Makefile详细解读

Makefile看起来有点长，磨刀不误砍柴工，花2个小时，是非常有益处的，建议多看几遍，吃透编译流程。

## fabric的Makefile

```mk
# Copyright IBM Corp All Rights Reserved.
# Copyright London Stock Exchange Group All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
# -------------------------------------------------------------
# This makefile defines the following targets
#
# make项列表
#
# 构建所有
#   - all (default) - builds all targets and runs all non-integration tests/checks
# 运行所有测试和检查
#   - checks - runs all non-integration tests/checks
# 运行linter和verify来检查改动的文件
#   - desk-check - runs linters and verify to test changed packages
# 构建configtxgen，主要用来创建创世块、创建通道时的配置交易、更新通道的锚点交易
#   - configtxgen - builds a native configtxgen binary
# 构建configtxlator，configtxgen生成的配置是二进制，使用configtxlator转换为json
#   - configtxlator - builds a native configtxlator binary
# 构建cryptogen，提供加解密的程序
#   - cryptogen  -  builds a native cryptogen binary
# 构建idemixgen，用来创建身份（id）混合器创建配置文件
#   - idemixgen  -  builds a native idemixgen binary
# peer节点
#   - peer - builds a native fabric peer binary
# 排序节点
#   - orderer - builds a native fabric orderer binary
# 发布当前平台的包
#   - release - builds release packages for the host platform
# 发布所有平台的包
#   - release-all - builds release packages for all target platforms
# 跑单元测试
#   - unit-test - runs the go-test based unit tests
# 对更改过的文件跑单元测试
#   - verify - runs unit tests for only the changed package tree
# 以coverprofile模式对所有pkg跑单元测试
#   - profile - runs unit tests for all packages in coverprofile mode (slow)
#   - test-cmd - generates a "go test" string suitable for manual customization
# 安装go tools，TODO 安装到哪，镜像还是外部GOPATH下？
#   - gotools - installs go tools like golint
# 对所有代码运行lint
#   - linter - runs all code checks
# 检查dep依赖
#   - check-deps - check for vendored dependencies that are no longer used
# 检查所有代码Apache license
#   - license - checks go source files for Apache license header
# 构建所有的native程序，包含peer，orderer等
#   - native - ensures all native binaries are available
# 构建所有的docker镜像，docker-clean为清除镜像
#   - docker[-clean] - ensures all docker images are available[/cleaned]
# 列出所有相关的docker镜像
#   - docker-list - generates a list of docker images that 'make docker' produces
# 构建peer-docker镜像
#   - peer-docker[-clean] - ensures the peer container is available[/cleaned]
# 构建orderer-docker镜像
#   - orderer-docker[-clean] - ensures the orderer container is available[/cleaned]
# 构建tools-docker镜像
#   - tools-docker[-clean] - ensures the tools container is available[/cleaned]
# 基于.proto文件生成所有的protobuf文件
#   - protos - generate all protobuf artifacts based on .proto files
# 清理所有构建数据
#   - clean - cleans the build area
# 比clean更牛，还会清理掉持久状态数据
#   - clean-all - superset of 'clean' that also removes persistent state
# 清理发布的包
#   - dist-clean - clean release packages for all target platforms
# 清理单元测试状态数据
#   - unit-test-clean - cleans unit test state (particularly from docker)
# 执行基本的检查，比如license，拼写，lint等
#   - basic-checks - performs basic checks like license, spelling, trailing spaces and linter
# CI使用的选项
#   - enable_ci_only_tests - triggers unit-tests in downstream jobs. Applicable only for CI not to
#     use in the local machine.
# 拉去第三方docker镜像
#   - docker-thirdparty - pulls thirdparty images (kafka,zookeeper,couchdb)
# 把所有make docker所产生的镜像，打上latest tag
#   - docker-tag-latest - re-tags the images made by 'make docker' with the :latest tag
# 把所有make docker所产生的镜像，打上stable tag
#   - docker-tag-stable - re-tags the images made by 'make docker' with the :stable tag
# 生成命令参考文档
#   - help-docs - generate the command reference docs

# 基础版本
BASE_VERSION = 1.4.2
# 前一个版本
PREV_VERSION = 1.4.1
# chaintool版本
CHAINTOOL_RELEASE=1.1.3
# 基础镜像版本
BASEIMAGE_RELEASE=0.4.15

# 设置项目名称，如果没有设置，则使用hyperledger
# Allow to build as a submodule setting the main project to
# the PROJECT_NAME env variable, for example,
# export PROJECT_NAME=hyperledger/fabric-test
ifeq ($(PROJECT_NAME),true)
PROJECT_NAME = $(PROJECT_NAME)/fabric
else
PROJECT_NAME = hyperledger/fabric
endif

# 构建路径
# ?=指当没有指定BUILD_DIR时，才使用默认的`.build`作为构建目录
BUILD_DIR ?= .build
# 未知，全文未使用
NEXUS_REPO = nexus3.hyperledger.org:10001/hyperledger

# 额外版本：git commit号
EXTRA_VERSION ?= $(shell git rev-parse --short HEAD)
# 项目版本由基础版本和额外版本组成
PROJECT_VERSION=$(BASE_VERSION)-snapshot-$(EXTRA_VERSION)

# Go编译信息
# 设置包名
PKGNAME = github.com/$(PROJECT_NAME)
# CGO编译选项
CGO_FLAGS = CGO_CFLAGS=" "
# 当前CPU架构
ARCH=$(shell go env GOARCH)
# OS和CPU架构
MARCH=$(shell go env GOOS)-$(shell go env GOARCH)

# Go编译时传入的版本信息，主要是docker相关信息，比如
## var Version string = "latest"
## var CommitSHA string = "development build"
## var BaseVersion string = "0.4.15"
## var BaseDockerLabel string = "org.hyperledger.fabric"
## var DockerNamespace string = "hyperledger"
## var BaseDockerNamespace string = "hyperledger"

# defined in common/metadata/metadata.go
METADATA_VAR = Version=$(BASE_VERSION)
METADATA_VAR += CommitSHA=$(EXTRA_VERSION)
METADATA_VAR += BaseVersion=$(BASEIMAGE_RELEASE)
METADATA_VAR += BaseDockerLabel=$(BASE_DOCKER_LABEL)
METADATA_VAR += DockerNamespace=$(DOCKER_NS)
METADATA_VAR += BaseDockerNamespace=$(BASE_DOCKER_NS)

# 使用GO_LDFLAGS设置go的ldflag信息，传入METADATA_VAR
# patsubst指替换通配符
GO_LDFLAGS = $(patsubst %,-X $(PKGNAME)/common/metadata.%,$(METADATA_VAR))

GO_TAGS ?=

# chaintool下载链接
CHAINTOOL_URL ?= https://nexus.hyperledger.org/content/repositories/releases/org/hyperledger/fabric/hyperledger-fabric/chaintool-$(CHAINTOOL_RELEASE)/hyperledger-fabric-chaintool-$(CHAINTOOL_RELEASE).jar

export GO_LDFLAGS GO_TAGS

# 检查go、docker、git、curl这几个程序是否存在
EXECUTABLES ?= go docker git curl
K := $(foreach exec,$(EXECUTABLES),\
	$(if $(shell which $(exec)),some string,$(error "No $(exec) in PATH: Check dependencies")))

# Go shim的依赖项，shim是chaincode的一个模块，可以先不去理解
GOSHIM_DEPS = $(shell ./scripts/goListFiles.sh $(PKGNAME)/core/chaincode/shim)

# protobuf相关的文件
PROTOS = $(shell git ls-files *.proto | grep -Ev 'vendor/|testdata/')

# 项目文件，不包含git、样例、图片、vendor等文件
# No sense rebuilding when non production code is changed
PROJECT_FILES = $(shell git ls-files  | grep -v ^test | grep -v ^unit-test | \
	grep -v ^.git | grep -v ^examples | grep -v ^devenv | grep -v .png$ | \
	grep -v ^LICENSE | grep -v ^vendor )
# docker镜像发布模板
RELEASE_TEMPLATES = $(shell git ls-files | grep "release/templates")
# 镜像列表
IMAGES = peer orderer ccenv buildenv tools
# 发布平台
RELEASE_PLATFORMS = windows-amd64 darwin-amd64 linux-amd64 linux-s390x linux-ppc64le
# 发布的package
RELEASE_PKGS = configtxgen cryptogen idemixgen discover configtxlator peer orderer

# 要发的pkg和它们的路径
pkgmap.cryptogen      := $(PKGNAME)/common/tools/cryptogen
pkgmap.idemixgen      := $(PKGNAME)/common/tools/idemixgen
pkgmap.configtxgen    := $(PKGNAME)/common/tools/configtxgen
pkgmap.configtxlator  := $(PKGNAME)/common/tools/configtxlator
pkgmap.peer           := $(PKGNAME)/peer
pkgmap.orderer        := $(PKGNAME)/orderer
pkgmap.block-listener := $(PKGNAME)/examples/events/block-listener
pkgmap.discover       := $(PKGNAME)/cmd/discover

# 把docker-env.mk包含进来，主要是docker构建相关的选项
include docker-env.mk

# all包含/依赖了编译程序、编译镜像和进行检查
# all会进行检查，本地编译和发布docker镜像
all: native docker checks

# 检查包含/依赖了基本检查、单元测试和集成测试
checks: basic-checks unit-test integration-test

# 基本检查指许可证、拼写和格式
basic-checks: license spelling trailing-spaces linter check-metrics-doc

# 包含/依赖检查和验证
desk-check: checks verify

help-docs: native
	@scripts/generateHelpDocs.sh

# 拉取第三方镜像，并打上tag，BASE_DOCKER_TAG定义在docker-env.mk
# 都是fabric定制的couchdb、zookeeper、kafka镜像
# Pull thirdparty docker images based on the latest baseimage release version
.PHONY: docker-thirdparty
docker-thirdparty:
	docker pull $(BASE_DOCKER_NS)/fabric-couchdb:$(BASE_DOCKER_TAG)
	docker tag $(BASE_DOCKER_NS)/fabric-couchdb:$(BASE_DOCKER_TAG) $(DOCKER_NS)/fabric-couchdb
	docker pull $(BASE_DOCKER_NS)/fabric-zookeeper:$(BASE_DOCKER_TAG)
	docker tag $(BASE_DOCKER_NS)/fabric-zookeeper:$(BASE_DOCKER_TAG) $(DOCKER_NS)/fabric-zookeeper
	docker pull $(BASE_DOCKER_NS)/fabric-kafka:$(BASE_DOCKER_TAG)
	docker tag $(BASE_DOCKER_NS)/fabric-kafka:$(BASE_DOCKER_TAG) $(DOCKER_NS)/fabric-kafka

# 调用脚本执行拼写检查
.PHONY: spelling
spelling:
	@scripts/check_spelling.sh

# 调用脚本执行许可证检查
.PHONY: license
license:
	@scripts/check_license.sh

# 调用脚本执行末尾空格检查
.PHONY: trailing-spaces
trailing-spaces:
	@scripts/check_trailingspaces.sh

# 包含gotools.mk，这个文件主要用来安装一些gotools，可以使用单个命令来装某个gotools，比如安装dep
# `make gotool.dep`，具体见该文件
include gotools.mk

# 实际调用gotools-install安装相关的gotools
.PHONY: gotools
gotools: gotools-install

# 以下这段设置是各程序的依赖
# 编译peer，依赖./build/bin/peer
# 编译peer-docker，依赖./build/image/peer/$(DUMMY)，DUMMY指DOCKER-TAG，定义在docker-env.mk
.PHONY: peer
peer: $(BUILD_DIR)/bin/peer
peer-docker: $(BUILD_DIR)/image/peer/$(DUMMY)

# orderer和镜像的依赖
.PHONY: orderer
orderer: $(BUILD_DIR)/bin/orderer
orderer-docker: $(BUILD_DIR)/image/orderer/$(DUMMY)

# 编译configtxgen的依赖
.PHONY: configtxgen
configtxgen: GO_LDFLAGS=-X $(pkgmap.$(@F))/metadata.CommitSHA=$(EXTRA_VERSION)
configtxgen: $(BUILD_DIR)/bin/configtxgen

# 编译configtxlator的依赖
configtxlator: GO_LDFLAGS=-X $(pkgmap.$(@F))/metadata.CommitSHA=$(EXTRA_VERSION)
configtxlator: $(BUILD_DIR)/bin/configtxlator

# 编译cryptogen的依赖
cryptogen: GO_LDFLAGS=-X $(pkgmap.$(@F))/metadata.CommitSHA=$(EXTRA_VERSION)
cryptogen: $(BUILD_DIR)/bin/cryptogen

# 编译idemixgen的依赖
idemixgen: GO_LDFLAGS=-X $(pkgmap.$(@F))/metadata.CommitSHA=$(EXTRA_VERSION)
idemixgen: $(BUILD_DIR)/bin/idemixgen

# 编译discover的依赖
discover: GO_LDFLAGS=-X $(pkgmap.$(@F))/metadata.Version=$(PROJECT_VERSION)
discover: $(BUILD_DIR)/bin/discover

# 编译tools相关的docker
tools-docker: $(BUILD_DIR)/image/tools/$(DUMMY)

# 生成构建环境（buildenv)镜像
buildenv: $(BUILD_DIR)/image/buildenv/$(DUMMY)

# 未知
ccenv: $(BUILD_DIR)/image/ccenv/$(DUMMY)

# 进行集成测试
.PHONY: integration-test
integration-test: gotool.ginkgo ccenv docker-thirdparty
	./scripts/run-integration-tests.sh

# 进行单元测试
unit-test: unit-test-clean peer-docker docker-thirdparty ccenv
	unit-test/run.sh

# 进行单元测试
unit-tests: unit-test

# CI选项
enable_ci_only_tests: unit-test

# 运行verify，就像注释说的，依然是单元测试
verify: export JOB_TYPE=VERIFY
verify: unit-test

# 运行带有profile的单元测试
profile: export JOB_TYPE=PROFILE
profile: unit-test

# Generates a string to the terminal suitable for manual augmentation / re-issue, useful for running tests by hand
test-cmd:
	@echo "go test -tags \"$(GO_TAGS)\""

# 编译所有docker镜像，依赖都是.build/image下
docker: $(patsubst %,$(BUILD_DIR)/image/%/$(DUMMY), $(IMAGES))

# 编译所有native程序，native指所有fabric本身的程序，依赖如下
native: peer orderer configtxgen cryptogen idemixgen configtxlator discover

# 运行linter
linter: check-deps buildenv
	@echo "LINT: Running code checks.."
	@$(DRUN) $(DOCKER_NS)/fabric-buildenv:$(DOCKER_TAG) ./scripts/golinter.sh

# 运行check-deps
check-deps: buildenv
	@echo "DEP: Checking for dependency issues.."
	@$(DRUN) $(DOCKER_NS)/fabric-buildenv:$(DOCKER_TAG) ./scripts/check_deps.sh

# 运行check-metrics-doc
check-metrics-doc: buildenv
	@echo "METRICS: Checking for outdated reference documentation.."
	@$(DRUN) $(DOCKER_NS)/fabric-buildenv:$(DOCKER_TAG) ./scripts/metrics_doc.sh check

# 运行generate-metrics-doc
generate-metrics-doc: buildenv
	@echo "Generating metrics reference documentation..."
	@$(DRUN) $(DOCKER_NS)/fabric-buildenv:$(DOCKER_TAG) ./scripts/metrics_doc.sh generate

# 安装chain tool
$(BUILD_DIR)/%/chaintool: Makefile
	@echo "Installing chaintool"
	@mkdir -p $(@D)
	curl -fL $(CHAINTOOL_URL) > $@
	chmod +x $@

# We (re)build a package within a docker context but persist the $GOPATH/pkg
# directory so that subsequent builds are faster
# 构建所有镜像和pkg
# DRUN是`docker run`和参数的简写
# 本地创建docker里要用到的gopath目录，然后挂载到docker里
# 然后在docker里按个编译pkgmap里面的程序，比如peer、orderer、cryptogen等等
$(BUILD_DIR)/docker/bin/%: $(PROJECT_FILES)
	$(eval TARGET = ${patsubst $(BUILD_DIR)/docker/bin/%,%,${@}})
	@echo "Building $@"
	@mkdir -p $(BUILD_DIR)/docker/bin $(BUILD_DIR)/docker/$(TARGET)/pkg
	@$(DRUN) \
		-v $(abspath $(BUILD_DIR)/docker/bin):/opt/gopath/bin \
		-v $(abspath $(BUILD_DIR)/docker/$(TARGET)/pkg):/opt/gopath/pkg \
		$(BASE_DOCKER_NS)/fabric-baseimage:$(BASE_DOCKER_TAG) \
		go install -tags "$(GO_TAGS)" -ldflags "$(DOCKER_GO_LDFLAGS)" $(pkgmap.$(@F))
	@touch $@

# 创建本地bin目录
$(BUILD_DIR)/bin:
	mkdir -p $@

# 运行changelog
changelog:
	./scripts/changelog.sh v$(PREV_VERSION) v$(BASE_VERSION)

# protoc-gen-go依赖.build/docker/gotools
$(BUILD_DIR)/docker/gotools/bin/protoc-gen-go: $(BUILD_DIR)/docker/gotools

# 构建go tools的docker镜像，给payload使用
# 创建本地目录(.build/docker/gotools)并挂载到(/opt/gotools)，依赖基础镜像，然后在docker中执行gotools.mk
# 最后调用gotools.mk生成程序，设置了GOTOOLS_BINDIR，生成的二进制会放在这个目录，因为这个目录映射了出来，
# 所以bin就在主机的`.build/docker/gotools/bin/`目录
# So, 如果构建成功，不需要像其他文章说的那样，需要手动拷贝protoc-gen-go到`.build/docker/gotools/bin/`目录
# 但是，如果翻墙失败，可以考虑手动复制protoc-gen-go的方式
$(BUILD_DIR)/docker/gotools: gotools.mk
	@echo "Building dockerized gotools"
	@mkdir -p $@/bin $@/obj
	@$(DRUN) \
		-v $(abspath $@):/opt/gotools \
		-w /opt/gopath/src/$(PKGNAME) \
		$(BASE_DOCKER_NS)/fabric-baseimage:$(BASE_DOCKER_TAG) \
		make -f gotools.mk GOTOOLS_BINDIR=/opt/gotools/bin GOTOOLS_GOPATH=/opt/gotools/obj

# 构建本地的运行文件，依赖设置都在上面了，这是进行构建，与Docker类似
# 程序即pkgmap中的程序
$(BUILD_DIR)/bin/%: $(PROJECT_FILES)
	@mkdir -p $(@D)
	@echo "$@"
	$(CGO_FLAGS) GOBIN=$(abspath $(@D)) go install -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))
	@echo "Binary available as $@"
	@touch $@

# 设置各镜像各自的payload文件
# 比如ccenv的payload拷贝会翻译成：cp .build/docker/gotools/bin/protoc-gen-go .build/bin/chaintool .build/goshim.tar.bz2 .build/image/ccenv/payload
# payload definitions'
$(BUILD_DIR)/image/ccenv/payload:      $(BUILD_DIR)/docker/gotools/bin/protoc-gen-go \
				$(BUILD_DIR)/bin/chaintool \
				$(BUILD_DIR)/goshim.tar.bz2
$(BUILD_DIR)/image/peer/payload:       $(BUILD_DIR)/docker/bin/peer \
				$(BUILD_DIR)/sampleconfig.tar.bz2
$(BUILD_DIR)/image/orderer/payload:    $(BUILD_DIR)/docker/bin/orderer \
				$(BUILD_DIR)/sampleconfig.tar.bz2
$(BUILD_DIR)/image/buildenv/payload:   $(BUILD_DIR)/gotools.tar.bz2 \
				$(BUILD_DIR)/docker/gotools/bin/protoc-gen-go

# 各镜像payload的实际拷贝
$(BUILD_DIR)/image/%/payload:
	mkdir -p $@
	cp $^ $@

.PRECIOUS: $(BUILD_DIR)/image/%/Dockerfile

# 根据image下的各目录中的Dockerfile.in生成对应的Dockerfile
$(BUILD_DIR)/image/%/Dockerfile: images/%/Dockerfile.in
	mkdir -p $(@D)
	@cat $< \
		| sed -e 's|_BASE_NS_|$(BASE_DOCKER_NS)|g' \
		| sed -e 's|_NS_|$(DOCKER_NS)|g' \
		| sed -e 's|_BASE_TAG_|$(BASE_DOCKER_TAG)|g' \
		| sed -e 's|_TAG_|$(DOCKER_TAG)|g' \
		> $@
	@echo LABEL $(BASE_DOCKER_LABEL).version=$(BASE_VERSION) \\>>$@
	@echo "     " $(BASE_DOCKER_LABEL).base.version=$(BASEIMAGE_RELEASE)>>$@

# 根据Dockerfile生成tools-image，并打上2个tag，分别是当前版本tag和latest tag
$(BUILD_DIR)/image/tools/$(DUMMY): $(BUILD_DIR)/image/tools/Dockerfile
	$(eval TARGET = ${patsubst $(BUILD_DIR)/image/%/$(DUMMY),%,${@}})
	@echo "Building docker $(TARGET)-image"
	$(DBUILD) -t $(DOCKER_NS)/fabric-$(TARGET) -f $(@D)/Dockerfile .
	docker tag $(DOCKER_NS)/fabric-$(TARGET) $(DOCKER_NS)/fabric-$(TARGET):$(DOCKER_TAG)
	docker tag $(DOCKER_NS)/fabric-$(TARGET) $(DOCKER_NS)/fabric-$(TARGET):$(ARCH)-latest
	@touch $@

# 根据Dockerfile、payload生成image下的所有镜像，比如orderer，然后打上tag
$(BUILD_DIR)/image/%/$(DUMMY): Makefile $(BUILD_DIR)/image/%/payload $(BUILD_DIR)/image/%/Dockerfile
	$(eval TARGET = ${patsubst $(BUILD_DIR)/image/%/$(DUMMY),%,${@}})
	@echo "Building docker $(TARGET)-image"
	$(DBUILD) -t $(DOCKER_NS)/fabric-$(TARGET) $(@D)
	docker tag $(DOCKER_NS)/fabric-$(TARGET) $(DOCKER_NS)/fabric-$(TARGET):$(DOCKER_TAG)
	docker tag $(DOCKER_NS)/fabric-$(TARGET) $(DOCKER_NS)/fabric-$(TARGET):$(ARCH)-latest
	@touch $@

# 打包gotools
$(BUILD_DIR)/gotools.tar.bz2: $(BUILD_DIR)/docker/gotools
	(cd $</bin && tar -jc *) > $@

# 打包goshim
$(BUILD_DIR)/goshim.tar.bz2: $(GOSHIM_DEPS)
	@echo "Creating $@"
	@tar -jhc -C $(GOPATH)/src $(patsubst $(GOPATH)/src/%,%,$(GOSHIM_DEPS)) > $@

# 打包sampleconfig
$(BUILD_DIR)/sampleconfig.tar.bz2: $(shell find sampleconfig -type f)
	(cd sampleconfig && tar -jc *) > $@

# 打包protos
$(BUILD_DIR)/protos.tar.bz2: $(PROTOS)

$(BUILD_DIR)/%.tar.bz2:
	@echo "Creating $@"
	@tar -jc $^ > $@

# 发布当前平台的relase包
# builds release packages for the host platform
release: $(patsubst %,release/%, $(MARCH))

# builds release packages for all target platforms
release-all: $(patsubst %,release/%, $(RELEASE_PLATFORMS))

release/%: GO_LDFLAGS=-X $(pkgmap.$(@F))/metadata.CommitSHA=$(EXTRA_VERSION)

release/windows-amd64: GOOS=windows
release/windows-amd64: $(patsubst %,release/windows-amd64/bin/%, $(RELEASE_PKGS))

release/darwin-amd64: GOOS=darwin
release/darwin-amd64: $(patsubst %,release/darwin-amd64/bin/%, $(RELEASE_PKGS))

release/linux-amd64: GOOS=linux
release/linux-amd64: $(patsubst %,release/linux-amd64/bin/%, $(RELEASE_PKGS))

release/%-amd64: GOARCH=amd64
release/linux-%: GOOS=linux

release/linux-s390x: GOARCH=s390x
release/linux-s390x: $(patsubst %,release/linux-s390x/bin/%, $(RELEASE_PKGS))

release/linux-ppc64le: GOARCH=ppc64le
release/linux-ppc64le: $(patsubst %,release/linux-ppc64le/bin/%, $(RELEASE_PKGS))

release/%/bin/configtxlator: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

release/%/bin/configtxgen: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

release/%/bin/cryptogen: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

release/%/bin/idemixgen: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

release/%/bin/discover: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

release/%/bin/orderer: GO_LDFLAGS = $(patsubst %,-X $(PKGNAME)/common/metadata.%,$(METADATA_VAR))

release/%/bin/orderer: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

release/%/bin/peer: GO_LDFLAGS = $(patsubst %,-X $(PKGNAME)/common/metadata.%,$(METADATA_VAR))

release/%/bin/peer: $(PROJECT_FILES)
	@echo "Building $@ for $(GOOS)-$(GOARCH)"
	mkdir -p $(@D)
	$(CGO_FLAGS) GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(abspath $@) -tags "$(GO_TAGS)" -ldflags "$(GO_LDFLAGS)" $(pkgmap.$(@F))

.PHONY: dist
dist: dist-clean dist/$(MARCH)

dist-all: dist-clean $(patsubst %,dist/%, $(RELEASE_PLATFORMS))

dist/%: release/%
	mkdir -p release/$(@F)/config
	cp -r sampleconfig/*.yaml release/$(@F)/config
	cd release/$(@F) && tar -czvf hyperledger-fabric-$(@F).$(PROJECT_VERSION).tar.gz *

# 在docker中生成protobuf文件
.PHONY: protos
protos: buildenv
	@$(DRUN) $(DOCKER_NS)/fabric-buildenv:$(DOCKER_TAG) ./scripts/compile_protos.sh

%-docker-list:
	$(eval TARGET = ${patsubst %-docker-list,%,${@}})
	@echo $(DOCKER_NS)/fabric-$(TARGET):$(DOCKER_TAG)

# 列出当前所有镜像
docker-list: $(patsubst %,%-docker-list, $(IMAGES))

%-docker-clean:
	$(eval TARGET = ${patsubst %-docker-clean,%,${@}})
	-docker images --quiet --filter=reference='$(DOCKER_NS)/fabric-$(TARGET):$(ARCH)-$(BASE_VERSION)$(if $(EXTRA_VERSION),-snapshot-*,)' | xargs docker rmi -f
	-@rm -rf $(BUILD_DIR)/image/$(TARGET) ||:

# 清理所有镜像
docker-clean: $(patsubst %,%-docker-clean, $(IMAGES))

docker-tag-latest: $(IMAGES:%=%-docker-tag-latest)

%-docker-tag-latest:
	$(eval TARGET = ${patsubst %-docker-tag-latest,%,${@}})
	docker tag $(DOCKER_NS)/fabric-$(TARGET):$(DOCKER_TAG) $(DOCKER_NS)/fabric-$(TARGET):latest

docker-tag-stable: $(IMAGES:%=%-docker-tag-stable)

%-docker-tag-stable:
	$(eval TARGET = ${patsubst %-docker-tag-stable,%,${@}})
	docker tag $(DOCKER_NS)/fabric-$(TARGET):$(DOCKER_TAG) $(DOCKER_NS)/fabric-$(TARGET):stable

.PHONY: clean
clean: docker-clean unit-test-clean release-clean
	-@rm -rf $(BUILD_DIR)

# 清理所有状态数据，依赖tools清理，发包清理
.PHONY: clean-all
clean-all: clean gotools-clean dist-clean
	-@rm -rf /var/hyperledger/*
	-@rm -rf docs/build/

# 发布版本清理
.PHONY: dist-clean
dist-clean:
	-@rm -rf release/windows-amd64/hyperledger-fabric-windows-amd64.$(PROJECT_VERSION).tar.gz
	-@rm -rf release/darwin-amd64/hyperledger-fabric-darwin-amd64.$(PROJECT_VERSION).tar.gz
	-@rm -rf release/linux-amd64/hyperledger-fabric-linux-amd64.$(PROJECT_VERSION).tar.gz
	-@rm -rf release/linux-s390x/hyperledger-fabric-linux-s390x.$(PROJECT_VERSION).tar.gz
	-@rm -rf release/linux-ppc64le/hyperledger-fabric-linux-ppc64le.$(PROJECT_VERSION).tar.gz

%-release-clean:
	$(eval TARGET = ${patsubst %-release-clean,%,${@}})
	-@rm -rf release/$(TARGET)

# 发包清理
release-clean: $(patsubst %,%-release-clean, $(RELEASE_PLATFORMS))

# 单元测试清理
.PHONY: unit-test-clean
unit-test-clean:
	cd unit-test && docker-compose down
```

## docker env的Makefile

`docker-env.mk`主要是Docker镜像构建相关的设置。


```mk
// docker-env.mk
# Copyright London Stock Exchange Group All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Mac上设置--user选项
ifneq ($(shell uname),Darwin)
DOCKER_RUN_FLAGS=--user=$(shell id -u)
endif

# 架构是s390x，uid不是0（root账号）的时候，-v选项
ifeq ($(shell uname -m),s390x)
ifneq ($(shell id -u),0)
DOCKER_RUN_FLAGS+=-v /etc/passwd:/etc/passwd:ro
endif
endif

# 以下是http和https的代理设置
ifneq ($(http_proxy),)
DOCKER_BUILD_FLAGS+=--build-arg 'http_proxy=$(http_proxy)'
DOCKER_RUN_FLAGS+=-e 'http_proxy=$(http_proxy)'
endif
ifneq ($(https_proxy),)
DOCKER_BUILD_FLAGS+=--build-arg 'https_proxy=$(https_proxy)'
DOCKER_RUN_FLAGS+=-e 'https_proxy=$(https_proxy)'
endif
ifneq ($(HTTP_PROXY),)
DOCKER_BUILD_FLAGS+=--build-arg 'HTTP_PROXY=$(HTTP_PROXY)'
DOCKER_RUN_FLAGS+=-e 'HTTP_PROXY=$(HTTP_PROXY)'
endif
ifneq ($(HTTPS_PROXY),)
DOCKER_BUILD_FLAGS+=--build-arg 'HTTPS_PROXY=$(HTTPS_PROXY)'
DOCKER_RUN_FLAGS+=-e 'HTTPS_PROXY=$(HTTPS_PROXY)'
endif
ifneq ($(no_proxy),)
DOCKER_BUILD_FLAGS+=--build-arg 'no_proxy=$(no_proxy)'
DOCKER_RUN_FLAGS+=-e 'no_proxy=$(no_proxy)'
endif
ifneq ($(NO_PROXY),)
DOCKER_BUILD_FLAGS+=--build-arg 'NO_PROXY=$(NO_PROXY)'
DOCKER_RUN_FLAGS+=-e 'NO_PROXY=$(NO_PROXY)'
endif

# DRUN代表docker run，并伴随以下参数，把当前路径映射到容器的gopath对应路径下
# 并且设置容器内的工作目录
DRUN = docker run -i --rm $(DOCKER_RUN_FLAGS) \
	-v $(abspath .):/opt/gopath/src/$(PKGNAME) \
	-w /opt/gopath/src/$(PKGNAME)

# docker build
DBUILD = docker build $(DOCKER_BUILD_FLAGS)

# 基础docker namespace设置时，使用hyperledger
BASE_DOCKER_NS ?= hyperledger
# 基础docker tag，由arch和release组成docker tag
BASE_DOCKER_TAG=$(ARCH)-$(BASEIMAGE_RELEASE)

# 与上面类似
DOCKER_NS ?= hyperledger
DOCKER_TAG=$(ARCH)-$(PROJECT_VERSION)
PREV_TAG=$(ARCH)-$(PREV_VERSION)

# 基础镜像标签
BASE_DOCKER_LABEL=org.hyperledger.fabric

# 动态连接信息
DOCKER_DYNAMIC_LINK ?= false
# Docker内的ldfalgs信息，继承makefile的
DOCKER_GO_LDFLAGS += $(GO_LDFLAGS)

ifeq ($(DOCKER_DYNAMIC_LINK),false)
DOCKER_GO_LDFLAGS += -linkmode external -extldflags '-static -lpthread'
endif

#
# What is a .dummy file?
#
# Make is designed to work with files.  It uses the presence (or lack thereof)
# and timestamps of files when deciding if a given target needs to be rebuilt.
# Docker containers throw a wrench into the works because the output of docker
# builds do not translate into standard files that makefile rules can evaluate.
# Therefore, we have to fake it.  We do this by constructioning our rules such
# as
#       my-docker-target/.dummy:
#              docker build ...
#              touch $@
#
# If the docker-build succeeds, the touch operation creates/updates the .dummy
# file.  If it fails, the touch command never runs.  This means the .dummy
# file follows relatively 1:1 with the underlying container.
#
# This isn't perfect, however.  For instance, someone could delete a docker
# container using docker-rmi outside of the build, and make would be fooled
# into thinking the dependency is statisfied when it really isn't.  This is
# our closest approximation we can come up with.
#
# As an aside, also note that we incorporate the version number in the .dummy
# file to differentiate different tags to fix FAB-1145
#
DUMMY = .dummy-$(DOCKER_TAG)

# Make是跟文件打交道的，它使用文件位置（？）和时间戳觉得是否要重新构建文件。
# 但Docker容器产生的文件是make无法识别的。所以做了适配，docker build运行
# 成功时，touch回去创建或更新dummy文件，如果失败则touch不执行。
# 这样保证了dummy文件和容器保持一对一的关系。
```

## go tools的Makefile

gotools指的一些列go语言的工具，并不是golang/tools仓库，具体是哪些tools，请看Makefile文件解析。

这些tools的安装有2种方式：
1. 少数几个支持从vendor目录直接安装
2. 默认方式是使用go get方式安装，所以请**翻墙**

另外，gotools.mk实际是在docker中运行的，也就是生成的程序都在docker镜像中，在当前host并没有运行，具体看gotools.mk调用的地方。调用处把GOBIN设置为了`.build/docker/gotools/bin`，并映射到了docker，构建后可以查看生成的程序：

```bash
➜  fabric git:(r1.4) ls .build/docker/gotools/bin
counterfeiter  dep  ginkgo  gocov  gocov-xml  goimports  golint  manifest-tool  misspell  mockery  protoc-gen-go
```

Makefile注释：

```mk
// gotools.mk
# Copyright IBM Corp All Rights Reserved.
# Copyright London Stock Exchange Group All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0

# 所有相关的tools，之所以叫go tools，因为是Go语言的，并不是指golang/tools仓库
GOTOOLS = counterfeiter dep golint goimports protoc-gen-go ginkgo gocov gocov-xml misspell mockery manifest-tool
# 构建目录与Makefile保持一致
BUILD_DIR ?= .build
# 构建gotools是的GOPATH，也就源码所在目录，当未设置时，使用默认路径
GOTOOLS_GOPATH ?= $(BUILD_DIR)/gotools
# gotools的生成二进制位置，当未设置时，使用GOPATH/bin
GOTOOLS_BINDIR ?= $(GOPATH)/bin

# 每个tool的目录映射
# go tool->path mapping
go.fqp.counterfeiter := github.com/maxbrunsfeld/counterfeiter
go.fqp.gocov         := github.com/axw/gocov/gocov
go.fqp.gocov-xml     := github.com/AlekSi/gocov-xml
go.fqp.goimports     := golang.org/x/tools/cmd/goimports
go.fqp.golint        := golang.org/x/lint/golint
go.fqp.manifest-tool := github.com/estesp/manifest-tool
go.fqp.misspell      := github.com/client9/misspell/cmd/misspell
go.fqp.mockery       := github.com/vektra/mockery/cmd/mockery

# 安装所有tools
.PHONY: gotools-install
gotools-install: $(patsubst %,$(GOTOOLS_BINDIR)/%, $(GOTOOLS))

# 清理tools
.PHONY: gotools-clean
gotools-clean:
	-@rm -rf $(BUILD_DIR)/gotools

# 可以使用vendor中的版本构建部分tools，比如protoc-gen-go，ginkgo，goimports，golint
# Special override for protoc-gen-go since we want to use the version vendored with the project
gotool.protoc-gen-go:
	@echo "Building github.com/golang/protobuf/protoc-gen-go -> protoc-gen-go"
	GOBIN=$(abspath $(GOTOOLS_BINDIR)) go install ./vendor/github.com/golang/protobuf/protoc-gen-go

# Special override for ginkgo since we want to use the version vendored with the project
gotool.ginkgo:
	@echo "Building github.com/onsi/ginkgo/ginkgo -> ginkgo"
	GOBIN=$(abspath $(GOTOOLS_BINDIR)) go install ./vendor/github.com/onsi/ginkgo/ginkgo

# Special override for goimports since we want to use the version vendored with the project
gotool.goimports:
	@echo "Building golang.org/x/tools/cmd/goimports -> goimports"
	GOBIN=$(abspath $(GOTOOLS_BINDIR)) go install ./vendor/golang.org/x/tools/cmd/goimports

# Special override for golint since we want to use the version vendored with the project
gotool.golint:
	@echo "Building golang.org/x/lint/golint -> golint"
	GOBIN=$(abspath $(GOTOOLS_BINDIR)) go install ./vendor/golang.org/x/lint/golint

# go dep的构建，使用特定版本
# Lock to a versioned dep
gotool.dep: DEP_VERSION ?= "v0.5.1"
gotool.dep:
	@GOPATH=$(abspath $(GOTOOLS_GOPATH)) go get -d -u github.com/golang/dep
	@git -C $(abspath $(GOTOOLS_GOPATH))/src/github.com/golang/dep checkout -q $(DEP_VERSION)
	@echo "Building github.com/golang/dep $(DEP_VERSION) -> dep"
	@GOPATH=$(abspath $(GOTOOLS_GOPATH)) GOBIN=$(abspath $(GOTOOLS_BINDIR)) go install -ldflags="-X main.version=$(DEP_VERSION) -X main.buildDate=$$(date '+%Y-%m-%d')" github.com/golang/dep/cmd/dep
	@git -C $(abspath $(GOTOOLS_GOPATH))/src/github.com/golang/dep checkout -q master

# 所有tools构建时的默认安装方式，会使用go get从网络拉去
# Default rule for gotools uses the name->path map for a generic 'go get' style build
gotool.%:
	$(eval TOOL = ${subst gotool.,,${@}})
	@echo "Building ${go.fqp.${TOOL}} -> $(TOOL)"
	@GOPATH=$(abspath $(GOTOOLS_GOPATH)) GOBIN=$(abspath $(GOTOOLS_BINDIR)) go get ${go.fqp.${TOOL}}

$(GOTOOLS_BINDIR)/%:
	$(eval TOOL = ${subst $(GOTOOLS_BINDIR)/,,${@}})
	@$(MAKE) -f gotools.mk gotool.$(TOOL)
```



# 构建建议

列出几条构建建议，建议在make前先做好，会提高构建效率，并且少采坑。

## 翻墙

设置好翻墙，包括http和https代理，以便能下载Github，golang.org的包，参考[让终端科学上网](http://lessisbetter.site/2018/09/06/Science-and-the-Internet/)。

> 发文时fabric还使用的vendor，如果限制fabric已经使用go mod了，建议配置国内go modules代理，这样就无需翻墙了，参考本文[结束语](#结束语)。

## Linux系统包管理设置为国内的源，Mac上brew设置为腾讯源

参考[让镜像飞，加速你的开发](http://lessisbetter.site/2019/07/13/fast-mirrors/)。

## docker设置为国内的源

参考[Docker镜像加速](https://yeasy.gitbooks.io/docker_practice/install/mirror.html)。

## 检查GOPATH和PATH，以及http代理

确保配置正确：

```
echo $http_proxy
echo $https_proxy
echo $GOPATH
echo $PATH
```

## 安装docker-compose

centos7下请参考：
```
sudo curl -L "https://github.com/docker/compose/releases/download/1.23.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

sudo chmod +x /usr/local/bin/docker-compose

docker-compose --version
```

## Mac上安装Gnu-tar

如果未安装，可能遇到下面的错误：

```
Step 3/5 : ADD payload/goshim.tar.bz2 $GOPATH/src/
failed to copy files: Error processing tar file(bzip2 data invalid: bad magic value in continuation file):
make: [build/image/ccenv/.dummy-x86_64-1.0.7-snapshot-ac3fabd] Error 1
```

需要安装gnu-tar，用gnu-tar替换mac默认的bsdtar，可以用brew list gnu-tar找到gnu-tar的位置:

```
$ brew install gnu-tar
➜  fabric git:(yx-release-1.4) ✗ brew install gnu-tar
==> Reinstalling gnu-tar
==> Downloading https://mirrors.cloud.tencent.com/homebrew-bottles/bottles/gnu-tar-1.32.mojave.bottle.tar.gz
######################################################################## 100.0%
==> Pouring gnu-tar-1.32.mojave.bottle.tar.gz
==> Caveats
GNU "tar" has been installed as "gtar".
If you need to use it as "tar", you can add a "gnubin" directory
to your PATH from your bashrc like:

    PATH="/usr/local/opt/gnu-tar/libexec/gnubin:$PATH"
==> Summary
🍺  /usr/local/Cellar/gnu-tar/1.32: 15 files, 1.7MB
$ which tar
/usr/local/opt/gnu-tar/libexec/gnubin/tar
```

按提示设置PATH才可以使用gnu tar。`export PATH="/usr/local/opt/gnu-tar/libexec/gnubin:$PATH"`加入到`.zshrc`，不必每次构建都设置PATH，但这样会让Mac默认使用GNU tar。

需要`make clean`然后重新`make`，不然依然会遇到bad magic的问题。

## Git升级到2.22以上版本

如果未升级可能遇到上文提到的dep不存在的问题。

# 通过Makefile定位编译问题

这类问题是类似的，要找到报错的位置，是做哪项构建时报的错，以及报错位置的前提条件是什么，这里列举2个。

## dep不存在的问题


在执行`make all`的时候，遇到了`dep`不存在的问题：

```
DEP: Checking for dependency issues..
./scripts/check_deps.sh: line 7: dep: command not found
```

通过Makefile知道，dep属于gotools，单独执行`make gotools`查看问题。

```bash
➜  fabric git:(r1.4) ✗ make gotools
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building github.com/maxbrunsfeld/counterfeiter -> counterfeiter
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building golang.org/x/lint/golint -> golint
GOBIN=/home/centos/go/bin go install ./vendor/golang.org/x/lint/golint
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building golang.org/x/tools/cmd/goimports -> goimports
GOBIN=/home/centos/go/bin go install ./vendor/golang.org/x/tools/cmd/goimports
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building github.com/onsi/ginkgo/ginkgo -> ginkgo
GOBIN=/home/centos/go/bin go install ./vendor/github.com/onsi/ginkgo/ginkgo
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building github.com/axw/gocov/gocov -> gocov
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building github.com/AlekSi/gocov-xml -> gocov-xml
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building github.com/vektra/mockery/cmd/mockery -> mockery
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
make[1]: 进入目录“/home/centos/go/src/github.com/hyperledger/fabric”
Building github.com/estesp/manifest-tool -> manifest-tool
make[1]: 离开目录“/home/centos/go/src/github.com/hyperledger/fabric”
```

其中，果然没有安装dep，单独编译dep：

```bash
➜  fabric git:(r1.4) ✗ make gotool.dep
Unknown option: -C
usage: git [--version] [--help] [-c name=value]
           [--exec-path[=<path>]] [--html-path] [--man-path] [--info-path]
           [-p|--paginate|--no-pager] [--no-replace-objects] [--bare]
           [--git-dir=<path>] [--work-tree=<path>] [--namespace=<name>]
           <command> [<args>]
make: *** [gotool.dep] 错误 129
```
报错误，git没有`-C`选项，怀疑centos系统自带git太老，`git version`查看果然只有`1.9`。

按照Git的INSTALL文件指导安装git，详细见：https://github.com/git/git/blob/master/INSTALL ，下面是简要安装步骤。

通过wget下载最新的[git release](https://github.com/git/git/releases)，然后使用以下命令安装git到`/usr/bin`目录。

```bash
wget https://github.com/git/git/archive/v2.22.0.tar.gz
# 省略：解压然后进入该目录
make
make prefix=/usr install
```

验证git版本，和make dep。

```
➜  fabric git:(r1.4) ✗ git version
git version 2.22.0

➜  fabric git:(r1.4) ✗ make gotool.dep
Building github.com/golang/dep v0.5.1 -> dep
```

通过fabric Makefile可知`check_deps.sh`是`make check-deps`的一部分，执行`make check-deps`可以看到检查dep通过了。

```bash
➜  fabric git:(r1.4) make check-deps
DEP: Checking for dependency issues..
dep:
 version     : v0.5.1
 build date  : 2019-07-15
 git hash    :
 go version  : go1.11.5
 go compiler : gc
 platform    : linux/amd64
 features    : ImportDuringSolve=false
# out of sync, but ignored, due to noverify in Gopkg.toml:
github.com/grpc-ecosystem/go-grpc-middleware: hash of vendored tree not equal to digest in Gopkg.lock
```

## protoc-gen-go 不存在的问题

```bash
$ make all
mkdir -p .build/image/ccenv/payload
cp .build/docker/gotools/bin/protoc-gen-go .build/bin/chaintool .build/goshim.tar.bz2 .build/image/ccenv/payload
cp: .build/docker/gotools/bin/protoc-gen-go: No such file or directory
make: *** [.build/image/ccenv/payload] Error 1
```

查看构建日志是否有以下日志：

```
Building dockerized gotools
```

应当是不存在，不过构建存在错误，所以才没有构建出docker要使用的gotools。

解决办法是：

```bash
$ make clean
$ make .build/docker/gotools # 直接编译docker的gotools
```

如果报网络连接导致的错误，参考[终端科学上网](http://lessisbetter.site/2018/09/06/Science-and-the-Internet/)，然后重新执行，或者下面这种办法：

```bash
$ make gotools # 本地安装gotools
$ cp `which protoc-gen-go` .build/docker/gotools/bin/ # 拷贝到docker gotools目录
```

然后重新`make all`或`make docker`。

# 构建日志

构建日志比较长，放到了[附录](#附录)中，对构建日志加了注释，可根据构建日志进一步掌握构建过程。

# 镜像解读

通过`make all`或`make docker`可以生成fabric的所有镜像，这些镜像可以通过`make docker-list`查看，如果使用docker images查看，会看到更多的镜像，并且发现下面这5个镜像还有另外一个"lastest"的标签，看Makefile可以知道，其实是1个镜像2个标签而已。

```
➜  fabric git:(r1.4) make docker-list
hyperledger/fabric-peer:amd64-1.4.2-snapshot-9dce7357b
hyperledger/fabric-orderer:amd64-1.4.2-snapshot-9dce7357b
hyperledger/fabric-ccenv:amd64-1.4.2-snapshot-9dce7357b
hyperledger/fabric-buildenv:amd64-1.4.2-snapshot-9dce7357b
hyperledger/fabric-tools:amd64-1.4.2-snapshot-9dce7357b
```

- fabric-baseos: peer、orderer、链码容器的镜像所依赖的基础镜像。
- fabric-baseimage：是fabric-buildenv所依赖的镜像。
- fabric-peer：可以使用该镜像启动一个peer节点。
- fabric-orderer：可以使用该镜像启动一个排序节点。
- fabric-ccenv：peer进程使用ccenv来构建链码容器镜像，注意ccenv不是链码容器镜像的运行环境，链码容器镜像是基于baseos的。
- fabric-buildenv：实际包含的是go tools.tar.bz2和protoc-gen-go的镜像，Make时一些工具会使用该镜像。
- fabric-tools：是fabric自身tools集合的镜像。

这几个镜像的Dockerfile文件在：`images`目录下，各镜像具体内容见各自的Dockerfile。

```
➜  fabric git:(r1.4) tree images
images
├── buildenv
│   └── Dockerfile.in
├── ccenv
│   └── Dockerfile.in
├── orderer
│   └── Dockerfile.in
├── peer
│   └── Dockerfile.in
├── testenv
│   ├── Dockerfile.alpine
│   └── softhsm
│       └── APKBUILD
└── tools
    └── Dockerfile.in

7 directories, 7 files
```

# 结束语

现在国内已经有第三方的Go modules代理服务了，比如：

1. [goproxy.io](https://goproxy.io/zh/)，是即将毕业的[盛奥飞](https://github.com/aofei)小哥捐给了七牛搭建的Go modules代理服务。
2. [aliyun goproxy](http://mirrors.aliyun.com/goproxy/)，现在阿里云开放了Go modules代理服务。

fabric使用vendor，下载各种东西的时候需要翻墙，即便是可以翻墙，也是有缺点的：

1. 慢。
2. 翻墙有流量限制。

fabric赶紧支持go mod吧，这样再也不用翻墙了。

# 参考资料

1. [fabric工程项目构建Makefile翻译及解析](https://shanma.pro/tutorial/56688.html)

# 附录

一份构建日志：

```
➜  fabric git:(r1.4) ✗ make all
// 构建native那些程序，等价make native
// peer
.build/bin/peer
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/metadata.Version=1.4.2 -X github.com/hyperledger/fabric/common/metadata.CommitSHA=9dce735 -X github.com/hyperledger/fabric/common/metadata.BaseVersion=0.4.15 -X github.com/hyperledger/fabric/common/metadata.BaseDockerLabel=org.hyperledger.fabric -X github.com/hyperledger/fabric/common/metadata.DockerNamespace=hyperledger -X github.com/hyperledger/fabric/common/metadata.BaseDockerNamespace=hyperledger" github.com/hyperledger/fabric/peer
Binary available as .build/bin/peer
// orderer
.build/bin/orderer
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/metadata.Version=1.4.2 -X github.com/hyperledger/fabric/common/metadata.CommitSHA=9dce735 -X github.com/hyperledger/fabric/common/metadata.BaseVersion=0.4.15 -X github.com/hyperledger/fabric/common/metadata.BaseDockerLabel=org.hyperledger.fabric -X github.com/hyperledger/fabric/common/metadata.DockerNamespace=hyperledger -X github.com/hyperledger/fabric/common/metadata.BaseDockerNamespace=hyperledger" github.com/hyperledger/fabric/orderer
Binary available as .build/bin/orderer
// configtxgen
.build/bin/configtxgen
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/configtxgen/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/configtxgen
Binary available as .build/bin/configtxgen
// cryptogen
.build/bin/cryptogen
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/cryptogen/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/cryptogen
Binary available as .build/bin/cryptogen
// idemixgen
.build/bin/idemixgen
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/idemixgen/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/idemixgen
Binary available as .build/bin/idemixgen
// configtxlator
.build/bin/configtxlator
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/configtxlator/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/configtxlator
Binary available as .build/bin/configtxlator
// discover
.build/bin/discover
CGO_CFLAGS=" " GOBIN=/home/centos/go/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/cmd/discover/metadata.Version=1.4.2-snapshot-9dce735" github.com/hyperledger/fabric/cmd/discover
Binary available as .build/bin/discover

// 以下这部分等价make docker
// 构建peer镜像
Building .build/docker/bin/peer
# github.com/hyperledger/fabric/peer
/tmp/go-link-829040977/000006.o: In function `pluginOpen':
/workdir/go/src/plugin/plugin_dlopen.go:19: warning: Using 'dlopen' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-829040977/000021.o: In function `mygetgrouplist':
/workdir/go/src/os/user/getgrouplist_unix.go:16: warning: Using 'getgrouplist' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-829040977/000020.o: In function `mygetgrgid_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:38: warning: Using 'getgrgid_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-829040977/000020.o: In function `mygetgrnam_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:43: warning: Using 'getgrnam_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-829040977/000020.o: In function `mygetpwnam_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:33: warning: Using 'getpwnam_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-829040977/000020.o: In function `mygetpwuid_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:28: warning: Using 'getpwuid_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-829040977/000004.o: In function `_cgo_18049202ccd9_C2func_getaddrinfo':
/tmp/go-build/cgo-gcc-prolog:49: warning: Using 'getaddrinfo' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
// 构建需要的压缩包
(cd sampleconfig && tar -jc *) > .build/sampleconfig.tar.bz2
// 复制peer需要的payload
mkdir -p .build/image/peer/payload
cp .build/docker/bin/peer .build/sampleconfig.tar.bz2 .build/image/peer/payload
// 打包peer镜像
mkdir -p .build/image/peer
Building docker peer-image
docker build --build-arg 'http_proxy=http://192.168.102.143:1087' --build-arg 'https_proxy=http://192.168.102.143:1087' -t hyperledger/fabric-peer .build/image/peer
Sending build context to Docker daemon  33.56MB
Step 1/7 : FROM hyperledger/fabric-baseos:amd64-0.4.15
 ---> 9d6ec11c60ff
Step 2/7 : ENV FABRIC_CFG_PATH /etc/hyperledger/fabric
 ---> Running in 3bea4b2a628b
Removing intermediate container 3bea4b2a628b
 ---> 8892a2046872
Step 3/7 : RUN mkdir -p /var/hyperledger/production $FABRIC_CFG_PATH
 ---> Running in 06437fde2305
Removing intermediate container 06437fde2305
 ---> 98fc3c6b0fae
Step 4/7 : COPY payload/peer /usr/local/bin
 ---> 635a5f0e02c4
Step 5/7 : ADD  payload/sampleconfig.tar.bz2 $FABRIC_CFG_PATH
 ---> d2e3f4b80946
Step 6/7 : CMD ["peer","node","start"]
 ---> Running in 47e57005f4f8
Removing intermediate container 47e57005f4f8
 ---> 59a7e54bfe1a
Step 7/7 : LABEL org.hyperledger.fabric.version=1.4.2       org.hyperledger.fabric.base.version=0.4.15
 ---> Running in aaacacec80e8
Removing intermediate container aaacacec80e8
 ---> e97b7fd4ff49
Successfully built e97b7fd4ff49
// 构建peer镜像完成，为镜像打包
Successfully tagged hyperledger/fabric-peer:latest
docker tag hyperledger/fabric-peer hyperledger/fabric-peer:amd64-1.4.2-snapshot-9dce735
docker tag hyperledger/fabric-peer hyperledger/fabric-peer:amd64-latest
// 以下为构建orderer镜像，与peer镜像过程类似
Building .build/docker/bin/orderer
# github.com/hyperledger/fabric/orderer
/tmp/go-link-846385019/000018.o: In function `pluginOpen':
/workdir/go/src/plugin/plugin_dlopen.go:19: warning: Using 'dlopen' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-846385019/000021.o: In function `mygetgrouplist':
/workdir/go/src/os/user/getgrouplist_unix.go:16: warning: Using 'getgrouplist' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-846385019/000020.o: In function `mygetgrgid_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:38: warning: Using 'getgrgid_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-846385019/000020.o: In function `mygetgrnam_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:43: warning: Using 'getgrnam_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-846385019/000020.o: In function `mygetpwnam_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:33: warning: Using 'getpwnam_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-846385019/000020.o: In function `mygetpwuid_r':
/workdir/go/src/os/user/cgo_lookup_unix.go:28: warning: Using 'getpwuid_r' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
/tmp/go-link-846385019/000004.o: In function `_cgo_18049202ccd9_C2func_getaddrinfo':
/tmp/go-build/cgo-gcc-prolog:49: warning: Using 'getaddrinfo' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
mkdir -p .build/image/orderer/payload
cp .build/docker/bin/orderer .build/sampleconfig.tar.bz2 .build/image/orderer/payload
mkdir -p .build/image/orderer
Building docker orderer-image
docker build --build-arg 'http_proxy=http://192.168.102.143:1087' --build-arg 'https_proxy=http://192.168.102.143:1087' -t hyperledger/fabric-orderer .build/image/orderer
Sending build context to Docker daemon  28.09MB
Step 1/8 : FROM hyperledger/fabric-baseos:amd64-0.4.15
 ---> 9d6ec11c60ff
Step 2/8 : ENV FABRIC_CFG_PATH /etc/hyperledger/fabric
 ---> Using cache
 ---> 8892a2046872
Step 3/8 : RUN mkdir -p /var/hyperledger/production $FABRIC_CFG_PATH
 ---> Using cache
 ---> 98fc3c6b0fae
Step 4/8 : COPY payload/orderer /usr/local/bin
 ---> 50854bee0fa6
Step 5/8 : ADD payload/sampleconfig.tar.bz2 $FABRIC_CFG_PATH/
 ---> bab56963bf0f
Step 6/8 : EXPOSE 7050
 ---> Running in bda05dbbf18a
Removing intermediate container bda05dbbf18a
 ---> 7b335f36f7d2
Step 7/8 : CMD ["orderer"]
 ---> Running in 210013bf0e3e
Removing intermediate container 210013bf0e3e
 ---> b543c69c8caf
Step 8/8 : LABEL org.hyperledger.fabric.version=1.4.2       org.hyperledger.fabric.base.version=0.4.15
 ---> Running in c762fc3e0590
Removing intermediate container c762fc3e0590
 ---> aa8604c99f23
Successfully built aa8604c99f23
Successfully tagged hyperledger/fabric-orderer:latest
docker tag hyperledger/fabric-orderer hyperledger/fabric-orderer:amd64-1.4.2-snapshot-9dce735
docker tag hyperledger/fabric-orderer hyperledger/fabric-orderer:amd64-latest
// 以下开始构gotools镜像
Building dockerized gotools
// 以下实际在docker中运行
// 默认go get下载，然后默认安装到$GOPATH/bin
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/maxbrunsfeld/counterfeiter -> counterfeiter
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/golang/dep v0.5.1 -> dep
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building golang.org/x/lint/golint -> golint
// 这几个指定了安装目录/opt/gotools/bin，实际映射到.build/docker/gotools/bin/
GOBIN=/opt/gotools/bin go install ./vendor/golang.org/x/lint/golint
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building golang.org/x/tools/cmd/goimports -> goimports
GOBIN=/opt/gotools/bin go install ./vendor/golang.org/x/tools/cmd/goimports
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/golang/protobuf/protoc-gen-go -> protoc-gen-go
GOBIN=/opt/gotools/bin go install ./vendor/github.com/golang/protobuf/protoc-gen-go
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/onsi/ginkgo/ginkgo -> ginkgo
GOBIN=/opt/gotools/bin go install ./vendor/github.com/onsi/ginkgo/ginkgo
// 以下安装到$GOPATH/bin
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/axw/gocov/gocov -> gocov
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/AlekSi/gocov-xml -> gocov-xml
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/client9/misspell/cmd/misspell -> misspell
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/vektra/mockery/cmd/mockery -> mockery
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
make[1]: Entering directory '/opt/gopath/src/github.com/hyperledger/fabric'
Building github.com/estesp/manifest-tool -> manifest-tool
make[1]: Leaving directory '/opt/gopath/src/github.com/hyperledger/fabric'
// 安装chaintool，gotools镜像需要
Installing chaintool
curl -fL https://nexus.hyperledger.org/content/repositories/releases/org/hyperledger/fabric/hyperledger-fabric/chaintool-1.1.3/hyperledger-fabric-chaintool-1.1.3.jar > .build/bin/chaintool
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 16.4M  100 16.4M    0     0  1142k      0  0:00:14  0:00:14 --:--:-- 2544k
chmod +x .build/bin/chaintool
Creating .build/goshim.tar.bz2
// 设置ccenv的payload
mkdir -p .build/image/ccenv/payload
cp .build/docker/gotools/bin/protoc-gen-go .build/bin/chaintool .build/goshim.tar.bz2 .build/image/ccenv/payload
mkdir -p .build/image/ccenv
// 构建ccenv镜像，是chain code的环境镜像，所以简写为ccenv
Building docker ccenv-image
docker build --build-arg 'http_proxy=http://192.168.102.143:1087' --build-arg 'https_proxy=http://192.168.102.143:1087' -t hyperledger/fabric-ccenv .build/image/ccenv
Sending build context to Docker daemon  25.12MB
Step 1/5 : FROM hyperledger/fabric-baseimage:amd64-0.4.15
 ---> c4c532c23a50
Step 2/5 : COPY payload/chaintool payload/protoc-gen-go /usr/local/bin/
 ---> 44e06a863d08
Step 3/5 : ADD payload/goshim.tar.bz2 $GOPATH/src/
 ---> 233605b067d5
Step 4/5 : RUN mkdir -p /chaincode/input /chaincode/output
 ---> Running in be1909a39e06
Removing intermediate container be1909a39e06
 ---> 605b1c70e97f
Step 5/5 : LABEL org.hyperledger.fabric.version=1.4.2       org.hyperledger.fabric.base.version=0.4.15
 ---> Running in dc470f15e125
Removing intermediate container dc470f15e125
 ---> 7cb803c8b124
Successfully built 7cb803c8b124
Successfully tagged hyperledger/fabric-ccenv:latest
docker tag hyperledger/fabric-ccenv hyperledger/fabric-ccenv:amd64-1.4.2-snapshot-9dce735
docker tag hyperledger/fabric-ccenv hyperledger/fabric-ccenv:amd64-latest
// 构建buildenv镜像
// gotools放进压缩包
(cd .build/docker/gotools/bin && tar -jc *) > .build/gotools.tar.bz2
mkdir -p .build/image/buildenv/payload
// gotools和protoc-gen-go是buildenv的payload
cp .build/gotools.tar.bz2 .build/docker/gotools/bin/protoc-gen-go .build/image/buildenv/payload
mkdir -p .build/image/buildenv
Building docker buildenv-image
docker build --build-arg 'http_proxy=http://192.168.102.143:1087' --build-arg 'https_proxy=http://192.168.102.143:1087' -t hyperledger/fabric-buildenv .build/image/buildenv
Sending build context to Docker daemon  47.17MB
Step 1/5 : FROM hyperledger/fabric-baseimage:amd64-0.4.15
 ---> c4c532c23a50
Step 2/5 : COPY payload/protoc-gen-go /usr/local/bin/
 ---> 90f62f1410b4
Step 3/5 : ADD payload/gotools.tar.bz2 /usr/local/bin/
 ---> e27228cd3fb8
Step 4/5 : ENV GOCACHE "/tmp"
 ---> Running in 780e38380727
Removing intermediate container 780e38380727
 ---> b610d861e6ce
Step 5/5 : LABEL org.hyperledger.fabric.version=1.4.2       org.hyperledger.fabric.base.version=0.4.15
 ---> Running in 226095fc14b5
Removing intermediate container 226095fc14b5
 ---> 6ba655852ec7
Successfully built 6ba655852ec7
Successfully tagged hyperledger/fabric-buildenv:latest
// gotools实际打包在了buildenv镜像中
docker tag hyperledger/fabric-buildenv hyperledger/fabric-buildenv:amd64-1.4.2-snapshot-9dce735
docker tag hyperledger/fabric-buildenv hyperledger/fabric-buildenv:amd64-latest
// 打包tools镜像，它的dockerfile文件：.build/image/tools/Dockerfile
// 从这里可以看到镜像里实际包含的是configtxgen configtxlator cryptogen peer discover idemixgen，这几个工具
// 并对系统进行了更新
// 所以tools镜像指的是fabric tools的镜像，而不是go tools
mkdir -p .build/image/tools
Building docker tools-image
docker build --build-arg 'http_proxy=http://192.168.102.143:1087' --build-arg 'https_proxy=http://192.168.102.143:1087' -t hyperledger/fabric-tools -f .build/image/tools/Dockerfile .
Sending build context to Docker daemon  179.5MB
Step 1/14 : FROM hyperledger/fabric-baseimage:amd64-0.4.15 as builder
 ---> c4c532c23a50
Step 2/14 : WORKDIR /opt/gopath
 ---> Running in bc4dd206cdcd
Removing intermediate container bc4dd206cdcd
 ---> c156c64ba0c0
Step 3/14 : RUN mkdir src && mkdir pkg && mkdir bin
 ---> Running in 752a63efe3be
Removing intermediate container 752a63efe3be
 ---> 001cb4d1136f
Step 4/14 : ADD . src/github.com/hyperledger/fabric
 ---> 5ba1e6fe79df
Step 5/14 : WORKDIR /opt/gopath/src/github.com/hyperledger/fabric
 ---> Running in 9b03a753a124
Removing intermediate container 9b03a753a124
 ---> e0eb57e0b44b
Step 6/14 : ENV EXECUTABLES go git curl
 ---> Running in 6b5978688143
Removing intermediate container 6b5978688143
 ---> 2a28ae07b3da
Step 7/14 : RUN make configtxgen configtxlator cryptogen peer discover idemixgen
 ---> Running in 27e814a9a148
//  在镜像里安装native中的各种工具，所以gotools镜像，包含的并不是gotools那几个工具
.build/bin/configtxgen
CGO_CFLAGS=" " GOBIN=/opt/gopath/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/configtxgen/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/configtxgen
Binary available as .build/bin/configtxgen
.build/bin/configtxlator
CGO_CFLAGS=" " GOBIN=/opt/gopath/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/configtxlator/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/configtxlator
Binary available as .build/bin/configtxlator
.build/bin/cryptogen
CGO_CFLAGS=" " GOBIN=/opt/gopath/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/cryptogen/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/cryptogen
Binary available as .build/bin/cryptogen
.build/bin/peer
CGO_CFLAGS=" " GOBIN=/opt/gopath/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/metadata.Version=1.4.2 -X github.com/hyperledger/fabric/common/metadata.CommitSHA=9dce735 -X github.com/hyperledger/fabric/common/metadata.BaseVersion=0.4.15 -X github.com/hyperledger/fabric/common/metadata.BaseDockerLabel=org.hyperledger.fabric -X github.com/hyperledger/fabric/common/metadata.DockerNamespace=hyperledger -X github.com/hyperledger/fabric/common/metadata.BaseDockerNamespace=hyperledger" github.com/hyperledger/fabric/peer
Binary available as .build/bin/peer
.build/bin/discover
CGO_CFLAGS=" " GOBIN=/opt/gopath/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/cmd/discover/metadata.Version=1.4.2-snapshot-9dce735" github.com/hyperledger/fabric/cmd/discover
Binary available as .build/bin/discover
.build/bin/idemixgen
CGO_CFLAGS=" " GOBIN=/opt/gopath/src/github.com/hyperledger/fabric/.build/bin go install -tags "" -ldflags "-X github.com/hyperledger/fabric/common/tools/idemixgen/metadata.CommitSHA=9dce735" github.com/hyperledger/fabric/common/tools/idemixgen
Binary available as .build/bin/idemixgen
Removing intermediate container 27e814a9a148
 ---> 019fcc98aafe
Step 8/14 : FROM hyperledger/fabric-baseimage:amd64-0.4.15
 ---> c4c532c23a50
Step 9/14 : ENV FABRIC_CFG_PATH /etc/hyperledger/fabric
 ---> Running in 971f1e778c1b
Removing intermediate container 971f1e778c1b
 ---> 3abe7ab3eda7
Step 10/14 : RUN apt-get update && apt-get install -y jq
 ---> Running in 0c6bc2dab637
Get:1 http://security.ubuntu.com/ubuntu xenial-security InRelease [109 kB]
Get:2 http://archive.ubuntu.com/ubuntu xenial InRelease [247 kB]
Get:3 http://archive.ubuntu.com/ubuntu xenial-updates InRelease [109 kB]
Get:4 http://security.ubuntu.com/ubuntu xenial-security/main amd64 Packages [896 kB]
Get:5 http://archive.ubuntu.com/ubuntu xenial-backports InRelease [107 kB]
Get:6 http://archive.ubuntu.com/ubuntu xenial/main amd64 Packages [1558 kB]
Get:7 http://security.ubuntu.com/ubuntu xenial-security/restricted amd64 Packages [12.7 kB]
Get:8 http://security.ubuntu.com/ubuntu xenial-security/universe amd64 Packages [569 kB]
Get:9 http://archive.ubuntu.com/ubuntu xenial/restricted amd64 Packages [14.1 kB]
Get:10 http://archive.ubuntu.com/ubuntu xenial/universe amd64 Packages [9827 kB]
Get:11 http://security.ubuntu.com/ubuntu xenial-security/multiverse amd64 Packages [6117 B]
Get:12 http://archive.ubuntu.com/ubuntu xenial/multiverse amd64 Packages [176 kB]
Get:13 http://archive.ubuntu.com/ubuntu xenial-updates/main amd64 Packages [1277 kB]
Get:14 http://archive.ubuntu.com/ubuntu xenial-updates/restricted amd64 Packages [13.1 kB]
Get:15 http://archive.ubuntu.com/ubuntu xenial-updates/universe amd64 Packages [974 kB]
Get:16 http://archive.ubuntu.com/ubuntu xenial-updates/multiverse amd64 Packages [19.1 kB]
Get:17 http://archive.ubuntu.com/ubuntu xenial-backports/main amd64 Packages [7942 B]
Get:18 http://archive.ubuntu.com/ubuntu xenial-backports/universe amd64 Packages [8532 B]
Fetched 15.9 MB in 17s (896 kB/s)
Reading package lists...
Reading package lists...
Building dependency tree...
Reading state information...
The following additional packages will be installed:
  libonig2
The following NEW packages will be installed:
  jq libonig2
0 upgraded, 2 newly installed, 0 to remove and 55 not upgraded.
Need to get 231 kB of archives.
After this operation, 797 kB of additional disk space will be used.
Get:1 http://archive.ubuntu.com/ubuntu xenial-updates/universe amd64 libonig2 amd64 5.9.6-1ubuntu0.1 [86.7 kB]
Get:2 http://archive.ubuntu.com/ubuntu xenial-updates/universe amd64 jq amd64 1.5+dfsg-1ubuntu0.1 [144 kB]
debconf: unable to initialize frontend: Dialog
debconf: (TERM is not set, so the dialog frontend is not usable.)
debconf: falling back to frontend: Readline
debconf: unable to initialize frontend: Readline
debconf: (This frontend requires a controlling tty.)
debconf: falling back to frontend: Teletype
dpkg-preconfigure: unable to re-open stdin:
Fetched 231 kB in 2s (105 kB/s)
Selecting previously unselected package libonig2:amd64.
(Reading database ... 22655 files and directories currently installed.)
Preparing to unpack .../libonig2_5.9.6-1ubuntu0.1_amd64.deb ...
Unpacking libonig2:amd64 (5.9.6-1ubuntu0.1) ...
Selecting previously unselected package jq.
Preparing to unpack .../jq_1.5+dfsg-1ubuntu0.1_amd64.deb ...
Unpacking jq (1.5+dfsg-1ubuntu0.1) ...
Processing triggers for libc-bin (2.23-0ubuntu11) ...
Setting up libonig2:amd64 (5.9.6-1ubuntu0.1) ...
Setting up jq (1.5+dfsg-1ubuntu0.1) ...
Processing triggers for libc-bin (2.23-0ubuntu11) ...
Removing intermediate container 0c6bc2dab637
 ---> bc8cfafb544f
Step 11/14 : VOLUME /etc/hyperledger/fabric
 ---> Running in 260f4ec6bd3e
Removing intermediate container 260f4ec6bd3e
 ---> 9f682419f109
Step 12/14 : COPY --from=builder /opt/gopath/src/github.com/hyperledger/fabric/.build/bin /usr/local/bin
 ---> ff18ec787bf5
Step 13/14 : COPY --from=builder /opt/gopath/src/github.com/hyperledger/fabric/sampleconfig $FABRIC_CFG_PATH
 ---> 70163f0cac4f
Step 14/14 : LABEL org.hyperledger.fabric.version=1.4.2       org.hyperledger.fabric.base.version=0.4.15
 ---> Running in 2f70bb608ac2
Removing intermediate container 2f70bb608ac2
 ---> e395ec9d27e8
Successfully built e395ec9d27e8
Successfully tagged hyperledger/fabric-tools:latest
// gotools镜像打包完成，打上tag
docker tag hyperledger/fabric-tools hyperledger/fabric-tools:amd64-1.4.2-snapshot-9dce735
docker tag hyperledger/fabric-tools hyperledger/fabric-tools:amd64-latest

// 以下等价于make checks
// 许可证检查
All files have SPDX-License-Identifier headers
// 拼写检查
Checking changed go files for spelling errors ...
spell checker passed
// trailing spaces检查
Checking trailing spaces ...
// dep检查
DEP: Checking for dependency issues..
dep:
 version     : v0.5.1
 build date  : 2019-07-16
 git hash    :
 go version  : go1.11.5
 go compiler : gc
 platform    : linux/amd64
 features    : ImportDuringSolve=false
# out of sync, but ignored, due to noverify in Gopkg.toml:
github.com/grpc-ecosystem/go-grpc-middleware: hash of vendored tree not equal to digest in Gopkg.lock
// 执行lint
LINT: Running code checks..
Checking with gofmt
Checking with goimports
Checking for golang.org/x/net/context
Checking with go vet
METRICS: Checking for outdated reference documentation..
cd unit-test && docker-compose down
WARNING: The TEST_PKGS variable is not set. Defaulting to a blank string.
WARNING: The JOB_TYPE variable is not set. Defaulting to a blank string.
docker pull hyperledger/fabric-couchdb:amd64-0.4.15
amd64-0.4.15: Pulling from hyperledger/fabric-couchdb
34667c7e4631: Already exists
d18d76a881a4: Already exists
119c7358fbfc: Already exists
2aaf13f3eff0: Already exists
3f89de4cf84b: Already exists
24194f819972: Already exists
78e4eabd31a5: Already exists
c7652b6bde40: Already exists
b4646dd65c45: Already exists
5e6defad8a30: Already exists
7695bf5d0b9d: Pull complete
6d9d46f66bc3: Pull complete
4912f1b4990a: Pull complete
f3b174a93eea: Pull complete
3763a939777a: Pull complete
f293593adbb6: Pull complete
1ae53ace804f: Pull complete
d4aa6d764b18: Pull complete
d747b2b30e48: Pull complete
52cbd2253fea: Pull complete
Digest: sha256:e9c528f90c84c50dd3a79c2d2c5f1ff87264a8009a1971b269ceecace4ef1fb9
Status: Downloaded newer image for hyperledger/fabric-couchdb:amd64-0.4.15
docker tag hyperledger/fabric-couchdb:amd64-0.4.15 hyperledger/fabric-couchdb
docker pull hyperledger/fabric-zookeeper:amd64-0.4.15
amd64-0.4.15: Pulling from hyperledger/fabric-zookeeper
34667c7e4631: Already exists
d18d76a881a4: Already exists
119c7358fbfc: Already exists
2aaf13f3eff0: Already exists
3f89de4cf84b: Already exists
24194f819972: Already exists
78e4eabd31a5: Already exists
c7652b6bde40: Already exists
b4646dd65c45: Already exists
5e6defad8a30: Already exists
0e045d9c2cdc: Pull complete
7ef4d8920518: Pull complete
dbeed81d9a45: Pull complete
aeea025ecc4e: Pull complete
Digest: sha256:4e4e8b8aaed7864f23d0c6c018cc8589e8e1d042413abc034dd7a6b3faacd2f0
Status: Downloaded newer image for hyperledger/fabric-zookeeper:amd64-0.4.15
docker tag hyperledger/fabric-zookeeper:amd64-0.4.15 hyperledger/fabric-zookeeper
docker pull hyperledger/fabric-kafka:amd64-0.4.15
amd64-0.4.15: Pulling from hyperledger/fabric-kafka
34667c7e4631: Already exists
d18d76a881a4: Already exists
119c7358fbfc: Already exists
2aaf13f3eff0: Already exists
3f89de4cf84b: Already exists
24194f819972: Already exists
78e4eabd31a5: Already exists
c7652b6bde40: Already exists
b4646dd65c45: Already exists
5e6defad8a30: Already exists
d0459116a54a: Pull complete
1bbcec7bfdef: Pull complete
5911218c5933: Pull complete
Digest: sha256:68398b1e1ee4165fd80b1a2f0e123625f489150673c7dc4816177816e43ace78
Status: Downloaded newer image for hyperledger/fabric-kafka:amd64-0.4.15
docker tag hyperledger/fabric-kafka:amd64-0.4.15 hyperledger/fabric-kafka
unit-test/run.sh

// 省略后面的单元测试
```


> 1. 本文作者：[大彬](http://lessisbetter.site/about/)
> 1. 如果喜欢本文，随意转载，但请保留此原文链接：[http://lessisbetter.site/2019/07/16/fabric-makefile/](http://lessisbetter.site/2019/07/16/fabric-makefile/)


<div style="color:#0096FF; text-align:center">关注公众号，获取最新Golang文章</div>
<img src="http://img.lessisbetter.site/2019-01-article_qrcode.jpg" style="border:0"  align=center />