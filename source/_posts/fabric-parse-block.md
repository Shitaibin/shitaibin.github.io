---
title: 利用工具解析Fabric区块与工具详解
date: 2019-08-01 19:41:28
tags: ['区块链', 'Fabric']
---


获取人类可读的区块内容分2步：
1. 从账本里把区块取出来，格式为protobuf
1. 把protobuf格式的区块，转换为JSON格式

所以这篇文章3步走：
1. 获取区块
2. 解析区块
3. 常见区块类型样例

## 获取区块

### 拉取应用通道区块


`peer channel fetch`能够拉去某个通道最新、最老、特定高度的区块，只不过得到的区块是protobuf格式的，人眼不可读。


```
root@eedf1a41eb00:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel fetch -h
Fetch a specified block, writing it to a file.

Usage:
  peer channel fetch <newest|oldest|config|(number)> [outputfile] [flags]

Flags:
      --bestEffort         Whether fetch requests should ignore errors and return blocks on a best effort basis
  -c, --channelID string   In case of a newChain command, the channel ID to create. It must be all lower case, less than 250 characters long and match the regular expression: [a-z][a-z0-9.-]*
  -h, --help               help for fetch

Global Flags:
      --cafile string                       Path to file containing PEM-encoded trusted certificate(s) for the ordering endpoint
      --certfile string                     Path to file containing PEM-encoded X509 public key to use for mutual TLS communication with the orderer endpoint
      --clientauth                          Use mutual TLS when communicating with the orderer endpoint
      --connTimeout duration                Timeout for client to connect (default 3s)
      --keyfile string                      Path to file containing PEM-encoded private key to use for mutual TLS communication with the orderer endpoint
  -o, --orderer string                      Ordering service endpoint
      --ordererTLSHostnameOverride string   The hostname override to use when validating the TLS connection to the orderer.
      --tls                                 Use TLS when communicating with the orderer endpoint
```


以下命令下载了指定channel的第0个区块，即此channel的创世块，区块保存为mychannel.block。

```
peer channel fetch 0 mychannel.block  -c mychannel 
```
 
如果不指定保存的区块名，会自动生成，格式：通道名_区块号，比如：

```
peer channel fetch 3 -c mychannel
```

操作：

```
root@ca8843f81b89:/opt/gopath/src/github.com/hyperledger/fabric/peer# peer channel fetch 3 -c mychannel
2019-08-01 02:20:45.378 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-08-01 02:20:45.382 UTC [cli.common] readBlock -> INFO 002 Received block: 3
root@ca8843f81b89:/opt/gopath/src/github.com/hyperledger/fabric/peer#
root@ca8843f81b89:/opt/gopath/src/github.com/hyperledger/fabric/peer# ls
channel-artifacts  crypto  log.txt  mychannel.block  mychannel_3.block  scripts
```

### 获取通道配置去块


如果使用`peer channel fetch config`可以获取某个通道的最新配置所在的区块。

```
peer channel fetch config -c mychannel 
```

命令执行结果的最后一行会显示配置所在的区块号，区块文件保存为`mychannel_config.block`。


### 拉取系统通道区块

拉取系统通道通常是为了获取系统配置，系统配置存在系统区块中，下面就是获取系统区块的方法。

系统通道区块是保存在orderer节点上的，需要在获取的时候指定orderer配置和证书，然后使用config而不是区块号，直接获取最新的配置，创世块使用区块0获取。

1. 连接到orderer节点，查询系统通道名称
```
ls /var/hyperledger/production/orderer/chains/
```

2. cli上设置orderer的设置，设置上面查询的通道名字，获取的区块与通道同名
```
export CHANNEL_NAME=byfn-sys-channel
export ORDERER_CA=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export CORE_PEER_ADDRESS=orderer.example.com:7050
export CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export CORE_PEER_LOCALMSPID="OrdererMSP"
export CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp
export ORDERER_CA=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem

peer channel fetch config $CHANNEL_NAME.block -o orderer.example.com:7050 -c $CHANNEL_NAME --tls --cafile $ORDERER_CA
```

以上命令执行结果的最后一行，会显示当前配置所在的区块高度。

## 解析工具

`configtxlator`是一个fabric中protbuf和JSON格式之间的转换工具，fabric中任何的使用Protobuf定义的类型，都可使用该工具进行转换。

#### 解析示例

比如创建通道交易：`channel.tx`也是protobuf格式的，可以利用此工具解析：

```
configtxlator proto_decode  --type common.Envelope --input channel.tx
```

- `--type xxx`：阅读源码，找出该proto格式数据对应的数据类型
- `--input xxx`：proto格式数据文件

结果：

```json
{
	"payload": {
		"data": {
			"config_update": {
				"channel_id": "mychannel",
				"isolated_data": {},
				"read_set": {
					"groups": {
						"Application": {
							"groups": {
								"Org1MSP": {
									"groups": {},
									"mod_policy": "",
									"policies": {},
									"values": {},
									"version": "0"
								},
								"Org2MSP": {
									"groups": {},
									"mod_policy": "",
									"policies": {},
									"values": {},
									"version": "0"
								}
							},
							"mod_policy": "",
							"policies": {},
							"values": {},
							"version": "0"
						}
					},
					"mod_policy": "",
					"policies": {},
					"values": {
						"Consortium": {
							"mod_policy": "",
							"value": null,
							"version": "0"
						}
					},
					"version": "0"
				},
				"write_set": {
					"groups": {
						"Application": {
							"groups": {
								"Org1MSP": {
									"groups": {},
									"mod_policy": "",
									"policies": {},
									"values": {},
									"version": "0"
								},
								"Org2MSP": {
									"groups": {},
									"mod_policy": "",
									"policies": {},
									"values": {},
									"version": "0"
								}
							},
							"mod_policy": "Admins",
							"policies": {
								"Admins": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "MAJORITY",
											"sub_policy": "Admins"
										}
									},
									"version": "0"
								},
								"Readers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Readers"
										}
									},
									"version": "0"
								},
								"Writers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Writers"
										}
									},
									"version": "0"
								}
							},
							"values": {
								"Capabilities": {
									"mod_policy": "Admins",
									"value": {
										"capabilities": {
											"V1_3": {}
										}
									},
									"version": "0"
								}
							},
							"version": "1"
						}
					},
					"mod_policy": "",
					"policies": {},
					"values": {
						"Consortium": {
							"mod_policy": "",
							"value": {
								"name": "SampleConsortium"
							},
							"version": "0"
						}
					},
					"version": "0"
				}
			},
			"signatures": []
		},
		"header": {
			"channel_header": {
				"channel_id": "mychannel",
				"epoch": "0",
				"extension": null,
				"timestamp": "2019-08-01T06:30:01Z",
				"tls_cert_hash": null,
				"tx_id": "",
				"type": 2,
				"version": 0
			},
			"signature_header": null
		}
	},
	"signature": null
}
```

### 解析区块

使用`configtxlator`可以把区块从protobuf解析成JSON格式，

```
configtxlator proto_decode  --type common.Block --input mychannel.block > mychannel.block.json
```

结果见[样例](常见区块样例)。

### 拓展查询

Fabric提供了使用`peer channel fetch`获取区块的功能，但没有提供查询交易、db等信息的接口，那如何办？

获取交易，有方法：`GetTransactionByID`。

获取DB，有方法：`GetStateLevelDBData`。

如果结果是非结构体格式的`[]byte`或者`string`，可以直接组装成JSON格式，比如`GetStateLevelDBData`。`GetTransactionByID`是返回protobuf定义的结构体，可以直接使用`configtxlator`调用的接口`DeepMarshalJSON`把结构体转换为JSON字符串。

`DeepMarshalJSON`是tools `protolator`提供的一个接口，`protolator`这个工具是完成protobuf数据和JSON数据之间转换的实际工具。利用这些工具和简单的Web框架，可以搭建出查询通道、区块、交易、数据(KV)的简易网站。


## 常见区块样例

fabric里包含了2大类区块：
1. 配置区块
1. 普通区块

区块0是配置区块，又被称为创世块，后续对配置的每一次改动都会生成1个配置块存入所修改配置的通道以及系统通道。

### 系统通道创世块

主要是包含了一下配置：
1. 组织
1. 通道

