---
title: Go语言日期和时间戳转换
date: 2020-07-29 19:48:59
tags: ['Go']
---


字符串格式日期、time.Time类型、整形时间戳三者之间的转换如下图：

![](http://img.lessisbetter.site/2020-07-go-time-date-transform.png)

有2点要注意：
1. 字符串日期和时间戳之间不能直接转换，需要通过time.Time完成。
2. 涉及字符串日期的时候，字符串日期格式一定要以Go诞生的时间为基准，而不是随意的时间，否则会导致时间转换不正确。所以，以下Demo中的日期格式是通用的。
3. 字符串日期格式要与真实的日期格式完全匹配，否则会解析时间不正确。比如设置的格式为`2006-01-02`，实际日期格式为`2006-1-2`时会解析错误。



```go
package main

import (
	"fmt"
	"time"
)

func Date2Time() {
	fmt.Println(">> Date2Time")
	defer fmt.Println("<< Date2Time")

	// 一定要以Go诞生的时间为基准
	// 2006年1月2号，MST时区，下午3:04分为基准
	const dateFormat = "Jan 2, 2006 at 3:04pm (MST)"
	t, _ := time.Parse(dateFormat, "May 20, 2020 at 0:00am (UTC)")
	fmt.Println(t)

	const shortForm = "2006-Jan-02"
	t, _ = time.Parse(shortForm, "2020-May-20")
	fmt.Println(t)

	t, _ = time.Parse("01/02/2006", "05/20/2020")
	fmt.Println(t)
}

func Time2Date() {
	fmt.Println(">> Time2Date")
	defer fmt.Println("<< Time2Date")

	tm := time.Now()
	fmt.Println(tm.Format("2006-01-02 03:04:05 PM"))
	fmt.Println(tm.Format("2006-1-2 03:04:05 PM"))
	fmt.Println(tm.Format("2006-Jan-02 03:04:05 PM"))
	fmt.Println(tm.Format("02/01/2006 03:04:05 PM"))
}

func Timestamp2Time() {
	fmt.Println(">> Timestamp2Time")
	defer fmt.Println("<< Timestamp2Time")

	ts := int64(1595900001)
	tm := time.Unix(ts, 0)
	fmt.Println(tm)
}

func Time2Timestamp() {
	fmt.Println(">> Time2Timestamp")
	defer fmt.Println("<< Time2Timestamp")

	tm := time.Now()
	ts := tm.Unix()
	fmt.Println(ts)
}

func main() {
	Date2Time()
	Time2Date()
	Timestamp2Time()
	Time2Timestamp()
}
```

运行结果：

```
>> Date2Time
2020-05-20 00:00:00 +0000 UTC
2020-05-20 00:00:00 +0000 UTC
2020-05-20 00:00:00 +0000 UTC
<< Date2Time
>> Time2Date
2020-07-28 09:35:46 AM
2020-7-28 09:35:46 AM
2020-Jul-28 09:35:46 AM
28/07/2020 09:35:46 AM
<< Time2Date
>> Timestamp2Time
2020-07-28 09:33:21 +0800 CST
<< Timestamp2Time
>> Time2Timestamp
1595900146
<< Time2Timestamp
```