```json
{
	"data": {
		"data": [{
			"payload": {
				"data": {
					"config": {
						"channel_group": {
							"groups": {
								"Consortiums": {
									"groups": {
										"SampleConsortium": {
											"groups": {
												"Org1MSP": {
													"groups": {},
													"mod_policy": "Admins",
													"policies": {
														"Admins": {
															"mod_policy": "Admins",
															"policy": {
																"type": 1,
																"value": {
																	"identities": [{
																		"principal": {
																			"msp_identifier": "Org1MSP",
																			"role": "ADMIN"
																		},
																		"principal_classification": "ROLE"
																	}],
																	"rule": {
																		"n_out_of": {
																			"n": 1,
																			"rules": [{
																				"signed_by": 0
																			}]
																		}
																	},
																	"version": 0
																}
															},
															"version": "0"
														},
														"Readers": {
															"mod_policy": "Admins",
															"policy": {
																"type": 1,
																"value": {
																	"identities": [{
																			"principal": {
																				"msp_identifier": "Org1MSP",
																				"role": "ADMIN"
																			},
																			"principal_classification": "ROLE"
																		},
																		{
																			"principal": {
																				"msp_identifier": "Org1MSP",
																				"role": "PEER"
																			},
																			"principal_classification": "ROLE"
																		},
																		{
																			"principal": {
																				"msp_identifier": "Org1MSP",
																				"role": "CLIENT"
																			},
																			"principal_classification": "ROLE"
																		}
																	],
																	"rule": {
																		"n_out_of": {
																			"n": 1,
																			"rules": [{
																					"signed_by": 0
																				},
																				{
																					"signed_by": 1
																				},
																				{
																					"signed_by": 2
																				}
																			]
																		}
																	},
																	"version": 0
																}
															},
															"version": "0"
														},
														"Writers": {
															"mod_policy": "Admins",
															"policy": {
																"type": 1,
																"value": {
																	"identities": [{
																			"principal": {
																				"msp_identifier": "Org1MSP",
																				"role": "ADMIN"
																			},
																			"principal_classification": "ROLE"
																		},
																		{
																			"principal": {
																				"msp_identifier": "Org1MSP",
																				"role": "CLIENT"
																			},
																			"principal_classification": "ROLE"
																		}
																	],
																	"rule": {
																		"n_out_of": {
																			"n": 1,
																			"rules": [{
																					"signed_by": 0
																				},
																				{
																					"signed_by": 1
																				}
																			]
																		}
																	},
																	"version": 0
																}
															},
															"version": "0"
														}
													},
													"values": {
														"MSP": {
															"mod_policy": "Admins",
															"value": {
																"config": {
																	"admins": [
																		"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLVENDQWRDZ0F3SUJBZ0lRUEtTRHJHNWRTT0liVHRLM3pqcEhlVEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUd3eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVE4d0RRWURWUVFMRXdaamJHbGxiblF4SHpBZEJnTlZCQU1NRmtGa2JXbHVRRzl5Clp6RXVaWGhoYlhCc1pTNWpiMjB3V1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVFiNEZydmg1V2oKclBSOTFIdFdSaFVORVpxQXFOL2pEYkhUbUtDSXBkY3k3K2JGTUduaUprdTExaTl2ajN6TnNQMGQrSWlSRDdiMgpJSlhVaGxZbVJjcXVvMDB3U3pBT0JnTlZIUThCQWY4RUJBTUNCNEF3REFZRFZSMFRBUUgvQkFJd0FEQXJCZ05WCkhTTUVKREFpZ0NCVUdsTldyVThlZFBPakorMkc3M2UyU1FEdjVYdFUzSWYrSTJEMmo4VWdFREFLQmdncWhrak8KUFFRREFnTkhBREJFQWlBRFB6Qk5uKytROURXd0VUS0ErRTQyNG5vekVzZjRFd2JzQWxuUCtXNU10UUlnSDc3Two3dEVJUFZacTRvVUtSb1I5QWsvUEUrWUFzYk4vdHZhVlZlZ2dLTGc9Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
																	],
																	"crypto_config": {
																		"identity_identifier_hash_function": "SHA256",
																		"signature_hash_family": "SHA2"
																	},
																	"fabric_node_ous": {
																		"client_ou_identifier": {
																			"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
																			"organizational_unit_identifier": "client"
																		},
																		"enable": true,
																		"peer_ou_identifier": {
																			"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
																			"organizational_unit_identifier": "peer"
																		}
																	},
																	"intermediate_certs": [],
																	"name": "Org1MSP",
																	"organizational_unit_identifiers": [],
																	"revocation_list": [],
																	"root_certs": [
																		"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo="
																	],
																	"signing_identity": null,
																	"tls_intermediate_certs": [],
																	"tls_root_certs": [
																		"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNWakNDQWYyZ0F3SUJBZ0lRQldDNzUzQUphWXVOSkhqeVpGb1JvVEFLQmdncWhrak9QUVFEQWpCMk1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWZNQjBHQTFVRUF4TVdkR3h6ClkyRXViM0puTVM1bGVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTAKTURCYU1IWXhDekFKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSApFdzFUWVc0Z1JuSmhibU5wYzJOdk1Sa3dGd1lEVlFRS0V4QnZjbWN4TG1WNFlXMXdiR1V1WTI5dE1SOHdIUVlEClZRUURFeFowYkhOallTNXZjbWN4TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJS29aSXpqMEQKQVFjRFFnQUVJcWRZYWtLRmtKRm1NZEhDRnVGdkJIVXZMMFhUa0RJTG40Qm5vdW5GWUFaWmRFNFdpQ1lkcnJsSwpjTmpQWG1pNXZEajcrQmhoWXBaQjRnbHZRbUpDb2FOdE1Hc3dEZ1lEVlIwUEFRSC9CQVFEQWdHbU1CMEdBMVVkCkpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQVRBUEJnTlZIUk1CQWY4RUJUQURBUUgvTUNrR0ExVWQKRGdRaUJDQ0JzMVk5ZjhzTjFBYndZdnFzcEdLRzBIenhTQ2RyWEdHdUVvc2dGb3BQcVRBS0JnZ3Foa2pPUFFRRApBZ05IQURCRUFpQnF5VzBOL0xhMTRlTVh4SXIzNWVQbXVXdXpQQnJrd1h4RG9pd1RtdXJzZ1FJZ0JRRkZJdVl5CmRSVk4zOHdZSU5vUU16eW5Uek93NFNBMXpRdUs3QzViZGk0PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
																	]
																},
																"type": 0
															},
															"version": "0"
														}
													},
													"version": "0"
												},
												"Org2MSP": {
													"groups": {},
													"mod_policy": "Admins",
													"policies": {
														"Admins": {
															"mod_policy": "Admins",
															"policy": {
																"type": 1,
																"value": {
																	"identities": [{
																		"principal": {
																			"msp_identifier": "Org2MSP",
																			"role": "ADMIN"
																		},
																		"principal_classification": "ROLE"
																	}],
																	"rule": {
																		"n_out_of": {
																			"n": 1,
																			"rules": [{
																				"signed_by": 0
																			}]
																		}
																	},
																	"version": 0
																}
															},
															"version": "0"
														},
														"Readers": {
															"mod_policy": "Admins",
															"policy": {
																"type": 1,
																"value": {
																	"identities": [{
																			"principal": {
																				"msp_identifier": "Org2MSP",
																				"role": "ADMIN"
																			},
																			"principal_classification": "ROLE"
																		},
																		{
																			"principal": {
																				"msp_identifier": "Org2MSP",
																				"role": "PEER"
																			},
																			"principal_classification": "ROLE"
																		},
																		{
																			"principal": {
																				"msp_identifier": "Org2MSP",
																				"role": "CLIENT"
																			},
																			"principal_classification": "ROLE"
																		}
																	],
																	"rule": {
																		"n_out_of": {
																			"n": 1,
																			"rules": [{
																					"signed_by": 0
																				},
																				{
																					"signed_by": 1
																				},
																				{
																					"signed_by": 2
																				}
																			]
																		}
																	},
																	"version": 0
																}
															},
															"version": "0"
														},
														"Writers": {
															"mod_policy": "Admins",
															"policy": {
																"type": 1,
																"value": {
																	"identities": [{
																			"principal": {
																				"msp_identifier": "Org2MSP",
																				"role": "ADMIN"
																			},
																			"principal_classification": "ROLE"
																		},
																		{
																			"principal": {
																				"msp_identifier": "Org2MSP",
																				"role": "CLIENT"
																			},
																			"principal_classification": "ROLE"
																		}
																	],
																	"rule": {
																		"n_out_of": {
																			"n": 1,
																			"rules": [{
																					"signed_by": 0
																				},
																				{
																					"signed_by": 1
																				}
																			]
																		}
																	},
																	"version": 0
																}
															},
															"version": "0"
														}
													},
													"values": {
														"MSP": {
															"mod_policy": "Admins",
															"value": {
																"config": {
																	"admins": [
																		"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
																	],
																	"crypto_config": {
																		"identity_identifier_hash_function": "SHA256",
																		"signature_hash_family": "SHA2"
																	},
																	"fabric_node_ous": {
																		"client_ou_identifier": {
																			"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
																			"organizational_unit_identifier": "client"
																		},
																		"enable": true,
																		"peer_ou_identifier": {
																			"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
																			"organizational_unit_identifier": "peer"
																		}
																	},
																	"intermediate_certs": [],
																	"name": "Org2MSP",
																	"organizational_unit_identifiers": [],
																	"revocation_list": [],
																	"root_certs": [
																		"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
																	],
																	"signing_identity": null,
																	"tls_intermediate_certs": [],
																	"tls_root_certs": [
																		"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNWekNDQWYyZ0F3SUJBZ0lRVGV5ZHpHQWVpNzB1ZkZzbTBmTWY1VEFLQmdncWhrak9QUVFEQWpCMk1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTWk1bGVHRnRjR3hsTG1OdmJURWZNQjBHQTFVRUF4TVdkR3h6ClkyRXViM0puTWk1bGVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTAKTURCYU1IWXhDekFKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSApFdzFUWVc0Z1JuSmhibU5wYzJOdk1Sa3dGd1lEVlFRS0V4QnZjbWN5TG1WNFlXMXdiR1V1WTI5dE1SOHdIUVlEClZRUURFeFowYkhOallTNXZjbWN5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJS29aSXpqMEQKQVFjRFFnQUVadTg3U0JzYWpnNXRTcFZKeGlZaE9YaWpOd3J0TmQvTFpuYkozWjUvY0dhaXZHeTZwQTB6Y1RjcApvdHN1YWJscE9BNHkxREEvbk5xaWtQa1dVVHZQcHFOdE1Hc3dEZ1lEVlIwUEFRSC9CQVFEQWdHbU1CMEdBMVVkCkpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQVRBUEJnTlZIUk1CQWY4RUJUQURBUUgvTUNrR0ExVWQKRGdRaUJDQUh4MDhOZ1FwdW9IR0tZWU9IYWh3VDg0cW9BN3p3dzFRTVNZT0h2VlZCWERBS0JnZ3Foa2pPUFFRRApBZ05JQURCRkFpRUF5QlBlakFHWjZtNXdWS244WHFhblFsMWUzYjNpUFBJVFdHaVN0dDBuZ3JJQ0lIUUJKRFd6CjFubzBMbnp0Nis4eEw5R25oY1NrZnZsWXR5MmhQcjdnTThFYgotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
																	]
																},
																"type": 0
															},
															"version": "0"
														}
													},
													"version": "0"
												}
											},
											"mod_policy": "/Channel/Orderer/Admins",
											"policies": {},
											"values": {
												"ChannelCreationPolicy": {
													"mod_policy": "/Channel/Orderer/Admins",
													"value": {
														"type": 3,
														"value": {
															"rule": "ANY",
															"sub_policy": "Admins"
														}
													},
													"version": "0"
												}
											},
											"version": "0"
										}
									},
									"mod_policy": "/Channel/Orderer/Admins",
									"policies": {
										"Admins": {
											"mod_policy": "/Channel/Orderer/Admins",
											"policy": {
												"type": 1,
												"value": {
													"identities": [],
													"rule": {
														"n_out_of": {
															"n": 0,
															"rules": []
														}
													},
													"version": 0
												}
											},
											"version": "0"
										}
									},
									"values": {},
									"version": "0"
								},
								"Orderer": {
									"groups": {
										"OrdererOrg": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "MEMBER"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "MEMBER"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNDekNDQWJHZ0F3SUJBZ0lSQUtuelI3NFZjN3RqOE5aQ21QV29QaWN3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRll4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJvd0dBWURWUVFEREJGQlpHMXBia0JsZUdGdGNHeGxMbU52YlRCWk1CTUdCeXFHU000OUFnRUdDQ3FHClNNNDlBd0VIQTBJQUJNUGUyNUtPU0hscUVZelJFVE83YXRjYWRvT0xnckRxelJQTjNjQ2RpR3A4QU4wdmdiTnAKTEEvTFJ0alFKbzdQaTZFZFlHaWh1MUNuRWgvNUxnYk90TmVqVFRCTE1BNEdBMVVkRHdFQi93UUVBd0lIZ0RBTQpCZ05WSFJNQkFmOEVBakFBTUNzR0ExVWRJd1FrTUNLQUlFQ0pBOWZTbDlUN0xsVWZ3QVhwM1V1cyt2YVpRbkZPCm9PSXJ2cmFrUDE3QU1Bb0dDQ3FHU000OUJBTUNBMGdBTUVVQ0lRQ1BjZVpmekNXa29MZ0N0NTMwbmEramY0a2cKN3BIWWwwY2NMTTZ4QkU0em5RSWdFVU52N2Q3MjQ2N1dnN0pMckZDb0x6eFhWUlMrN2UyWVJYSUlKOS9NVTJRPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": null,
															"intermediate_certs": [],
															"name": "OrdererMSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNQRENDQWVPZ0F3SUJBZ0lRSm9TdloyVE5oVTZjN0kvZ3VRNHYvVEFLQmdncWhrak9QUVFEQWpCcE1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVVNQklHQTFVRUNoTUxaWGhoYlhCc1pTNWpiMjB4RnpBVkJnTlZCQU1URG1OaExtVjRZVzF3CmJHVXVZMjl0TUI0WERURTVNRGd3TVRBeU1UUXdNRm9YRFRJNU1EY3lPVEF5TVRRd01Gb3dhVEVMTUFrR0ExVUUKQmhNQ1ZWTXhFekFSQmdOVkJBZ1RDa05oYkdsbWIzSnVhV0V4RmpBVUJnTlZCQWNURFZOaGJpQkdjbUZ1WTJsegpZMjh4RkRBU0JnTlZCQW9UQzJWNFlXMXdiR1V1WTI5dE1SY3dGUVlEVlFRREV3NWpZUzVsZUdGdGNHeGxMbU52CmJUQlpNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQTBJQUJFaUxuejB5TXp6K0dPNTlLZ3NMV0E1SVNaTXgKaUdRMVkrVHB3a1hZQXhjQnZENXZMMGhXcCtwWDdmSCtqaU9TOFBCMDFkamQ0TVJsb0lCQTgzYkxxdktqYlRCcgpNQTRHQTFVZER3RUIvd1FFQXdJQnBqQWRCZ05WSFNVRUZqQVVCZ2dyQmdFRkJRY0RBZ1lJS3dZQkJRVUhBd0V3CkR3WURWUjBUQVFIL0JBVXdBd0VCL3pBcEJnTlZIUTRFSWdRZ1FJa0QxOUtYMVBzdVZSL0FCZW5kUzZ6NjlwbEMKY1U2ZzRpdSt0cVEvWHNBd0NnWUlLb1pJemowRUF3SURSd0F3UkFJZ2JmRWVkMjJGRHFFSStwU0pKTXZrQi9GQQpFRitIUlg5OW91bGRLVlBqcDgwQ0lBS1VISmxlR01HYzF6dHRNSStCcHBldG53UU5nWjRsUDY5MUs0bENnU2hMCi0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNRekNDQWVxZ0F3SUJBZ0lSQVBWKy9UOVlSTjV0YmFXVGlETjg5Mmt3Q2dZSUtvWkl6ajBFQXdJd2JERUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJvd0dBWURWUVFERXhGMGJITmpZUzVsCmVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTBNREJhTUd3eEN6QUoKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSEV3MVRZVzRnUm5KaApibU5wYzJOdk1SUXdFZ1lEVlFRS0V3dGxlR0Z0Y0d4bExtTnZiVEVhTUJnR0ExVUVBeE1SZEd4elkyRXVaWGhoCmJYQnNaUzVqYjIwd1dUQVRCZ2NxaGtqT1BRSUJCZ2dxaGtqT1BRTUJCd05DQUFSUkxQK2ZLeFpnd2tFa2JIREoKb1JQak5ySXZBWWx2SHBMUTJoSXE1aXJQQnJlcEU4akRNTERyVklZR0NRdDBydGxjWFZTT3dZVTFkMXNOUy9USApSb1JvbzIwd2F6QU9CZ05WSFE4QkFmOEVCQU1DQWFZd0hRWURWUjBsQkJZd0ZBWUlLd1lCQlFVSEF3SUdDQ3NHCkFRVUZCd01CTUE4R0ExVWRFd0VCL3dRRk1BTUJBZjh3S1FZRFZSME9CQ0lFSUJWM1owTGw1TnpOcUdqVlpmbHIKUHRqRXFrNUtvUWFweXpJOFNrTnJQQVpWTUFvR0NDcUdTTTQ5QkFNQ0EwY0FNRVFDSUQ5Z3U5bU9TejVLaTd5cQpGU2czd1FGdXphb2pRakdiNVN4YUwwVzJTOUxXQWlCSzZIOXhNSENuZm5BV291bVpsdXNHd3RsOU5PVDhkdXFVCnR2eHRPOVY4S1E9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "0"
										}
									},
									"mod_policy": "Admins",
									"policies": {
										"Admins": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "MAJORITY",
													"sub_policy": "Admins"
												}
											},
											"version": "0"
										},
										"BlockValidation": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										},
										"Readers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Readers"
												}
											},
											"version": "0"
										},
										"Writers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										}
									},
									"values": {
										"BatchSize": {
											"mod_policy": "Admins",
											"value": {
												"absolute_max_bytes": 103809024,
												"max_message_count": 10,
												"preferred_max_bytes": 524288
											},
											"version": "0"
										},
										"BatchTimeout": {
											"mod_policy": "Admins",
											"value": {
												"timeout": "2s"
											},
											"version": "0"
										},
										"Capabilities": {
											"mod_policy": "Admins",
											"value": {
												"capabilities": {
													"V1_1": {}
												}
											},
											"version": "0"
										},
										"ChannelRestrictions": {
											"mod_policy": "Admins",
											"value": null,
											"version": "0"
										},
										"ConsensusType": {
											"mod_policy": "Admins",
											"value": {
												"metadata": null,
												"state": "STATE_NORMAL",
												"type": "solo"
											},
											"version": "0"
										}
									},
									"version": "0"
								}
							},
							"mod_policy": "Admins",
							"policies": {
								"Admins": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "MAJORITY",
											"sub_policy": "Admins"
										}
									},
									"version": "0"
								},
								"Readers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Readers"
										}
									},
									"version": "0"
								},
								"Writers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Writers"
										}
									},
									"version": "0"
								}
							},
							"values": {
								"BlockDataHashingStructure": {
									"mod_policy": "Admins",
									"value": {
										"width": 4294967295
									},
									"version": "0"
								},
								"Capabilities": {
									"mod_policy": "Admins",
									"value": {
										"capabilities": {
											"V1_3": {}
										}
									},
									"version": "0"
								},
								"HashingAlgorithm": {
									"mod_policy": "Admins",
									"value": {
										"name": "SHA256"
									},
									"version": "0"
								},
								"OrdererAddresses": {
									"mod_policy": "/Channel/Orderer/Admins",
									"value": {
										"addresses": [
											"orderer.example.com:7050"
										]
									},
									"version": "0"
								}
							},
							"version": "0"
						},
						"sequence": "0"
					},
					"last_update": null
				},
				"header": {
					"channel_header": {
						"channel_id": "byfn-sys-channel",
						"epoch": "0",
						"extension": null,
						"timestamp": "2019-08-01T02:18:40Z",
						"tls_cert_hash": null,
						"tx_id": "1c988034ab1d1658ebe508f89acd5f1e4e7bc2eeb6355e9d6084c36fba8ea562",
						"type": 1,
						"version": 1
					},
					"signature_header": {
						"creator": null,
						"nonce": "vPlG4HADPlXSQNWhjggubdDnUWXuH+wP"
					}
				}
			},
			"signature": null
		}]
	},
	"header": {
		"data_hash": "uzdDxPqI54ONV6pv/4m/l2OXNBFKuprirariF2kW278=",
		"number": "0",
		"previous_hash": null
	},
	"metadata": {
		"metadata": [
			"",
			"",
			"",
			""
		]
	}
}
```

### 应用通道创世块

系通道的配置的信息主要是：
1. 组织关系，权限、证书
1. 配置更新策略

> 某个链码的配置包含在链码里，不在通道的配置里。

```json
{
	"data": {
		"data": [{
			"payload": {
				"data": {
					"config": {
						"channel_group": {
							"groups": {
								"Application": {
									"groups": {
										"Org1MSP": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "Org1MSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "PEER"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		},
																		{
																			"signed_by": 2
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLVENDQWRDZ0F3SUJBZ0lRUEtTRHJHNWRTT0liVHRLM3pqcEhlVEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUd3eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVE4d0RRWURWUVFMRXdaamJHbGxiblF4SHpBZEJnTlZCQU1NRmtGa2JXbHVRRzl5Clp6RXVaWGhoYlhCc1pTNWpiMjB3V1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVFiNEZydmg1V2oKclBSOTFIdFdSaFVORVpxQXFOL2pEYkhUbUtDSXBkY3k3K2JGTUduaUprdTExaTl2ajN6TnNQMGQrSWlSRDdiMgpJSlhVaGxZbVJjcXVvMDB3U3pBT0JnTlZIUThCQWY4RUJBTUNCNEF3REFZRFZSMFRBUUgvQkFJd0FEQXJCZ05WCkhTTUVKREFpZ0NCVUdsTldyVThlZFBPakorMkc3M2UyU1FEdjVYdFUzSWYrSTJEMmo4VWdFREFLQmdncWhrak8KUFFRREFnTkhBREJFQWlBRFB6Qk5uKytROURXd0VUS0ErRTQyNG5vekVzZjRFd2JzQWxuUCtXNU10UUlnSDc3Two3dEVJUFZacTRvVUtSb1I5QWsvUEUrWUFzYk4vdHZhVlZlZ2dLTGc9Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": {
																"client_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
																	"organizational_unit_identifier": "client"
																},
																"enable": true,
																"peer_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
																	"organizational_unit_identifier": "peer"
																}
															},
															"intermediate_certs": [],
															"name": "Org1MSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo="
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNWakNDQWYyZ0F3SUJBZ0lRQldDNzUzQUphWXVOSkhqeVpGb1JvVEFLQmdncWhrak9QUVFEQWpCMk1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWZNQjBHQTFVRUF4TVdkR3h6ClkyRXViM0puTVM1bGVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTAKTURCYU1IWXhDekFKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSApFdzFUWVc0Z1JuSmhibU5wYzJOdk1Sa3dGd1lEVlFRS0V4QnZjbWN4TG1WNFlXMXdiR1V1WTI5dE1SOHdIUVlEClZRUURFeFowYkhOallTNXZjbWN4TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJS29aSXpqMEQKQVFjRFFnQUVJcWRZYWtLRmtKRm1NZEhDRnVGdkJIVXZMMFhUa0RJTG40Qm5vdW5GWUFaWmRFNFdpQ1lkcnJsSwpjTmpQWG1pNXZEajcrQmhoWXBaQjRnbHZRbUpDb2FOdE1Hc3dEZ1lEVlIwUEFRSC9CQVFEQWdHbU1CMEdBMVVkCkpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQVRBUEJnTlZIUk1CQWY4RUJUQURBUUgvTUNrR0ExVWQKRGdRaUJDQ0JzMVk5ZjhzTjFBYndZdnFzcEdLRzBIenhTQ2RyWEdHdUVvc2dGb3BQcVRBS0JnZ3Foa2pPUFFRRApBZ05IQURCRUFpQnF5VzBOL0xhMTRlTVh4SXIzNWVQbXVXdXpQQnJrd1h4RG9pd1RtdXJzZ1FJZ0JRRkZJdVl5CmRSVk4zOHdZSU5vUU16eW5Uek93NFNBMXpRdUs3QzViZGk0PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "0"
										},
										"Org2MSP": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "Org2MSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "PEER"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		},
																		{
																			"signed_by": 2
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": {
																"client_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
																	"organizational_unit_identifier": "client"
																},
																"enable": true,
																"peer_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
																	"organizational_unit_identifier": "peer"
																}
															},
															"intermediate_certs": [],
															"name": "Org2MSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNWekNDQWYyZ0F3SUJBZ0lRVGV5ZHpHQWVpNzB1ZkZzbTBmTWY1VEFLQmdncWhrak9QUVFEQWpCMk1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTWk1bGVHRnRjR3hsTG1OdmJURWZNQjBHQTFVRUF4TVdkR3h6ClkyRXViM0puTWk1bGVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTAKTURCYU1IWXhDekFKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSApFdzFUWVc0Z1JuSmhibU5wYzJOdk1Sa3dGd1lEVlFRS0V4QnZjbWN5TG1WNFlXMXdiR1V1WTI5dE1SOHdIUVlEClZRUURFeFowYkhOallTNXZjbWN5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJS29aSXpqMEQKQVFjRFFnQUVadTg3U0JzYWpnNXRTcFZKeGlZaE9YaWpOd3J0TmQvTFpuYkozWjUvY0dhaXZHeTZwQTB6Y1RjcApvdHN1YWJscE9BNHkxREEvbk5xaWtQa1dVVHZQcHFOdE1Hc3dEZ1lEVlIwUEFRSC9CQVFEQWdHbU1CMEdBMVVkCkpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQVRBUEJnTlZIUk1CQWY4RUJUQURBUUgvTUNrR0ExVWQKRGdRaUJDQUh4MDhOZ1FwdW9IR0tZWU9IYWh3VDg0cW9BN3p3dzFRTVNZT0h2VlZCWERBS0JnZ3Foa2pPUFFRRApBZ05JQURCRkFpRUF5QlBlakFHWjZtNXdWS244WHFhblFsMWUzYjNpUFBJVFdHaVN0dDBuZ3JJQ0lIUUJKRFd6CjFubzBMbnp0Nis4eEw5R25oY1NrZnZsWXR5MmhQcjdnTThFYgotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "0"
										}
									},
									"mod_policy": "Admins",
									"policies": {
										"Admins": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "MAJORITY",
													"sub_policy": "Admins"
												}
											},
											"version": "0"
										},
										"Readers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Readers"
												}
											},
											"version": "0"
										},
										"Writers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										}
									},
									"values": {
										"Capabilities": {
											"mod_policy": "Admins",
											"value": {
												"capabilities": {
													"V1_3": {}
												}
											},
											"version": "0"
										}
									},
									"version": "1"
								},
								"Orderer": {
									"groups": {
										"OrdererOrg": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "MEMBER"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "MEMBER"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNDekNDQWJHZ0F3SUJBZ0lSQUtuelI3NFZjN3RqOE5aQ21QV29QaWN3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRll4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJvd0dBWURWUVFEREJGQlpHMXBia0JsZUdGdGNHeGxMbU52YlRCWk1CTUdCeXFHU000OUFnRUdDQ3FHClNNNDlBd0VIQTBJQUJNUGUyNUtPU0hscUVZelJFVE83YXRjYWRvT0xnckRxelJQTjNjQ2RpR3A4QU4wdmdiTnAKTEEvTFJ0alFKbzdQaTZFZFlHaWh1MUNuRWgvNUxnYk90TmVqVFRCTE1BNEdBMVVkRHdFQi93UUVBd0lIZ0RBTQpCZ05WSFJNQkFmOEVBakFBTUNzR0ExVWRJd1FrTUNLQUlFQ0pBOWZTbDlUN0xsVWZ3QVhwM1V1cyt2YVpRbkZPCm9PSXJ2cmFrUDE3QU1Bb0dDQ3FHU000OUJBTUNBMGdBTUVVQ0lRQ1BjZVpmekNXa29MZ0N0NTMwbmEramY0a2cKN3BIWWwwY2NMTTZ4QkU0em5RSWdFVU52N2Q3MjQ2N1dnN0pMckZDb0x6eFhWUlMrN2UyWVJYSUlKOS9NVTJRPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": null,
															"intermediate_certs": [],
															"name": "OrdererMSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNQRENDQWVPZ0F3SUJBZ0lRSm9TdloyVE5oVTZjN0kvZ3VRNHYvVEFLQmdncWhrak9QUVFEQWpCcE1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVVNQklHQTFVRUNoTUxaWGhoYlhCc1pTNWpiMjB4RnpBVkJnTlZCQU1URG1OaExtVjRZVzF3CmJHVXVZMjl0TUI0WERURTVNRGd3TVRBeU1UUXdNRm9YRFRJNU1EY3lPVEF5TVRRd01Gb3dhVEVMTUFrR0ExVUUKQmhNQ1ZWTXhFekFSQmdOVkJBZ1RDa05oYkdsbWIzSnVhV0V4RmpBVUJnTlZCQWNURFZOaGJpQkdjbUZ1WTJsegpZMjh4RkRBU0JnTlZCQW9UQzJWNFlXMXdiR1V1WTI5dE1SY3dGUVlEVlFRREV3NWpZUzVsZUdGdGNHeGxMbU52CmJUQlpNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQTBJQUJFaUxuejB5TXp6K0dPNTlLZ3NMV0E1SVNaTXgKaUdRMVkrVHB3a1hZQXhjQnZENXZMMGhXcCtwWDdmSCtqaU9TOFBCMDFkamQ0TVJsb0lCQTgzYkxxdktqYlRCcgpNQTRHQTFVZER3RUIvd1FFQXdJQnBqQWRCZ05WSFNVRUZqQVVCZ2dyQmdFRkJRY0RBZ1lJS3dZQkJRVUhBd0V3CkR3WURWUjBUQVFIL0JBVXdBd0VCL3pBcEJnTlZIUTRFSWdRZ1FJa0QxOUtYMVBzdVZSL0FCZW5kUzZ6NjlwbEMKY1U2ZzRpdSt0cVEvWHNBd0NnWUlLb1pJemowRUF3SURSd0F3UkFJZ2JmRWVkMjJGRHFFSStwU0pKTXZrQi9GQQpFRitIUlg5OW91bGRLVlBqcDgwQ0lBS1VISmxlR01HYzF6dHRNSStCcHBldG53UU5nWjRsUDY5MUs0bENnU2hMCi0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNRekNDQWVxZ0F3SUJBZ0lSQVBWKy9UOVlSTjV0YmFXVGlETjg5Mmt3Q2dZSUtvWkl6ajBFQXdJd2JERUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJvd0dBWURWUVFERXhGMGJITmpZUzVsCmVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTBNREJhTUd3eEN6QUoKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSEV3MVRZVzRnUm5KaApibU5wYzJOdk1SUXdFZ1lEVlFRS0V3dGxlR0Z0Y0d4bExtTnZiVEVhTUJnR0ExVUVBeE1SZEd4elkyRXVaWGhoCmJYQnNaUzVqYjIwd1dUQVRCZ2NxaGtqT1BRSUJCZ2dxaGtqT1BRTUJCd05DQUFSUkxQK2ZLeFpnd2tFa2JIREoKb1JQak5ySXZBWWx2SHBMUTJoSXE1aXJQQnJlcEU4akRNTERyVklZR0NRdDBydGxjWFZTT3dZVTFkMXNOUy9USApSb1JvbzIwd2F6QU9CZ05WSFE4QkFmOEVCQU1DQWFZd0hRWURWUjBsQkJZd0ZBWUlLd1lCQlFVSEF3SUdDQ3NHCkFRVUZCd01CTUE4R0ExVWRFd0VCL3dRRk1BTUJBZjh3S1FZRFZSME9CQ0lFSUJWM1owTGw1TnpOcUdqVlpmbHIKUHRqRXFrNUtvUWFweXpJOFNrTnJQQVpWTUFvR0NDcUdTTTQ5QkFNQ0EwY0FNRVFDSUQ5Z3U5bU9TejVLaTd5cQpGU2czd1FGdXphb2pRakdiNVN4YUwwVzJTOUxXQWlCSzZIOXhNSENuZm5BV291bVpsdXNHd3RsOU5PVDhkdXFVCnR2eHRPOVY4S1E9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "0"
										}
									},
									"mod_policy": "Admins",
									"policies": {
										"Admins": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "MAJORITY",
													"sub_policy": "Admins"
												}
											},
											"version": "0"
										},
										"BlockValidation": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										},
										"Readers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Readers"
												}
											},
											"version": "0"
										},
										"Writers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										}
									},
									"values": {
										"BatchSize": {
											"mod_policy": "Admins",
											"value": {
												"absolute_max_bytes": 103809024,
												"max_message_count": 10,
												"preferred_max_bytes": 524288
											},
											"version": "0"
										},
										"BatchTimeout": {
											"mod_policy": "Admins",
											"value": {
												"timeout": "2s"
											},
											"version": "0"
										},
										"Capabilities": {
											"mod_policy": "Admins",
											"value": {
												"capabilities": {
													"V1_1": {}
												}
											},
											"version": "0"
										},
										"ChannelRestrictions": {
											"mod_policy": "Admins",
											"value": null,
											"version": "0"
										},
										"ConsensusType": {
											"mod_policy": "Admins",
											"value": {
												"metadata": null,
												"state": "STATE_NORMAL",
												"type": "solo"
											},
											"version": "0"
										}
									},
									"version": "0"
								}
							},
							"mod_policy": "Admins",
							"policies": {
								"Admins": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "MAJORITY",
											"sub_policy": "Admins"
										}
									},
									"version": "0"
								},
								"Readers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Readers"
										}
									},
									"version": "0"
								},
								"Writers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Writers"
										}
									},
									"version": "0"
								}
							},
							"values": {
								"BlockDataHashingStructure": {
									"mod_policy": "Admins",
									"value": {
										"width": 4294967295
									},
									"version": "0"
								},
								"Capabilities": {
									"mod_policy": "Admins",
									"value": {
										"capabilities": {
											"V1_3": {}
										}
									},
									"version": "0"
								},
								"Consortium": {
									"mod_policy": "Admins",
									"value": {
										"name": "SampleConsortium"
									},
									"version": "0"
								},
								"HashingAlgorithm": {
									"mod_policy": "Admins",
									"value": {
										"name": "SHA256"
									},
									"version": "0"
								},
								"OrdererAddresses": {
									"mod_policy": "/Channel/Orderer/Admins",
									"value": {
										"addresses": [
											"orderer.example.com:7050"
										]
									},
									"version": "0"
								}
							},
							"version": "0"
						},
						"sequence": "1"
					},
					"last_update": {
						"payload": {
							"data": {
								"config_update": {
									"channel_id": "mychannel",
									"isolated_data": {},
									"read_set": {
										"groups": {
											"Application": {
												"groups": {
													"Org1MSP": {
														"groups": {},
														"mod_policy": "",
														"policies": {},
														"values": {},
														"version": "0"
													},
													"Org2MSP": {
														"groups": {},
														"mod_policy": "",
														"policies": {},
														"values": {},
														"version": "0"
													}
												},
												"mod_policy": "",
												"policies": {},
												"values": {},
												"version": "0"
											}
										},
										"mod_policy": "",
										"policies": {},
										"values": {
											"Consortium": {
												"mod_policy": "",
												"value": null,
												"version": "0"
											}
										},
										"version": "0"
									},
									"write_set": {
										"groups": {
											"Application": {
												"groups": {
													"Org1MSP": {
														"groups": {},
														"mod_policy": "",
														"policies": {},
														"values": {},
														"version": "0"
													},
													"Org2MSP": {
														"groups": {},
														"mod_policy": "",
														"policies": {},
														"values": {},
														"version": "0"
													}
												},
												"mod_policy": "Admins",
												"policies": {
													"Admins": {
														"mod_policy": "Admins",
														"policy": {
															"type": 3,
															"value": {
																"rule": "MAJORITY",
																"sub_policy": "Admins"
															}
														},
														"version": "0"
													},
													"Readers": {
														"mod_policy": "Admins",
														"policy": {
															"type": 3,
															"value": {
																"rule": "ANY",
																"sub_policy": "Readers"
															}
														},
														"version": "0"
													},
													"Writers": {
														"mod_policy": "Admins",
														"policy": {
															"type": 3,
															"value": {
																"rule": "ANY",
																"sub_policy": "Writers"
															}
														},
														"version": "0"
													}
												},
												"values": {
													"Capabilities": {
														"mod_policy": "Admins",
														"value": {
															"capabilities": {
																"V1_3": {}
															}
														},
														"version": "0"
													}
												},
												"version": "1"
											}
										},
										"mod_policy": "",
										"policies": {},
										"values": {
											"Consortium": {
												"mod_policy": "",
												"value": {
													"name": "SampleConsortium"
												},
												"version": "0"
											}
										},
										"version": "0"
									}
								},
								"signatures": [{
									"signature": "MEQCIEuHMvFeH442rJZ8BURKXjseQ3MMpGO0VprPj8WdW5nOAiB1aDbHtIKo5ThxqvWCCJEdsXiKtAAbzN8DkE5VV4hUrg==",
									"signature_header": {
										"creator": {
											"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLVENDQWRDZ0F3SUJBZ0lRUEtTRHJHNWRTT0liVHRLM3pqcEhlVEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUd3eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVE4d0RRWURWUVFMRXdaamJHbGxiblF4SHpBZEJnTlZCQU1NRmtGa2JXbHVRRzl5Clp6RXVaWGhoYlhCc1pTNWpiMjB3V1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVFiNEZydmg1V2oKclBSOTFIdFdSaFVORVpxQXFOL2pEYkhUbUtDSXBkY3k3K2JGTUduaUprdTExaTl2ajN6TnNQMGQrSWlSRDdiMgpJSlhVaGxZbVJjcXVvMDB3U3pBT0JnTlZIUThCQWY4RUJBTUNCNEF3REFZRFZSMFRBUUgvQkFJd0FEQXJCZ05WCkhTTUVKREFpZ0NCVUdsTldyVThlZFBPakorMkc3M2UyU1FEdjVYdFUzSWYrSTJEMmo4VWdFREFLQmdncWhrak8KUFFRREFnTkhBREJFQWlBRFB6Qk5uKytROURXd0VUS0ErRTQyNG5vekVzZjRFd2JzQWxuUCtXNU10UUlnSDc3Two3dEVJUFZacTRvVUtSb1I5QWsvUEUrWUFzYk4vdHZhVlZlZ2dLTGc9Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
											"mspid": "Org1MSP"
										},
										"nonce": "d3VBJn3yTRNFp7JKJCL/XFObhMe3pS3W"
									}
								}]
							},
							"header": {
								"channel_header": {
									"channel_id": "mychannel",
									"epoch": "0",
									"extension": null,
									"timestamp": "2019-08-01T02:18:45Z",
									"tls_cert_hash": null,
									"tx_id": "",
									"type": 2,
									"version": 0
								},
								"signature_header": {
									"creator": {
										"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLVENDQWRDZ0F3SUJBZ0lRUEtTRHJHNWRTT0liVHRLM3pqcEhlVEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUd3eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVE4d0RRWURWUVFMRXdaamJHbGxiblF4SHpBZEJnTlZCQU1NRmtGa2JXbHVRRzl5Clp6RXVaWGhoYlhCc1pTNWpiMjB3V1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVFiNEZydmg1V2oKclBSOTFIdFdSaFVORVpxQXFOL2pEYkhUbUtDSXBkY3k3K2JGTUduaUprdTExaTl2ajN6TnNQMGQrSWlSRDdiMgpJSlhVaGxZbVJjcXVvMDB3U3pBT0JnTlZIUThCQWY4RUJBTUNCNEF3REFZRFZSMFRBUUgvQkFJd0FEQXJCZ05WCkhTTUVKREFpZ0NCVUdsTldyVThlZFBPakorMkc3M2UyU1FEdjVYdFUzSWYrSTJEMmo4VWdFREFLQmdncWhrak8KUFFRREFnTkhBREJFQWlBRFB6Qk5uKytROURXd0VUS0ErRTQyNG5vekVzZjRFd2JzQWxuUCtXNU10UUlnSDc3Two3dEVJUFZacTRvVUtSb1I5QWsvUEUrWUFzYk4vdHZhVlZlZ2dLTGc9Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
										"mspid": "Org1MSP"
									},
									"nonce": "tGLvhwDbf/Py2be3k/WLsZzKRPcry9po"
								}
							}
						},
						"signature": "MEUCIQDmxLlWl9H6CdVqUbQ6OPmeZ1JnJYRYDtD18KQ1b82WkwIgNxFDuaYCdBs3ZzZxvsF2CD7pAtrbER4ZDOq3SkKie7E="
					}
				},
				"header": {
					"channel_header": {
						"channel_id": "mychannel",
						"epoch": "0",
						"extension": null,
						"timestamp": "2019-08-01T02:18:45Z",
						"tls_cert_hash": null,
						"tx_id": "",
						"type": 1,
						"version": 0
					},
					"signature_header": {
						"creator": {
							"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNEVENDQWJPZ0F3SUJBZ0lSQU0rUFQ2YTJsYm1EY0NpNEVhTEFSeFl3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRmd4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJ3d0dnWURWUVFERXhOdmNtUmxjbVZ5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJCktvWkl6ajBEQVFjRFFnQUVZVGcwdXZJMVZ0dEsrb2o2MG9LRjRtWlc4YlFXN0FIRFpZcFZueEdoTE5Kems2cmwKTU1uS0RiRmxibElETE9qK0tiakVwOW9WdEN6OVBsbk4xTmhHSEtOTk1Fc3dEZ1lEVlIwUEFRSC9CQVFEQWdlQQpNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqQkNRd0lvQWdRSWtEMTlLWDFQc3VWUi9BQmVuZFM2ejY5cGxDCmNVNmc0aXUrdHFRL1hzQXdDZ1lJS29aSXpqMEVBd0lEU0FBd1JRSWhBTnd0cDQzMUdkYkdqb3pXRU1DQWdwNWIKeFdnMHNRMVlGbG9TYzF1MFFRU3FBaUF1TVNkc1AvMXZoclhVcGtoT1Voa3NwRjYrYVl1V2ozazZaVE84RWV3agpqdz09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
							"mspid": "OrdererMSP"
						},
						"nonce": "xfIU/l1eFdFbtagz4fuZaJzuPW/hroRx"
					}
				}
			},
			"signature": "MEUCIQDm/oh3UE8/ZQu0Cad7rJw/FaUsCu4SsXZfxY3VSaMsCQIgbEsRitpgRb9vy80u9C7z103nj1/kQtka1LRiGSLy/6I="
		}]
	},
	"header": {
		"data_hash": "tJk5enGTIZYB/+XlYPbOwpjRH9341YajXd5YaWv86/k=",
		"number": "0",
		"previous_hash": null
	},
	"metadata": {
		"metadata": [
			"",
			"",
			"AA==",
			""
		]
	}
}
```

### 应用通道配置块

```json
{
	"data": {
		"data": [{
			"payload": {
				"data": {
					"config": {
						"channel_group": {
							"groups": {
								"Application": {
									"groups": {
										"Org1MSP": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "Org1MSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "PEER"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		},
																		{
																			"signed_by": 2
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org1MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"AnchorPeers": {
													"mod_policy": "Admins",
													"value": {
														"anchor_peers": [{
															"host": "peer0.org1.example.com",
															"port": 7051
														}]
													},
													"version": "0"
												},
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLVENDQWRDZ0F3SUJBZ0lRUEtTRHJHNWRTT0liVHRLM3pqcEhlVEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUd3eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVE4d0RRWURWUVFMRXdaamJHbGxiblF4SHpBZEJnTlZCQU1NRmtGa2JXbHVRRzl5Clp6RXVaWGhoYlhCc1pTNWpiMjB3V1RBVEJnY3Foa2pPUFFJQkJnZ3Foa2pPUFFNQkJ3TkNBQVFiNEZydmg1V2oKclBSOTFIdFdSaFVORVpxQXFOL2pEYkhUbUtDSXBkY3k3K2JGTUduaUprdTExaTl2ajN6TnNQMGQrSWlSRDdiMgpJSlhVaGxZbVJjcXVvMDB3U3pBT0JnTlZIUThCQWY4RUJBTUNCNEF3REFZRFZSMFRBUUgvQkFJd0FEQXJCZ05WCkhTTUVKREFpZ0NCVUdsTldyVThlZFBPakorMkc3M2UyU1FEdjVYdFUzSWYrSTJEMmo4VWdFREFLQmdncWhrak8KUFFRREFnTkhBREJFQWlBRFB6Qk5uKytROURXd0VUS0ErRTQyNG5vekVzZjRFd2JzQWxuUCtXNU10UUlnSDc3Two3dEVJUFZacTRvVUtSb1I5QWsvUEUrWUFzYk4vdHZhVlZlZ2dLTGc9Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": {
																"client_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
																	"organizational_unit_identifier": "client"
																},
																"enable": true,
																"peer_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
																	"organizational_unit_identifier": "peer"
																}
															},
															"intermediate_certs": [],
															"name": "Org1MSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVRENDQWZlZ0F3SUJBZ0lRSnJqamM3b1RSLy8zSG9wcDFYY0Y4VEFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUhNeEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVJrd0Z3WURWUVFLRXhCdmNtY3hMbVY0WVcxd2JHVXVZMjl0TVJ3d0dnWURWUVFECkV4TmpZUzV2Y21jeExtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUUKSmNFQkUvUlF1Ty9JR2h0QWJjSnhnTEhyMHNEbENFS0dpQnA3NXlRYytjdUFQK21NWDI4TGtWTERJaGhELzV5MgpiMTJUM1o4Z1Y1N2tMOHdrUTM1SXpxTnRNR3N3RGdZRFZSMFBBUUgvQkFRREFnR21NQjBHQTFVZEpRUVdNQlFHCkNDc0dBUVVGQndNQ0JnZ3JCZ0VGQlFjREFUQVBCZ05WSFJNQkFmOEVCVEFEQVFIL01Da0dBMVVkRGdRaUJDQlUKR2xOV3JVOGVkUE9qSisyRzczZTJTUUR2NVh0VTNJZitJMkQyajhVZ0VEQUtCZ2dxaGtqT1BRUURBZ05IQURCRQpBaUF3YzVYMVZLVGZQM0ZqL0o1Tk9wVHlNU08vU2MzcnFhbmxOelRUbk5VRmZnSWdNZi9HVWpjcjhra1V2Y2hBCjlzM0NIc1VYZ1loTWNPaHVxWFJmZHdTRC9XRT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo="
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNWakNDQWYyZ0F3SUJBZ0lRQldDNzUzQUphWXVOSkhqeVpGb1JvVEFLQmdncWhrak9QUVFEQWpCMk1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWZNQjBHQTFVRUF4TVdkR3h6ClkyRXViM0puTVM1bGVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTAKTURCYU1IWXhDekFKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSApFdzFUWVc0Z1JuSmhibU5wYzJOdk1Sa3dGd1lEVlFRS0V4QnZjbWN4TG1WNFlXMXdiR1V1WTI5dE1SOHdIUVlEClZRUURFeFowYkhOallTNXZjbWN4TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJS29aSXpqMEQKQVFjRFFnQUVJcWRZYWtLRmtKRm1NZEhDRnVGdkJIVXZMMFhUa0RJTG40Qm5vdW5GWUFaWmRFNFdpQ1lkcnJsSwpjTmpQWG1pNXZEajcrQmhoWXBaQjRnbHZRbUpDb2FOdE1Hc3dEZ1lEVlIwUEFRSC9CQVFEQWdHbU1CMEdBMVVkCkpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQVRBUEJnTlZIUk1CQWY4RUJUQURBUUgvTUNrR0ExVWQKRGdRaUJDQ0JzMVk5ZjhzTjFBYndZdnFzcEdLRzBIenhTQ2RyWEdHdUVvc2dGb3BQcVRBS0JnZ3Foa2pPUFFRRApBZ05IQURCRUFpQnF5VzBOL0xhMTRlTVh4SXIzNWVQbXVXdXpQQnJrd1h4RG9pd1RtdXJzZ1FJZ0JRRkZJdVl5CmRSVk4zOHdZSU5vUU16eW5Uek93NFNBMXpRdUs3QzViZGk0PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "1"
										},
										"Org2MSP": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "Org2MSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "PEER"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		},
																		{
																			"signed_by": 2
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "ADMIN"
																	},
																	"principal_classification": "ROLE"
																},
																{
																	"principal": {
																		"msp_identifier": "Org2MSP",
																		"role": "CLIENT"
																	},
																	"principal_classification": "ROLE"
																}
															],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																			"signed_by": 0
																		},
																		{
																			"signed_by": 1
																		}
																	]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"AnchorPeers": {
													"mod_policy": "Admins",
													"value": {
														"anchor_peers": [{
															"host": "peer0.org2.example.com",
															"port": 9051
														}]
													},
													"version": "0"
												},
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": {
																"client_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
																	"organizational_unit_identifier": "client"
																},
																"enable": true,
																"peer_ou_identifier": {
																	"certificate": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
																	"organizational_unit_identifier": "peer"
																}
															},
															"intermediate_certs": [],
															"name": "Org2MSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWZpZ0F3SUJBZ0lSQU1rYVQ5em1XTEo2bFVNUlhRZmgrSTh3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCek1Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFWk1CY0dBMVVFQ2hNUWIzSm5NaTVsZUdGdGNHeGxMbU52YlRFY01Cb0dBMVVFCkF4TVRZMkV1YjNKbk1pNWxlR0Z0Y0d4bExtTnZiVEJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUEKQkpZSEEzOVNmbjczdXFIT0JrTzJ0R1pucFdvR09NRHFmRkJwZG9FOXhCTzNCdFZaT2hMblBYY01MRGErcTdJMQpxbFJHQmh4TTVpLzZ1L0V4Z2psaTVVK2piVEJyTUE0R0ExVWREd0VCL3dRRUF3SUJwakFkQmdOVkhTVUVGakFVCkJnZ3JCZ0VGQlFjREFnWUlLd1lCQlFVSEF3RXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QXBCZ05WSFE0RUlnUWcKbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEVBd0lEU0FBdwpSUUloQUpzYVBHWklWTkU4S09zbjJzZ2ZSSlo1ek1BbEpIS1p3V1lJQTljVVNWS1FBaUF6ZkIrL0VMUFQrbFFmCjZUNmhEQXU1bkwwRGpoUUxqa0ZmL3RXNUVDMzlCQT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNWekNDQWYyZ0F3SUJBZ0lRVGV5ZHpHQWVpNzB1ZkZzbTBmTWY1VEFLQmdncWhrak9QUVFEQWpCMk1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTWk1bGVHRnRjR3hsTG1OdmJURWZNQjBHQTFVRUF4TVdkR3h6ClkyRXViM0puTWk1bGVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTAKTURCYU1IWXhDekFKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSApFdzFUWVc0Z1JuSmhibU5wYzJOdk1Sa3dGd1lEVlFRS0V4QnZjbWN5TG1WNFlXMXdiR1V1WTI5dE1SOHdIUVlEClZRUURFeFowYkhOallTNXZjbWN5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJS29aSXpqMEQKQVFjRFFnQUVadTg3U0JzYWpnNXRTcFZKeGlZaE9YaWpOd3J0TmQvTFpuYkozWjUvY0dhaXZHeTZwQTB6Y1RjcApvdHN1YWJscE9BNHkxREEvbk5xaWtQa1dVVHZQcHFOdE1Hc3dEZ1lEVlIwUEFRSC9CQVFEQWdHbU1CMEdBMVVkCkpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQVRBUEJnTlZIUk1CQWY4RUJUQURBUUgvTUNrR0ExVWQKRGdRaUJDQUh4MDhOZ1FwdW9IR0tZWU9IYWh3VDg0cW9BN3p3dzFRTVNZT0h2VlZCWERBS0JnZ3Foa2pPUFFRRApBZ05JQURCRkFpRUF5QlBlakFHWjZtNXdWS244WHFhblFsMWUzYjNpUFBJVFdHaVN0dDBuZ3JJQ0lIUUJKRFd6CjFubzBMbnp0Nis4eEw5R25oY1NrZnZsWXR5MmhQcjdnTThFYgotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "1"
										}
									},
									"mod_policy": "Admins",
									"policies": {
										"Admins": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "MAJORITY",
													"sub_policy": "Admins"
												}
											},
											"version": "0"
										},
										"Readers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Readers"
												}
											},
											"version": "0"
										},
										"Writers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										}
									},
									"values": {
										"Capabilities": {
											"mod_policy": "Admins",
											"value": {
												"capabilities": {
													"V1_3": {}
												}
											},
											"version": "0"
										}
									},
									"version": "1"
								},
								"Orderer": {
									"groups": {
										"OrdererOrg": {
											"groups": {},
											"mod_policy": "Admins",
											"policies": {
												"Admins": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "ADMIN"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Readers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "MEMBER"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												},
												"Writers": {
													"mod_policy": "Admins",
													"policy": {
														"type": 1,
														"value": {
															"identities": [{
																"principal": {
																	"msp_identifier": "OrdererMSP",
																	"role": "MEMBER"
																},
																"principal_classification": "ROLE"
															}],
															"rule": {
																"n_out_of": {
																	"n": 1,
																	"rules": [{
																		"signed_by": 0
																	}]
																}
															},
															"version": 0
														}
													},
													"version": "0"
												}
											},
											"values": {
												"MSP": {
													"mod_policy": "Admins",
													"value": {
														"config": {
															"admins": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNDekNDQWJHZ0F3SUJBZ0lSQUtuelI3NFZjN3RqOE5aQ21QV29QaWN3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRll4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJvd0dBWURWUVFEREJGQlpHMXBia0JsZUdGdGNHeGxMbU52YlRCWk1CTUdCeXFHU000OUFnRUdDQ3FHClNNNDlBd0VIQTBJQUJNUGUyNUtPU0hscUVZelJFVE83YXRjYWRvT0xnckRxelJQTjNjQ2RpR3A4QU4wdmdiTnAKTEEvTFJ0alFKbzdQaTZFZFlHaWh1MUNuRWgvNUxnYk90TmVqVFRCTE1BNEdBMVVkRHdFQi93UUVBd0lIZ0RBTQpCZ05WSFJNQkFmOEVBakFBTUNzR0ExVWRJd1FrTUNLQUlFQ0pBOWZTbDlUN0xsVWZ3QVhwM1V1cyt2YVpRbkZPCm9PSXJ2cmFrUDE3QU1Bb0dDQ3FHU000OUJBTUNBMGdBTUVVQ0lRQ1BjZVpmekNXa29MZ0N0NTMwbmEramY0a2cKN3BIWWwwY2NMTTZ4QkU0em5RSWdFVU52N2Q3MjQ2N1dnN0pMckZDb0x6eFhWUlMrN2UyWVJYSUlKOS9NVTJRPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															],
															"crypto_config": {
																"identity_identifier_hash_function": "SHA256",
																"signature_hash_family": "SHA2"
															},
															"fabric_node_ous": null,
															"intermediate_certs": [],
															"name": "OrdererMSP",
															"organizational_unit_identifiers": [],
															"revocation_list": [],
															"root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNQRENDQWVPZ0F3SUJBZ0lRSm9TdloyVE5oVTZjN0kvZ3VRNHYvVEFLQmdncWhrak9QUVFEQWpCcE1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVVNQklHQTFVRUNoTUxaWGhoYlhCc1pTNWpiMjB4RnpBVkJnTlZCQU1URG1OaExtVjRZVzF3CmJHVXVZMjl0TUI0WERURTVNRGd3TVRBeU1UUXdNRm9YRFRJNU1EY3lPVEF5TVRRd01Gb3dhVEVMTUFrR0ExVUUKQmhNQ1ZWTXhFekFSQmdOVkJBZ1RDa05oYkdsbWIzSnVhV0V4RmpBVUJnTlZCQWNURFZOaGJpQkdjbUZ1WTJsegpZMjh4RkRBU0JnTlZCQW9UQzJWNFlXMXdiR1V1WTI5dE1SY3dGUVlEVlFRREV3NWpZUzVsZUdGdGNHeGxMbU52CmJUQlpNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQTBJQUJFaUxuejB5TXp6K0dPNTlLZ3NMV0E1SVNaTXgKaUdRMVkrVHB3a1hZQXhjQnZENXZMMGhXcCtwWDdmSCtqaU9TOFBCMDFkamQ0TVJsb0lCQTgzYkxxdktqYlRCcgpNQTRHQTFVZER3RUIvd1FFQXdJQnBqQWRCZ05WSFNVRUZqQVVCZ2dyQmdFRkJRY0RBZ1lJS3dZQkJRVUhBd0V3CkR3WURWUjBUQVFIL0JBVXdBd0VCL3pBcEJnTlZIUTRFSWdRZ1FJa0QxOUtYMVBzdVZSL0FCZW5kUzZ6NjlwbEMKY1U2ZzRpdSt0cVEvWHNBd0NnWUlLb1pJemowRUF3SURSd0F3UkFJZ2JmRWVkMjJGRHFFSStwU0pKTXZrQi9GQQpFRitIUlg5OW91bGRLVlBqcDgwQ0lBS1VISmxlR01HYzF6dHRNSStCcHBldG53UU5nWjRsUDY5MUs0bENnU2hMCi0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K"
															],
															"signing_identity": null,
															"tls_intermediate_certs": [],
															"tls_root_certs": [
																"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNRekNDQWVxZ0F3SUJBZ0lSQVBWKy9UOVlSTjV0YmFXVGlETjg5Mmt3Q2dZSUtvWkl6ajBFQXdJd2JERUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJvd0dBWURWUVFERXhGMGJITmpZUzVsCmVHRnRjR3hsTG1OdmJUQWVGdzB4T1RBNE1ERXdNakUwTURCYUZ3MHlPVEEzTWprd01qRTBNREJhTUd3eEN6QUoKQmdOVkJBWVRBbFZUTVJNd0VRWURWUVFJRXdwRFlXeHBabTl5Ym1saE1SWXdGQVlEVlFRSEV3MVRZVzRnUm5KaApibU5wYzJOdk1SUXdFZ1lEVlFRS0V3dGxlR0Z0Y0d4bExtTnZiVEVhTUJnR0ExVUVBeE1SZEd4elkyRXVaWGhoCmJYQnNaUzVqYjIwd1dUQVRCZ2NxaGtqT1BRSUJCZ2dxaGtqT1BRTUJCd05DQUFSUkxQK2ZLeFpnd2tFa2JIREoKb1JQak5ySXZBWWx2SHBMUTJoSXE1aXJQQnJlcEU4akRNTERyVklZR0NRdDBydGxjWFZTT3dZVTFkMXNOUy9USApSb1JvbzIwd2F6QU9CZ05WSFE4QkFmOEVCQU1DQWFZd0hRWURWUjBsQkJZd0ZBWUlLd1lCQlFVSEF3SUdDQ3NHCkFRVUZCd01CTUE4R0ExVWRFd0VCL3dRRk1BTUJBZjh3S1FZRFZSME9CQ0lFSUJWM1owTGw1TnpOcUdqVlpmbHIKUHRqRXFrNUtvUWFweXpJOFNrTnJQQVpWTUFvR0NDcUdTTTQ5QkFNQ0EwY0FNRVFDSUQ5Z3U5bU9TejVLaTd5cQpGU2czd1FGdXphb2pRakdiNVN4YUwwVzJTOUxXQWlCSzZIOXhNSENuZm5BV291bVpsdXNHd3RsOU5PVDhkdXFVCnR2eHRPOVY4S1E9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
															]
														},
														"type": 0
													},
													"version": "0"
												}
											},
											"version": "0"
										}
									},
									"mod_policy": "Admins",
									"policies": {
										"Admins": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "MAJORITY",
													"sub_policy": "Admins"
												}
											},
											"version": "0"
										},
										"BlockValidation": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										},
										"Readers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Readers"
												}
											},
											"version": "0"
										},
										"Writers": {
											"mod_policy": "Admins",
											"policy": {
												"type": 3,
												"value": {
													"rule": "ANY",
													"sub_policy": "Writers"
												}
											},
											"version": "0"
										}
									},
									"values": {
										"BatchSize": {
											"mod_policy": "Admins",
											"value": {
												"absolute_max_bytes": 103809024,
												"max_message_count": 10,
												"preferred_max_bytes": 524288
											},
											"version": "0"
										},
										"BatchTimeout": {
											"mod_policy": "Admins",
											"value": {
												"timeout": "2s"
											},
											"version": "0"
										},
										"Capabilities": {
											"mod_policy": "Admins",
											"value": {
												"capabilities": {
													"V1_1": {}
												}
											},
											"version": "0"
										},
										"ChannelRestrictions": {
											"mod_policy": "Admins",
											"value": null,
											"version": "0"
										},
										"ConsensusType": {
											"mod_policy": "Admins",
											"value": {
												"metadata": null,
												"state": "STATE_NORMAL",
												"type": "solo"
											},
											"version": "0"
										}
									},
									"version": "0"
								}
							},
							"mod_policy": "Admins",
							"policies": {
								"Admins": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "MAJORITY",
											"sub_policy": "Admins"
										}
									},
									"version": "0"
								},
								"Readers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Readers"
										}
									},
									"version": "0"
								},
								"Writers": {
									"mod_policy": "Admins",
									"policy": {
										"type": 3,
										"value": {
											"rule": "ANY",
											"sub_policy": "Writers"
										}
									},
									"version": "0"
								}
							},
							"values": {
								"BlockDataHashingStructure": {
									"mod_policy": "Admins",
									"value": {
										"width": 4294967295
									},
									"version": "0"
								},
								"Capabilities": {
									"mod_policy": "Admins",
									"value": {
										"capabilities": {
											"V1_3": {}
										}
									},
									"version": "0"
								},
								"Consortium": {
									"mod_policy": "Admins",
									"value": {
										"name": "SampleConsortium"
									},
									"version": "0"
								},
								"HashingAlgorithm": {
									"mod_policy": "Admins",
									"value": {
										"name": "SHA256"
									},
									"version": "0"
								},
								"OrdererAddresses": {
									"mod_policy": "/Channel/Orderer/Admins",
									"value": {
										"addresses": [
											"orderer.example.com:7050"
										]
									},
									"version": "0"
								}
							},
							"version": "0"
						},
						"sequence": "3"
					},
					"last_update": {
						"payload": {
							"data": {
								"config_update": {
									"channel_id": "mychannel",
									"isolated_data": {},
									"read_set": {
										"groups": {
											"Application": {
												"groups": {
													"Org2MSP": {
														"groups": {},
														"mod_policy": "",
														"policies": {
															"Admins": {
																"mod_policy": "",
																"policy": null,
																"version": "0"
															},
															"Readers": {
																"mod_policy": "",
																"policy": null,
																"version": "0"
															},
															"Writers": {
																"mod_policy": "",
																"policy": null,
																"version": "0"
															}
														},
														"values": {
															"MSP": {
																"mod_policy": "",
																"value": null,
																"version": "0"
															}
														},
														"version": "0"
													}
												},
												"mod_policy": "Admins",
												"policies": {},
												"values": {},
												"version": "1"
											}
										},
										"mod_policy": "",
										"policies": {},
										"values": {},
										"version": "0"
									},
									"write_set": {
										"groups": {
											"Application": {
												"groups": {
													"Org2MSP": {
														"groups": {},
														"mod_policy": "Admins",
														"policies": {
															"Admins": {
																"mod_policy": "",
																"policy": null,
																"version": "0"
															},
															"Readers": {
																"mod_policy": "",
																"policy": null,
																"version": "0"
															},
															"Writers": {
																"mod_policy": "",
																"policy": null,
																"version": "0"
															}
														},
														"values": {
															"AnchorPeers": {
																"mod_policy": "Admins",
																"value": {
																	"anchor_peers": [{
																		"host": "peer0.org2.example.com",
																		"port": 9051
																	}]
																},
																"version": "0"
															},
															"MSP": {
																"mod_policy": "",
																"value": null,
																"version": "0"
															}
														},
														"version": "1"
													}
												},
												"mod_policy": "Admins",
												"policies": {},
												"values": {},
												"version": "1"
											}
										},
										"mod_policy": "",
										"policies": {},
										"values": {},
										"version": "0"
									}
								},
								"signatures": [{
									"signature": "MEQCIG3LXxjcsZ+8jSCZEZbUMqWOslJGqFAzNz1zz/JlqssmAiBaO8xvVXT1vusIAQaLsldAXXU9np280n5UwYyJLsuYBw==",
									"signature_header": {
										"creator": {
											"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
											"mspid": "Org2MSP"
										},
										"nonce": "InlUsKBi6xaHgTtivM0cOO5Vabiw6oSS"
									}
								}]
							},
							"header": {
								"channel_header": {
									"channel_id": "mychannel",
									"epoch": "0",
									"extension": null,
									"timestamp": "2019-08-01T02:19:01Z",
									"tls_cert_hash": null,
									"tx_id": "",
									"type": 2,
									"version": 0
								},
								"signature_header": {
									"creator": {
										"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
										"mspid": "Org2MSP"
									},
									"nonce": "5U3mT268xjTWiMCBXcO2+wEJcikv2YJj"
								}
							}
						},
						"signature": "MEUCIQCpsp/8oaQEmtp5baG8ogkrXgP+unRtBIQzLgsVf9AlbQIgLrQ6mG1TyxMEdFtL1rjaLLj9iL3A/qzFSh3jTiUH7ME="
					}
				},
				"header": {
					"channel_header": {
						"channel_id": "mychannel",
						"epoch": "0",
						"extension": null,
						"timestamp": "2019-08-01T02:19:01Z",
						"tls_cert_hash": null,
						"tx_id": "",
						"type": 1,
						"version": 0
					},
					"signature_header": {
						"creator": {
							"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNEVENDQWJPZ0F3SUJBZ0lSQU0rUFQ2YTJsYm1EY0NpNEVhTEFSeFl3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRmd4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJ3d0dnWURWUVFERXhOdmNtUmxjbVZ5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJCktvWkl6ajBEQVFjRFFnQUVZVGcwdXZJMVZ0dEsrb2o2MG9LRjRtWlc4YlFXN0FIRFpZcFZueEdoTE5Kems2cmwKTU1uS0RiRmxibElETE9qK0tiakVwOW9WdEN6OVBsbk4xTmhHSEtOTk1Fc3dEZ1lEVlIwUEFRSC9CQVFEQWdlQQpNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqQkNRd0lvQWdRSWtEMTlLWDFQc3VWUi9BQmVuZFM2ejY5cGxDCmNVNmc0aXUrdHFRL1hzQXdDZ1lJS29aSXpqMEVBd0lEU0FBd1JRSWhBTnd0cDQzMUdkYkdqb3pXRU1DQWdwNWIKeFdnMHNRMVlGbG9TYzF1MFFRU3FBaUF1TVNkc1AvMXZoclhVcGtoT1Voa3NwRjYrYVl1V2ozazZaVE84RWV3agpqdz09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K",
							"mspid": "OrdererMSP"
						},
						"nonce": "6oiXowzUUpo6JFlSyB50x1Ma12ZoFUba"
					}
				}
			},
			"signature": "MEQCIBNyEeC+cWzOCLq9J9haktAwM3e+BBjNeEQc55xiB2yPAiAIF+KkWEh+RARJM/iA15JSfgvCP9zwgIrvSxO/Ki/KQQ=="
		}]
	},
	"header": {
		"data_hash": "35xdxe58OecLRLqrdJREGDaw+XEVSDFvN4Vk8v/GNPA=",
		"number": "2",
		"previous_hash": "6xJ0rP3gVYFZpwcBDW/i84IIkTi8Jj0cWBeX2GXsCUQ="
	},
	"metadata": {
		"metadata": [
			"CgQKAggCEv0GCrIGCpUGCgpPcmRlcmVyTVNQEoYGLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNEVENDQWJPZ0F3SUJBZ0lSQU0rUFQ2YTJsYm1EY0NpNEVhTEFSeFl3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRmd4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJ3d0dnWURWUVFERXhOdmNtUmxjbVZ5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJCktvWkl6ajBEQVFjRFFnQUVZVGcwdXZJMVZ0dEsrb2o2MG9LRjRtWlc4YlFXN0FIRFpZcFZueEdoTE5Kems2cmwKTU1uS0RiRmxibElETE9qK0tiakVwOW9WdEN6OVBsbk4xTmhHSEtOTk1Fc3dEZ1lEVlIwUEFRSC9CQVFEQWdlQQpNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqQkNRd0lvQWdRSWtEMTlLWDFQc3VWUi9BQmVuZFM2ejY5cGxDCmNVNmc0aXUrdHFRL1hzQXdDZ1lJS29aSXpqMEVBd0lEU0FBd1JRSWhBTnd0cDQzMUdkYkdqb3pXRU1DQWdwNWIKeFdnMHNRMVlGbG9TYzF1MFFRU3FBaUF1TVNkc1AvMXZoclhVcGtoT1Voa3NwRjYrYVl1V2ozazZaVE84RWV3agpqdz09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0KEhig4rR9Ua6PViqus4vI1MI7T5OdGzlRTykSRjBEAiBI+JDzNh3q5fzUahojTbQkWxVBf+QksfhsRNdTtEVYfgIgJqbdOquXXkWQ8kB7xKjub/sfbX1Cnm2Vo2uHlSZAIG4=",
			"CgIIAg==",
			"AA==",
			""
		]
	}
}
```

### 应用通道普通区块

普通区块指不修改配置的区块，里面包含2类交易：
1. 实例化链码的交易
1. 调用链码的交易

实例化实际Invoke的是LSCC，调用应用chaincode，也会先用到LSCC，再到应用chaincode，那么怎么区分当前到底是Invoke哪个chaincode？区块中的`chaincode_proposal_payload`，代表了当前操作的chaincode。

`ns_rwset`是操作过程的读写集，包含LSCC和应用chaincode的。

#### 实例化chaincode

`ns_rwset`包含2个`collection_hashed_rwset`：
- 第1个：说明了当前操作的是lscc，读`mycc`没结果，然后把`mycc`放到写集，这是创建合约的典型过程。
- 第2个：是进行chaincode的初始化，也是只写入，这里是设置a和b的值。

```json
{
	"data": {
		"data": [{
			"payload": {
				"data": {
					"actions": [{
						"header": {
							"creator": {
								"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
								"mspid": "Org2MSP"
							},
							"nonce": "CLJ2euIe3YSE7LhNiTuXdBCS2DnvabH2"
						},
						"payload": {
							"action": {
								"endorsements": [{
									"endorser": "CgdPcmcyTVNQEqYGLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNKekNDQWM2Z0F3SUJBZ0lRVHA5QTREM25oa2NJaVdXRk4xRUZQakFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTWk1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NaTVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUdveEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVEwd0N3WURWUVFMRXdSd1pXVnlNUjh3SFFZRFZRUURFeFp3WldWeU1DNXZjbWN5CkxtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVSRjBFV0NuQW5oMm8KcnFFazhmRTlLdEFCdmJIc1FYTHhMRnZZdlZYVlFPS1crVDBpVk44eWdQbTZlM0kxcG5FTS9hK3Vha2dtYWNmOApzVnVZVERMSythTk5NRXN3RGdZRFZSMFBBUUgvQkFRREFnZUFNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqCkJDUXdJb0FnbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEUKQXdJRFJ3QXdSQUlnVTMwdllnVHpCYS84ZGFaZlpBYThzLzN3RFdZdlRpL1BEY3RuWFJBT043QUNJQmNvQzlXSgpYK28rdHFUUDZybS8vdWxpUU02Rk53cUtBSDlYQWxOcVdhbWsKLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
									"signature": "MEUCIQCRu+F6XBVrfy24JtxuAiy9+3PNYy6tRmKDmgtmGx0OLAIgQeMPTKzPhh9fH39tmZEDjJCGet/ob2BzbRExZIYq2po="
								}],
								"proposal_response_payload": {
									"extension": {
										"chaincode_id": {
											"name": "lscc",
											"path": "",
											"version": "1.4.2"
										},
										"events": null,
										"response": {
											"message": "",
											"payload": "CgRteWNjEgMxLjAaBGVzY2MiBHZzY2MqLBIMEgoIAhICCAASAggBGg0SCwoHT3JnMU1TUBADGg0SCwoHT3JnMk1TUBADMkQKIJJH+4JOIdCHD/55PPBgJOZehvHg5Ytk6QxbGU9uNzQAEiAHHxQpHhUrsq6I5/355ad00xNha6MVSoT2oNRaF19jJjogR2/KGpSSdAAZcfHsKDbLCTIfC3Emizdi1okxyT8hgTRCLBIMEgoIARICCAASAggBGg0SCwoHT3JnMU1TUBABGg0SCwoHT3JnMk1TUBAB",
											"status": 200
										},
										"results": {
											"data_model": "KV",
											"ns_rwset": [{
													"collection_hashed_rwset": [],
													"namespace": "lscc",
													"rwset": {
														"metadata_writes": [],
														"range_queries_info": [],
														"reads": [{
															"key": "mycc",
															"version": null
														}],
														"writes": [{
															"is_delete": false,
															"key": "mycc",
															"value": "CgRteWNjEgMxLjAaBGVzY2MiBHZzY2MqLBIMEgoIAhICCAASAggBGg0SCwoHT3JnMU1TUBADGg0SCwoHT3JnMk1TUBADMkQKIJJH+4JOIdCHD/55PPBgJOZehvHg5Ytk6QxbGU9uNzQAEiAHHxQpHhUrsq6I5/355ad00xNha6MVSoT2oNRaF19jJjogR2/KGpSSdAAZcfHsKDbLCTIfC3Emizdi1okxyT8hgTRCLBIMEgoIARICCAASAggBGg0SCwoHT3JnMU1TUBABGg0SCwoHT3JnMk1TUBAB"
														}]
													}
												},
												{
													"collection_hashed_rwset": [],
													"namespace": "mycc",
													"rwset": {
														"metadata_writes": [],
														"range_queries_info": [],
														"reads": [],
														"writes": [{
																"is_delete": false,
																"key": "a",
																"value": "MTAw"
															},
															{
																"is_delete": false,
																"key": "b",
																"value": "MjAw"
															}
														]
													}
												}
											]
										},
										"token_expectation": null
									},
									"proposal_hash": "QFsKOSAIcsdRQ/3UYkYrUuK36Apj4iulCKW/LKmtAAs="
								}
							},
							"chaincode_proposal_payload": {
								"TransientMap": {},
								"input": {
									"chaincode_spec": {
										"chaincode_id": {
											"name": "lscc",
											"path": "",
											"version": ""
										},
										"input": {
											"args": [
												"ZGVwbG95",
												"bXljaGFubmVs",
												"CicIARILEgRteWNjGgMxLjAaFgoEaW5pdAoBYQoDMTAwCgFiCgMyMDA=",
												"EgwSCggCEgIIABICCAEaDRILCgdPcmcxTVNQEAMaDRILCgdPcmcyTVNQEAM=",
												"ZXNjYw==",
												"dnNjYw=="
											],
											"decorations": {}
										},
										"timeout": 0,
										"type": "GOLANG"
									}
								}
							}
						}
					}]
				},
				"header": {
					"channel_header": {
						"channel_id": "mychannel",
						"epoch": "0",
						"extension": "EgYSBGxzY2M=",
						"timestamp": "2019-08-01T02:19:04.887742126Z",
						"tls_cert_hash": null,
						"tx_id": "91c8e4c4e6c91db19eb8e40f95e2b29cea3d916b2a3249459b9fa83b44fc445a",
						"type": 3,
						"version": 0
					},
					"signature_header": {
						"creator": {
							"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
							"mspid": "Org2MSP"
						},
						"nonce": "CLJ2euIe3YSE7LhNiTuXdBCS2DnvabH2"
					}
				}
			},
			"signature": "MEUCIQD0jJ2zDEbsKIi8ekG3E5xF//EddpMJdKL5nF0anvHp7QIgTNsEJk3N344hq4fklJn/c0fVojzeos4t4w17r7VOJSg="
		}]
	},
	"header": {
		"data_hash": "w8fXJmELmqvXJAWXPge6oCH0SxwoR4nube3o//fYz4A=",
		"number": "3",
		"previous_hash": "qpUWyIdR36SuQa/xqGEnwm1wjpaQxIeU8aaA8RFeN/8="
	},
	"metadata": {
		"metadata": [
			"CgQKAggCEv0GCrIGCpUGCgpPcmRlcmVyTVNQEoYGLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNEVENDQWJPZ0F3SUJBZ0lSQU0rUFQ2YTJsYm1EY0NpNEVhTEFSeFl3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRmd4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJ3d0dnWURWUVFERXhOdmNtUmxjbVZ5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJCktvWkl6ajBEQVFjRFFnQUVZVGcwdXZJMVZ0dEsrb2o2MG9LRjRtWlc4YlFXN0FIRFpZcFZueEdoTE5Kems2cmwKTU1uS0RiRmxibElETE9qK0tiakVwOW9WdEN6OVBsbk4xTmhHSEtOTk1Fc3dEZ1lEVlIwUEFRSC9CQVFEQWdlQQpNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqQkNRd0lvQWdRSWtEMTlLWDFQc3VWUi9BQmVuZFM2ejY5cGxDCmNVNmc0aXUrdHFRL1hzQXdDZ1lJS29aSXpqMEVBd0lEU0FBd1JRSWhBTnd0cDQzMUdkYkdqb3pXRU1DQWdwNWIKeFdnMHNRMVlGbG9TYzF1MFFRU3FBaUF1TVNkc1AvMXZoclhVcGtoT1Voa3NwRjYrYVl1V2ozazZaVE84RWV3agpqdz09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0KEhjerftAXzK8sFOlQ17D0d7A0oP73xf29PkSRjBEAiAp7vqkuMOhC4XzOjwov/HlydZHpMgKuVfeBITm8T752AIgDl9dQHLeaLXEmjFXgv+38H1tFgv/ohHNxdraFexmlrg=",
			"CgIIAg==",
			"AA==",
			""
		]
	}
}
```

#### 调用chaincode

`ns_rwset`包含2个`collection_hashed_rwset`：
- 第1个：说明了当前操作的是lscc，从区块3里把mycc读取出来。
- 第2个：说明操作的是mycc，先把a和b读取出来，然后又把a和b的结果写回mycc。

```json
{
	"data": {
		"data": [{
			"payload": {
				"data": {
					"actions": [{
						"header": {
							"creator": {
								"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
								"mspid": "Org2MSP"
							},
							"nonce": "6Z4RNNIV085Nv/pOYUc5W3EaWcBueAAs"
						},
						"payload": {
							"action": {
								"endorsements": [{
										"endorser": "CgdPcmcxTVNQEqYGLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNKekNDQWM2Z0F3SUJBZ0lRVTlaQzNZWEVySzEybHlSRmx2VW1DREFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTVM1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NUzVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUdveEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVEwd0N3WURWUVFMRXdSd1pXVnlNUjh3SFFZRFZRUURFeFp3WldWeU1DNXZjbWN4CkxtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVGdnVqVG5lMXYyRk4KVENxOTI4WlZrSlhheXRNbVlZcnJ2dndoMEV4b1VVZU1yRjRueU9hZjBRcUo4NjZKeTNibFNQL0xDZFJqOElzdwprdzZmNFBDdEE2Tk5NRXN3RGdZRFZSMFBBUUgvQkFRREFnZUFNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqCkJDUXdJb0FnVkJwVFZxMVBIblR6b3lmdGh1OTN0a2tBNytWN1ZOeUgvaU5nOW8vRklCQXdDZ1lJS29aSXpqMEUKQXdJRFJ3QXdSQUlnSCtpTHF0THQ4WGYwSzNSVHNZUVJLNFIyY05hMXNSV3BVd05QYkxEdzFZd0NJRTg4c2kyTgprZkMvTzB6SkhDandhdFR1aDFVbEt4eFc4OU16aWx3aXJjWnEKLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
										"signature": "MEQCIEnnXFAiBoxqlqgTRs9aBW5PWv+uyjHEEi1XGWXbX0aaAiBEteVfQu7352r5zokdeKdG5+K5LF+IiAbR+QOomOjF1Q=="
									},
									{
										"endorser": "CgdPcmcyTVNQEqYGLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNKekNDQWM2Z0F3SUJBZ0lRVHA5QTREM25oa2NJaVdXRk4xRUZQakFLQmdncWhrak9QUVFEQWpCek1Rc3cKQ1FZRFZRUUdFd0pWVXpFVE1CRUdBMVVFQ0JNS1EyRnNhV1p2Y201cFlURVdNQlFHQTFVRUJ4TU5VMkZ1SUVaeQpZVzVqYVhOamJ6RVpNQmNHQTFVRUNoTVFiM0puTWk1bGVHRnRjR3hsTG1OdmJURWNNQm9HQTFVRUF4TVRZMkV1CmIzSm5NaTVsZUdGdGNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmEKTUdveEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVApZVzRnUm5KaGJtTnBjMk52TVEwd0N3WURWUVFMRXdSd1pXVnlNUjh3SFFZRFZRUURFeFp3WldWeU1DNXZjbWN5CkxtVjRZVzF3YkdVdVkyOXRNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVSRjBFV0NuQW5oMm8KcnFFazhmRTlLdEFCdmJIc1FYTHhMRnZZdlZYVlFPS1crVDBpVk44eWdQbTZlM0kxcG5FTS9hK3Vha2dtYWNmOApzVnVZVERMSythTk5NRXN3RGdZRFZSMFBBUUgvQkFRREFnZUFNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqCkJDUXdJb0FnbVFGMFluM29zOXBQSFdDTWtrdThVdTNiSzRyZjVBSWVRNjBRWDI0eHhyOHdDZ1lJS29aSXpqMEUKQXdJRFJ3QXdSQUlnVTMwdllnVHpCYS84ZGFaZlpBYThzLzN3RFdZdlRpL1BEY3RuWFJBT043QUNJQmNvQzlXSgpYK28rdHFUUDZybS8vdWxpUU02Rk53cUtBSDlYQWxOcVdhbWsKLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
										"signature": "MEUCIQCKz1zIddnNjjoGnzSTuxvVy19TvQSlONS4C9Y3iaJhaAIgY+Zpl003I0X/FsH8+ekifXvugeHCPeZ3UhkO90MWg3U="
									}
								],
								"proposal_response_payload": {
									"extension": {
										"chaincode_id": {
											"name": "mycc",
											"path": "",
											"version": "1.0"
										},
										"events": null,
										"response": {
											"message": "",
											"payload": null,
											"status": 200
										},
										"results": {
											"data_model": "KV",
											"ns_rwset": [{
													"collection_hashed_rwset": [],
													"namespace": "lscc",
													"rwset": {
														"metadata_writes": [],
														"range_queries_info": [],
														"reads": [{
															"key": "mycc",
															"version": {
																"block_num": "3",
																"tx_num": "0"
															}
														}],
														"writes": []
													}
												},
												{
													"collection_hashed_rwset": [],
													"namespace": "mycc",
													"rwset": {
														"metadata_writes": [],
														"range_queries_info": [],
														"reads": [{
																"key": "a",
																"version": {
																	"block_num": "3",
																	"tx_num": "0"
																}
															},
															{
																"key": "b",
																"version": {
																	"block_num": "3",
																	"tx_num": "0"
																}
															}
														],
														"writes": [{
																"is_delete": false,
																"key": "a",
																"value": "OTA="
															},
															{
																"is_delete": false,
																"key": "b",
																"value": "MjEw"
															}
														]
													}
												}
											]
										},
										"token_expectation": null
									},
									"proposal_hash": "okKS/G4+W9VT9+t6VXJnAClnPvOhtUkiCdqjPmzkqjI="
								}
							},
							"chaincode_proposal_payload": {
								"TransientMap": {},
								"input": {
									"chaincode_spec": {
										"chaincode_id": {
											"name": "mycc",
											"path": "",
											"version": ""
										},
										"input": {
											"args": [
												"aW52b2tl",
												"YQ==",
												"Yg==",
												"MTA="
											],
											"decorations": {}
										},
										"timeout": 0,
										"type": "GOLANG"
									}
								}
							}
						}
					}]
				},
				"header": {
					"channel_header": {
						"channel_id": "mychannel",
						"epoch": "0",
						"extension": "EgYSBG15Y2M=",
						"timestamp": "2019-08-01T02:19:38.504172871Z",
						"tls_cert_hash": null,
						"tx_id": "2377b308f2ea91e58d1b21d71b09370dc3c39bab3b92d2c0bc40801843150d6b",
						"type": 3,
						"version": 0
					},
					"signature_header": {
						"creator": {
							"id_bytes": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNLekNDQWRHZ0F3SUJBZ0lSQUo5YnI3UHJmQWg5cHVVcDFMZkJ3V0V3Q2dZSUtvWkl6ajBFQXdJd2N6RUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhHVEFYQmdOVkJBb1RFRzl5WnpJdVpYaGhiWEJzWlM1amIyMHhIREFhQmdOVkJBTVRFMk5oCkxtOXlaekl1WlhoaGJYQnNaUzVqYjIwd0hoY05NVGt3T0RBeE1ESXhOREF3V2hjTk1qa3dOekk1TURJeE5EQXcKV2pCc01Rc3dDUVlEVlFRR0V3SlZVekVUTUJFR0ExVUVDQk1LUTJGc2FXWnZjbTVwWVRFV01CUUdBMVVFQnhNTgpVMkZ1SUVaeVlXNWphWE5qYnpFUE1BMEdBMVVFQ3hNR1kyeHBaVzUwTVI4d0hRWURWUVFEREJaQlpHMXBia0J2CmNtY3lMbVY0WVcxd2JHVXVZMjl0TUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFZndwdkRmOHoKWVdVaWxwclcxQ2hsc3hBaDhVcjBLQXpUYm9oc0oyQjFNWk40ZkVUakhKTHRnWjZDT0ZRaVFoNy9BK1NyNVhYdApDRnpvNUZWSlNSNmc2YU5OTUVzd0RnWURWUjBQQVFIL0JBUURBZ2VBTUF3R0ExVWRFd0VCL3dRQ01BQXdLd1lEClZSMGpCQ1F3SW9BZ21RRjBZbjNvczlwUEhXQ01ra3U4VXUzYks0cmY1QUllUTYwUVgyNHh4cjh3Q2dZSUtvWkkKemowRUF3SURTQUF3UlFJaEFPVUZRWUMvZE1ZMGZ0U2JNYVFLL213Uy83a0JyRWZicXFNaHBwWjlqWG1uQWlCeQpjczdFalFuZHJ2RHRMZnVPUEY4QnJyVGZPdWZDTTVNN09YSDl4S2ZQdVE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==",
							"mspid": "Org2MSP"
						},
						"nonce": "6Z4RNNIV085Nv/pOYUc5W3EaWcBueAAs"
					}
				}
			},
			"signature": "MEUCIQD5A7tvxqe4q/l+D1KOpDDaTZ5DdpsLs+xTA1CqsR+nBAIgSo+cFAzBBDfRJK8bcV6khmqWuhATKHm/7uiJiDkDjKI="
		}]
	},
	"header": {
		"data_hash": "9Q8SRPt+L2bvRGXAteiCXOkiutLu1nZBiCCaiwAlFdk=",
		"number": "4",
		"previous_hash": "vE7W/Qond3H6koHXpoWm2dfcZfZnmMYwF5lfNj6hDlY="
	},
	"metadata": {
		"metadata": [
			"CgQKAggCEv0GCrIGCpUGCgpPcmRlcmVyTVNQEoYGLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNEVENDQWJPZ0F3SUJBZ0lSQU0rUFQ2YTJsYm1EY0NpNEVhTEFSeFl3Q2dZSUtvWkl6ajBFQXdJd2FURUwKTUFrR0ExVUVCaE1DVlZNeEV6QVJCZ05WQkFnVENrTmhiR2xtYjNKdWFXRXhGakFVQmdOVkJBY1REVk5oYmlCRwpjbUZ1WTJselkyOHhGREFTQmdOVkJBb1RDMlY0WVcxd2JHVXVZMjl0TVJjd0ZRWURWUVFERXc1allTNWxlR0Z0CmNHeGxMbU52YlRBZUZ3MHhPVEE0TURFd01qRTBNREJhRncweU9UQTNNamt3TWpFME1EQmFNRmd4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlFd3BEWVd4cFptOXlibWxoTVJZd0ZBWURWUVFIRXcxVFlXNGdSbkpoYm1OcApjMk52TVJ3d0dnWURWUVFERXhOdmNtUmxjbVZ5TG1WNFlXMXdiR1V1WTI5dE1Ga3dFd1lIS29aSXpqMENBUVlJCktvWkl6ajBEQVFjRFFnQUVZVGcwdXZJMVZ0dEsrb2o2MG9LRjRtWlc4YlFXN0FIRFpZcFZueEdoTE5Kems2cmwKTU1uS0RiRmxibElETE9qK0tiakVwOW9WdEN6OVBsbk4xTmhHSEtOTk1Fc3dEZ1lEVlIwUEFRSC9CQVFEQWdlQQpNQXdHQTFVZEV3RUIvd1FDTUFBd0t3WURWUjBqQkNRd0lvQWdRSWtEMTlLWDFQc3VWUi9BQmVuZFM2ejY5cGxDCmNVNmc0aXUrdHFRL1hzQXdDZ1lJS29aSXpqMEVBd0lEU0FBd1JRSWhBTnd0cDQzMUdkYkdqb3pXRU1DQWdwNWIKeFdnMHNRMVlGbG9TYzF1MFFRU3FBaUF1TVNkc1AvMXZoclhVcGtoT1Voa3NwRjYrYVl1V2ozazZaVE84RWV3agpqdz09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0KEhhh6UhNerUcr/HbaA9SbvQ3xInOkYF9oKoSRjBEAiAwGjDnt+7TPrPz7fhm/63rUCFlJYzgRXdPautelXme3gIgUXb8ynZgf2rfIA8bL+y992HIgjtDCBppydWmPmXD9g4=",
			"CgIIAg==",
			"AA==",
			""
		]
	}
}
```