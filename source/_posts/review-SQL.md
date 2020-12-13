title: SQL回顾总结
date: 2016-03-13 14:47:20
tags: ['SQL']
---


> 本博文中的所有内容，可以在MySQL 5.6.21中运行。


MySQL 5.1在线参考手册：[时光机](http://doc.mysql.cn/mysql5/refman-5.1-zh.html-chapter/)





# 查询

## 限制行号和偏倚量。

从第OFFSET+1开始，共获取LIMIT个结果。可以用来求某列，第OFFSET+1大或小的行。

```SQL
SELECT *
FROM products
LIMIT 3
OFFSET 2;

SELECT *
FROM products
LIMIT 2,3;
```


<!--more-->


## 注释

1) 嵌入在行内
2) 整行都是注释
3) 块注释

```SQL
1) --
2) #
3) /*  */
```


# 检索排序

> 关键字：ORDER BY，DESC。

## ORDER BY子句的位置（必须最后一句）
  在指定一条ORDER BY子句时，应该保证它是SELECT语句中最后一条子句。如果它不是最后的子句，将会出现错误消息。
## 通过非选择列进行排序（排序的那列可以不显示）
  通常，ORDER BY子句中使用的列将是为显示而选择的列。但是，实际上并不一定要这样，用非检索的列排序数据是完全合法的。

## 多列排序

```SQL
SELECT prod_id, prod_price, prod_name
FROM products
ORDER BY prod_price, prod_name;
```

效果
![](https://lessisbetter.site/images/review-SQL-3-1.png)


为什么列顺序不是：

```SQL
SELECT prod_id, prod_name, prod_price
FROM products
ORDER BY prod_price, prod_name;
```

效果
![](https://lessisbetter.site/images/review-SQL-3-2.png)



因为`prod_name`放中间不好看。


## 按列位置排序

**禁止使用**

```SQL
SELECT prod_id, prod_price, prod_name
FROM products
ORDER BY 2, 3;
```

虽然简写了列名字，但容易出错，并且相当不直观，隐藏了潜在BUG。在修改SQL的语句的更容易错误，可能依据的排序列根本不在查询中。

## 逆序

在排序依据列的名字加DESC。

```SQL
SELECT prod_id, prod_price, prod_name
FROM products
ORDER BY prod_price DESC, prod_name DESC;
```

效果：根据价格从高到低排序，同价，则根据名字，从后向前排序。



# 检索过滤

> 关键词：WHERE。

## 操作符

![](https://lessisbetter.site/images/review-SQL-operators.png)


## 范围检查

``` SQL
SELECT prod_id, prod_price, prod_name
FROM products
WHERE prod_price BETWEEN 8 AND 10;
```

## 空值检查

IS NULL。

**这不同于值为0，或字符串为空。**


查找没有邮箱的客户。

```SQL
SELECT DISTINCT cust_name
FROM customers
WHERE cust_email IS NULL;
```

找到有邮箱的用户。

```SQL
SELECT DISTINCT cust_name
FROM customers
WHERE cust_email IS NOT NULL;
```


# 高级过滤

> 关键词：NOT，IN，AND，OR。

## AND, OR

WHERE子句可以包含任意数目的AND和OR操作符。允许两者结合以进行复杂、高级的过滤。SQL（像多数语言一样）**在处理OR操作符前，优先处理AND操作符**。当SQL看到上述WHERE子句时，它理解为：由供应商BRS01制造的价格为10美元以上的所有产品，以及由供应商DLL01制造的所有产品，而不管其价格如何。换句话说，由于AND在求值过程中优先级更高，操作符被错误地组合了。

```SQL
SELECT prod_name, prod_price
FROM Products
WHERE vend_id = 'DLL01' OR vend_id = ‘BRS01’
AND prod_price >= 10
```
理想是这样子的：

```SQL
SELECT prod_name, prod_price
FROM Products
WHERE (vend_id = 'DLL01' OR vend_id = ‘BRS01’)
AND prod_price >= 10;
```

## IN

满足所在集合的记录。
1. **完成的是OR的工作，IN是OR的简洁版本**。
2. 在有很多合法选项时，IN操作符的语法**更清楚，更直观**。
3. 在与其他AND和OR操作符组合使用IN时，求值顺序更**容易管理**。
4. IN操作符一般比一组OR操作符执行得**更快**。
5. IN的最大优点是可以**包含其他SELECT语句，能够更动态地建立WHERE子句**。

```SQL
SELECT vend_id, prod_id, prod_price, prod_name
FROM products
WHERE vend_id
IN ('DLL01', 'BRS01');
```


## NOT

WHERE子句中的NOT操作符有且只有一个功能，那就是否定**其后**所跟的任何条件。
在更复杂的子句中，NOT是非常有用的。例如，在与IN操作符联合使用时，NOT可以非常简单地找出与条件列表不匹配的行。


# 通配符过滤

> 关键词：%，_。

引用自《SQL必知必会》。

> 通配符（wildcard）
用来匹配值的一部分的特殊字符。


> 搜索模式（search pattern）
由字面值、通配符或两者组合构成的搜索条件。

通配符本身实际上是SQL的WHERE子句中有特殊含义的字符，SQL支持几种通配符。为在搜索子句中使用通配符，必须使用LIKE操作符。LIKE指示DBMS，后跟的搜索模式利用通配符匹配而不是简单的相等匹配进行比较。


> 谓词（predicate）
操作符何时不是操作符？答案是，它作为谓词时。从技术上说，LIKE是谓词而不是操作符。虽然最终的结果是相同的，但应该对此术语有所了解，以免在SQL文献或手册中遇到此术语时不知所云。



## 谓词：`LIKE`

## %：任何字符出现任意次数

1. 使用相当的灵活，可以把`%`放在字符串的任何一个位置，也可以使用多个`%`。
2. 不匹配`NULL`。

搜索商品名称以Fish开头的商品。

```SQL
SELECT prod_id, prod_name 
FROM Products 
WHERE prod_name LIKE 'Fish%';
```

以bag结尾呢？

```SQL
WHERE prod_name LIKE '%bag';
```


```SQL
'F%y' ： 以F开头，以y结尾。
'F%y%'：以F开头，中间有y。
```

实用案例：邮箱匹配

```SQL
SELECT cust_name, cust_email
FROM customers
WHERE cust_email LIKE '%@fun4all.com';
```

## _：只匹配单个字符。

1. 有且仅有一个字符。
2. 可以是空格。
3. 可以连用。

```SQL
SELECT prod_id, prod_name
FROM Products
WHERE prod_name LIKE '__ inch teddy bear';
```

**MySQL的LIKE只支持`%`和`_`，其他匹配，可以使用谓词`REGEXP`。**

## 技巧

1. 不要过度使用通配符。如果其他操作符能达到相同的目的，应该使用其他操作符。
2. 在确实需要使用通配符时，也尽量不要把它们用在搜索模式的开始处。把通配符置于开始处，搜索起来是最慢的。
3. 仔细注意通配符的位置。如果放错地方，可能不会返回想要的数据。


# 计算字段

> 字段（field）
基本上与列（column）的意思相同，经常互换使用，不过数据库列一般称为列，而术语字段通常与计算字段一起使用。

## 拼接

MySQL需要使用拼接函数。

```SQL
concat(): 参数为列名，和字符串
concat_ws(): 第一个参数为连接符，剩余参数为列明，各列之间使用连接符连接
```

例1

```SQL
SELECT concat(vend_name, '(', vend_country, ')')
	AS vend_title
FROM vendors;
```

效果：

```SQL
'Bear Emporium(USA)'
'Bears R Us(USA)'
'Doll House Inc.(USA)'
'Fun and Games(England)'
'Furball Inc.(USA)'
'Jouets et ours(France)'
```

例2

```SQL
SELECT concat_ws('-', vend_name, vend_country)
FROM vendors;
```

效果

```SQL
'Bear Emporium-USA'
'Bears R Us-USA'
'Doll House Inc.-USA'
'Fun and Games-England'
'Furball Inc.-USA'
'Jouets et ours-France'
```

## 别名/导出列

AS是SQL的一条最佳实践。

```SQL
SELECT concat_ws('-', vend_name, vend_country)
	AS vend_title
FROM vendors;
```

## 算术计算

支持列或字段之间的四则运算。

```SQL
SELECT prod_id,
	   quantity,
       item_price,
       quantity*item_price AS expanded_price
FROM orderitems
WHERE order_num = 20008;
```

> SELECT语句校验
SELECT语句为测试、检验函数和计算提供了很好的方法。虽然SELECT通常用于从表中检索数据，但是省略了FROM子句后就是简单地访问和处理表达式，例如SELECT 3 * 2;将返回6，SELECT Trim(' abc ');将返回abc，SELECT Now();使用Now()函数返回当前日期和时间。现在你明白了，可以根据需要使用SELECT语句进行检验。



# 函数

> 不同的DBMS支持的函数不同。

常用函数可以分为以下几类：
- 数值函数
- 文本函数
- 日期时间函数
- DBMS系统函数

常用函数参考：[时光机](http://www.cnblogs.com/kissdodog/p/4168721.html)

## 文本函数

处理字符串的函数。

例1：

```SQL
SELECT vend_name,
  upper(vend_name) AS vend_name_upcase
FROM vendors
ORDER BY vend_name;
```

## 日期时间函数

日期和时间采用相应的数据类型存储在表中，**每种DBMS都有自己的特殊形式**。日期和时间值以特殊的格式存储，以便能快速和有效地排序或过滤，并且节省物理存储空间。

应用程序一般不使用日期和时间的存储格式，因此日期和时间函数总是用来读取、统计和处理这些值。由于这个原因，日期和时间函数在SQL中具有重要的作用。遗憾的是，它们很不一致，**可移植性最差**。


**时间函数相当的丰富，包含了各种转换，日期加减，抽取。**

```SQL
SELECT curdate();
SELECT curtime();
SELECT now();
SELECT month("2016-3-13 1:1:1"); -- 获取输入date的月份
```

## 数值处理

**在各大DBMS中，最统一、最一致的函数。**

主要包括代数、三角、几何运算。




# 聚集函数


聚集函数（aggregate function）对某些行运行的函数，计算并返回一个值。

![](https://lessisbetter.site/images/9-1.png)

## AVG

- AVG()只能用来确定特定数值列的平均值，而且列名必须作为函数参数给出。为了获得多个列的平均值，必须使用多个AVG()函数。
- 忽略NULL行。


## COUNT

- 返回指定列所有非NULL行数。

## MAX、MIN

- 返回指定列所有非NULL行的最大/小值。

## SUM

- 返回指定列的总和。
- 忽略NULL行。


## 函数参数

以上4个函数：可以是数值列运算后的得到的新字段，如：

```SQL
SELECT SUM(item_price*quantity) AS total_price
FROM OrderItems
WHERE order_num = 20005;
```

## 结合DISTINCT

```SQL
SELECT AVG(DISTINCT prod_price) AS avg_price
FROM Products
WHERE vend_id = 'DLL01';
```

## 奇葩的存在

唯有COUNT可以使用*。

```SQL
SELECT COUNT(*) AS num_items
FROM Products
WHERE vend_id = 'DLL01';
```


# 分组数据

> 关键词：GROUP BY & HAVING。

## GROUP BY

- GROUP BY子句可以包含任意数目的列，因而可以对分组进行**嵌套**，更细致地进行数据分组。
- 如果在GROUP  BY子句中嵌套了分组，数据将在**最后指定的分组**上进行汇总。换句话说，在建立分组时，指定的所有列都一起计算（所以不能从个别的列取回数据）。
- GROUP BY子句中列出的每一列都必须是检索列或有效的表达式（但不能是聚集函数）。如果在SELECT中使用表达式，则必须在GROUP  BY子句中指定相同的表达式。不能使用别名。
- 大多数SQL实现不允许GROUP BY列带有长度可变的数据类型（如文本或备注型字段）。
- 除聚集计算语句外，SELECT语句中的每一列都必须在GROUP BY子句中给出。【并没有呀，下例依然可以运行，**但是结果并不是想要的**】

```SQL
SELECT vend_id, prod_id, COUNT(*) as num_prods
FROM products
GROUP BY vend_id;
```

这样只会去那个`vend_id`的第一个`prod_id`。

所以还是需要遵循规则：

```SQL
SELECT vend_id, prod_id, COUNT(*) as num_prods
FROM products
GROUP BY vend_id, prod_id;
```

- 如果分组列中包含具有NULL值的行，则NULL将作为一个分组返回。如果列中有多行NULL值，它们将分为一组。
- GROUP BY子句必须出现在WHERE子句之后，ORDER BY子句之前。

## 过滤分组：HAVING

- WHERE是针对行的，不是针对分组。
- HAVING支持所有WHERE操作符。
- 唯一差别：WHERE过滤行，而HAVING过滤分组。


- MySQL允许HAVING中使用列/字段的别名。

```SQL
-- 从订单列表中，选择哪些下过两次订单的用户。
-- 首先，你需要的是每个用户的信息，所以需要使用group by分组，
-- 然后，你需要计算每个用户下了多少订单，所以使用count
-- 最后，过滤，因为是对group的结果进行过滤，所以使用having，而不是where。
SELECT cust_id, COUNT(*) AS orders
FROM orders
GROUP BY cust_id
HAVING COUNT(*) >= 2;

-- MySQL允许HAVING中使用列/字段的别名
SELECT cust_id, COUNT(*) AS orders
FROM orders
GROUP BY cust_id
HAVING orders >= 2;
```

**腾讯才曾经考过这样一个题目**：有张表，存放的是不同用户对不同品牌汽车的评分，每个用户对每个汽车有个评分，要求查询出给2辆及以上做出评分的用户信息。


- WHERE在数据分组前进行过滤，HAVING在数据分组后进行过滤。这是一个重要的区别，WHERE排除的行不包括在分组中。这可能会改变计算值，从而影响HAVING子句中基于这些值过滤掉的分组。
- 同时是使用WHERE, HAVING。

```SQL
-- 选择价格大于4并且至少有2个商品的供应商。
SELECT vend_id, COUNT(*) as num_prods
FROM products
WHERE prod_price >= 4
GROUP BY vend_id
HAVING num_prods >= 2;
```

- GROUP不保证输出数据有序。要有序，需要结合ORDER BY。

```SQL
-- 选择订购买商品数量大于3的订单，并且按商品数量和订单号排序。
SELECT order_num, COUNT(*) as items
FROM orderitems
GROUP BY order_num
HAVING items >= 3
ORDER BY items, order_num;
```

![](https://lessisbetter.site/images/10-2.png)


# 子查询

> MySQL从4.1版本才支持子查询。

- 子查询总是从内向外处理。
- 包含子查询的SELECT语句难以阅读和调试，它们在较为复杂时更是如此。如上所示，把子查询分解为多行并进行适当的缩进，能极大地简化子查询的使用。

```SQL
-- 查找购买了RGAN01的用户的信息。
SELECT cust_name, cust_contact
FROM customers
WHERE cust_id IN (SELECT cust_id
 FROM Orders
 WHERE order_num IN (SELECT order_num
 FROM orderitems
 WHERE prod_id = 'RGAN01'));
```

- 警告：只能是单列
    作为子查询的SELECT语句只能查询单个列。企图检索多个列将返回错误。
- 警告：子查询和性能
    这里给出的代码有效，并且获得了所需的结果。但是，使用子查询并不总是执行这类数据检索的最有效方法。更多的论述，请参阅第12课，其中将再次给出这个例子。

## 作为计算字段使用子查询

```SQL
SELECT cust_name, 
       cust_state,
       (SELECT COUNT(*) 
        FROM Orders 
        WHERE Orders.cust_id = Customers.cust_id) AS orders
FROM Customers 
ORDER BY cust_name;
```



# 联结表

> 关键词：JOIN。

> 联结： 如果数据存储在多个表中，怎样用一条SELECT语句就检索出数据呢？

## 联结

- 关系通过主键而建立。
- SQL语句中可以省略JOIN关键词。

```SQL
SELECT vend_name, prod_name, prod_price
FROM vendors, products
WHERE vendors.vend_id = products.vend_id;
```

等价于：

```
SELECT vend_name, prod_name, prod_price
FROM vendors JOIN products
WHERE vendors.vend_id = products.vend_id;
```

效果：

![](https://lessisbetter.site/images/12-1.png)

- 如果没有WHERE，将会产生笛卡尔积效果：

```SQL
SELECT vend_name, prod_name, prod_price
FROM vendors, products
ORDER BY vend_name, prod_name;
```

效果：

![](https://lessisbetter.site/images/12-2.png)

所以我们需要WHERE进行过滤。

## 内连接

目前使用的联结又称为等值联结，也被称为内联结，换另外一种方式：

使用关键词`INNER JOIN`和`ON`，省略掉了`WHERE`效果相同。

```SQL
SELECT vend_name, prod_name, prod_price
FROM vendors INNER JOIN products
ON vendors.vend_id = products.vend_id
ORDER BY vend_name, prod_name;
```

## 联结多个表

SQL不限制一条SELECT语句中可以联结的表的数目，但联结越多，性能下降越大。

```SQL
-- 20007这个订单下的所有商品，价格及数量，以及供货商。
SELECT prod_name, vend_name, prod_price, quantity
FROM vendors, products, orderitems
WHERE vendors.vend_id = products.vend_id
  AND orderitems.prod_id = products.prod_id
  AND orderitems.order_num = 20007
ORDER BY vend_name, prod_name;
```


以简洁的JOIN完成上一节SELECT的子查询：

```SQL
SELECT cust_name, cust_contact
FROM customers, orders, orderitems
WHERE customers.cust_id = orders.cust_id
  AND orderitems.order_num = orders.order_num
  AND orderitems.prod_id = 'RGAN01'
```




# 高级联结

> 关键词：别名、外联结、聚集函数。


## 别名

- 缩短SQL语句；
- 允许在一条SELECT语句中多次使用相同的表。
- 与列别名不一样，表别名不返回到客户端。
- MySQL里面支持省略`AS`，就像Oracle的一样，Oracle是不支持使用`AS`。

```SQL
SELECT cust_name, cust_contact
FROM customers AS C, orders AS O, orderitems AS OI
WHERE C.cust_id = O.cust_id
  AND O.order_num = OI.order_num
  AND OI.prod_id = 'RGAN01';
```

WHERE语句中的条件顺序很重要，一般可以是这种思路：我查询的是customer信息，那么第一个条件先写和customer相关的，就会引出另外一张表，再写和这张表相关的，最后一个条件，必然为限定条件。

## 不同类型的联结

四种其他联结：内连接（inner join）、自联结（self-join）、自然联结（natural join）和外联结（outer join）。

### 自联结

条件与所查询的内容在同一个表。

假如要给与Jim Jones同一公司的所有顾客发送一封信件。这个查询要求首先找出Jim Jones工作的公司，然后找出在该公司工作的顾客。

![](https://lessisbetter.site/images/13-1.png)

在这里好像cust_name是公司名，而cust_contact是联系人的名字，而Jim Jones则是其中的一个联系人。

```SQL
SELECT c1.cust_id, c1.cust_name, c1.cust_contact
FROM customers AS c1, Customers AS c2
WHERE c1.cust_name = c2.cust_name
  AND c2.cust_contact = 'Jim Jones';
```

### 自然联结

自然联结排除多次出现，使每一列只返回一次。事实上，我们迄今为止建立的每个内联结都是自然联结，很可能永远都不会用到不是自然联结的内联结。


### 外联结

不仅包含，有关联行的那些行，还包含没有关联行的那些行。

- LEFT：包含左边表的所有行。
- RIGHT：包含右边表的所有行。
- 是需要调整FROM语句中的表的顺序，就可以互换LEFT和RIGHT。
- MySQL不支持`FULL OUTER JOIN`。
- 条件只能使用`ON`过滤。

```SQL
SELECT customers.cust_id, orders.order_num
FROM orders LEFT OUTER JOIN customers
ON orders.cust_id = customers.cust_id;
```

效果：

![](https://lessisbetter.site/images/13-2.png)


## 聚集函数与联结

联结不过是把不同表中的数据合到一张“虚拟的表”，这张虚拟的表，就是由选择的列构成，我们可以在这些列上，使用聚合函数。

```SQL
-- 查询有订单的每个用户的订单数量
SELECT customers.cust_id, 
	COUNT(orders.order_num) AS num_ord
FROM customers, orders
WHERE customers.cust_id = orders.cust_id
GROUP BY customers.cust_id;
```

```SQL
-- 简化上一个SQL查询
SELECT customers.cust_id AS customer_id,
	COUNT(orders.order_num) AS order_count
FROM customers, orders
WHERE customers.cust_id = orders.cust_id
GROUP BY customer_id;
```

查询每个用户的订单数量，包含哪些没有订单的用户。

```SQL
SELECT customers.cust_id AS customer_id,
  COUNT(orders.order_num) AS order_count
FROM customers LEFT OUTER JOIN orders
ON customers.cust_id = orders.cust_id
GROUP BY customer_id;
```

效果：
![](https://lessisbetter.site/images/13-3.png)


## 联结总结

1. 注意所使用的联结类型。一般我们使用内联结，但使用外联结也有效。
1. 关于确切的联结语法，应该查看具体的文档，看相应的DBMS支持何种语法（大多数DBMS使用这两课中描述的某种语法）。
1. 保证使用正确的联结条件（不管采用哪种语法），否则会返回不正确的数据。
1. 应该总是提供联结条件，否则会得出笛卡儿积。
1. 在一个联结中可以包含多个表，甚至可以对每个联结采用不同的联结类型。虽然这样做是合法的，一般也很有用，但应该在一起测试它们前分别测试每个联结。这会使故障排除更为简单。



# 组合查询

> 关键词：UNION。

执行多个查询（多条SELECT语句），并将结果作为一个查询结果集返回。这些组合查询通常称为并（union）或复合查询（compound query）。


- 每个查询之间，使用一个`UNION`。
- `UNION`会去掉各查询结果重复的项，仅保留一个。
- `UNION ALL`可以保留重复的项。


主要有两种情况需要使用组合查询：
1. 在一个查询中从不同的表返回结构数据；
2. 对一个表执行多个查询，按一个查询返回数据。


## 同WHERE转换

**组合相同表**的两个查询所完成的工作与具有多个WHERE子句条件的一个查询所完成的工作相同，使用`OR`组合过滤条件即可。换句话说，任何具有多个WHERE子句的SELECT语句都可以作为一个组合查询，在下面可以看到这一点。

```SQL
-- 同一表中查询
SELECT cust_name, cust_contact, cust_email
FROM customers
WHERE cust_state in ('IL', 'IN', 'MI')
UNION
SELECT cust_name, cust_contact, cust_email
FROM customers
WHERE cust_name = 'Fun4ALL';

-- 替换为等价的WHERE过滤
SELECT cust_name, cust_contact, cust_email
FROM customers
WHERE cust_state in ('IL', 'IN', 'MI')
   OR cust_name = 'Fun4ALL';
```

## 排序

放在最后一行。

```SQL
SELECT cust_name, cust_contact, cust_email
FROM customers
WHERE cust_state in ('IL', 'IN', 'MI')
UNION
SELECT cust_name, cust_contact, cust_email
FROM customers
WHERE cust_name = 'Fun4ALL'
ORDER BY cust_name, cust_contact;
```

---------------------------

以上全是查询，下面的内容开启，修改数据库内容。


# 插入数据


> 关键词：INSERT、INTO、VALUES。

插入有以下三种功能：

- 插入完整的行；
- 插入行的一部分；
- 插入某些查询的结果。


## 插入完整的一行

```SQL
INSERT INTO customers
VALUES ('1000000006',
        'Toy Land',
        '123 Any Street',
        'New York',
        'NY',
        '11111',
        'USA',
        NULL,
        NULL);
```

不安全，依赖于表中列的次序，更安全的方案是：

```SQL
INSERT INTO Customers(cust_id,
                      cust_name,
                      cust_address,
                      cust_city,
                      cust_state,
                      cust_zip,
                      cust_country,
                      cust_contact,
                      cust_email)
VALUES('1000000006',
       'Toy Land',
       '123 Any Street',
       'New York',
       'NY',
       '11111',
       'USA',
       NULL,
       NULL);
```

## 插入部分行

插入哪些列，就使用那些列的名字。

前提是：省略的那些列，
- 允许NULL，
- 或者提供了默认值，
不然会出错。

```SQL
INSERT INTO Customers(cust_id,
                      cust_name,
                      cust_address,
                      cust_city,
                      cust_state,
                      cust_zip,
                      cust_country)
VALUES('1000000008',
       'Toy Land',
       '123 Any Street',
       'New York',
       'NY',
       '11111',
       'USA');
```

## 插入SELECT结果

```SQL
-- 将数据从custnew取出，插入到customers
INSERT INTO Customers(cust_id,
                      cust_contact,
                      cust_email,
                      cust_name,
                      cust_address,
                      cust_city,
                      cust_state,
                      cust_zip,
                      cust_country)
SELECT cust_id,
       cust_contact,
       cust_email,
       cust_name,
       cust_address,
       cust_city,
       cust_state,
       cust_zip,
       cust_country
FROM CustNew;
```

## 插入多行

使用多个INSERT语句。


## 从一个表复制到另外一个表

- 要创建一个全新的表。
- 如果只复制部分列，修改SELECT语句。

```
CREATE TABLE custcopy AS
SELECT * FROM customers;
```




# 更新和删除数据(表内容)

> 关键词： UPDATE、DELETE、SET。

## UPDATE

两个功能：
- 修改表中特定的行。
- 修改所有的行。



```SQL
-- 更新一个列
UPDATE customers
SET cust_email = 'kim@thetoystore.com'
WHERE cust_id = '1000000005';
```

> 不要省略WHERE子句，不然就更新所有行了。


```SQL
-- 更新多个列，只需要1个SET
UPDATE customers
SET cust_contact = 'Sam Roberts',
    cust_email = 'sam@toyland.com'
WHERE cust_id = '1000000006';
```

## DELETE

两个功能：
- 删除表中特定的行。
- 删除所有的行。


```SQL
DELETE FROM customers
WHERE cust_id = '100000006';
```

- 更快的清空表

它比使用DELETE清空表更快，因为它不记录数据的变化。

```
TRUNCATE custcopy;
```

## UPDATE和DELETE重要原则

1. 除非确实打算更新和删除每一行，否则绝对不要使用不带WHERE子句的UPDATE或DELETE语句。
1. 保证每个表都有主键（如果忘记这个内容，请参阅第12课），尽可能像WHERE子句那样使用它（可以指定各主键、多个值或值的范围）。
1. 在UPDATE或DELETE语句使用WHERE子句前，应该先用SELECT进行测试，保证它过滤的是正确的记录，以防编写的WHERE子句不正确。
1. 使用强制实施引用完整性的数据库（关于这个内容，请参阅第12课），这样DBMS将不允许删除其数据与其他表相关联的行。
1. 有的DBMS允许数据库管理员施加约束，防止执行不带WHERE子句的UPDATE或DELETE语句。如果所采用的DBMS支持这个特性，应该使用它。


# 创建和操纵表

> 关键词：CREATE TABLE。

## 创建表

```SQL
CREATE TABLE copyproducts
(
    prod_id       CHAR(10)          NOT NULL,
    vend_id       CHAR(10)          NOT NULL,
    prod_name     CHAR(254)         NOT NULL,
    prod_price    DECIMAL(8,2)      NOT NULL,
    prod_desc     text              NULL
);
```

表名紧跟CREATE TABLE关键字。实际的表定义（所有列）括在圆括号之中，各列之间用逗号分隔。

在创建新的表时，指定的表名必须不存在，否则会出错。防止意外覆盖已有的表，SQL要求首先手工删除该表（请参阅后面的内容），然后再重建它，而不是简单地用创建表语句覆盖它。

如果该列可以为NULL，那么创建表时，可以省略最后的NULL，如上一个SQL语句的第7行，可以改为
```SQL
CREATE TABLE copyproducts
(
    prod_id       CHAR(10)          NOT NULL,
    vend_id       CHAR(10)          NOT NULL,
    prod_name     CHAR(254)         NOT NULL,
    prod_price    DECIMAL(8,2)      NOT NULL,
    prod_desc     text
);
```

指定默认值

```SQL
CREATE TABLE copyorderitems
(
    order_num      INTEGER          NOT NULL,
    order_item     INTEGER          NOT NULL,
    prod_id        CHAR(10)         NOT NULL,
    quantity       INTEGER          NOT NULL      DEFAULT 1,
    item_price     DECIMAL(8,2)     NOT NULL
);
```

默认值还可以使用函数，比如常用的日期函数，但在MySQL中也有一定限制：MySQL的字段默认值不可以是函数，除 TIMESTAMP字段可以用CURRENT_TIMESTAMP外，其它都使用常数为默认值。


```SQL
DROP TABLE students;
CREATE TABLE students
(
    stu_id          CHAR(10)      NOT NULL,
    stu_name        CHAR(10)      NOT NULL,
    createtime      timestamp     not null    default current_timestamp
);


insert into
students (stu_id,
          stu_name)
values ('12',
        'sj');
       
       
select *
from students;
```


## ALTER TABLE

更新表**定义（原有的结构）**，UPDATE才是更新表里的数据。

对于ALTER TABLE不同的DBMS支持大不相同，MySQL的相关文档：[时光机器](http://doc.mysql.cn/mysql5/refman-5.1-zh.html-chapter/sql-syntax.html#alter-table)。

支持的操作：
- 增加列。
- 删除列。
- 修改列。
- 增加限制。
- 删除主键。
- 删除索引。
- 删除外键。
- 省略。。。


```SQL
ALTER TABLE vendors
ADD vend_phone CHAR(20);


ALTER TABLE vendors
DROP COLUMN vend_phone;
```

> 警告
> 使用ALTER TABLE要极为小心，应该在进行改动前做完整的备份（模式和数据的备份）。数据库表的更改不能撤销，如果增加了不需要的列，也许无法删除它们。类似地，如果删除了不应该删除的列，可能会丢失该列中的所有数据。


## DROP TABLE

> 警告
> 玩火需谨慎，永久性删除，不能恢复。


> 提示：使用关系规则防止意外删除
 > 许多DBMS允许强制实施有关规则，防止删除与其他表相关联的表。在实施这些规则时，如果对某个表发布一条DROP TABLE语句，且该表是某个关系的组成部分，则DBMS将阻止这条语句执行，直到该关系被删除为止。如果允许，应该启用这些选项，它能防止意外删除有用的表。

## 重命名表

RENAME TABLE：对一个或多个表重命名。

```SQL
RENAME TABLE
products TO prods,
customers TO custs;


RENAME TABLE
prods TO products,
custs TO customers;
```

# 视图


> 视图，它不包含任何列或数据，包含的是一个查询。


为什么使用视图：

- 重用SQL语句（**经常使用的SQL语句**）。
- 简化复杂的SQL操作。在编写查询后，可以方便地重用它而不必知道其基本查询细节。
- 使用表的一部分而不是整个表。
- 保护数据。可以授予用户访问表的特定部分的权限，而不是整个表的访问权限。
- 更改数据格式和表示。视图可返回与底层表的表示和格式不同的数据。

可以对视图执行SELECT操作，过滤和排序数据，将视图联结到其他视图或表，甚至添加和更新数据，在添加或更改这些表中的数据时，视图将返回改变过的数据。


因为视图不包含数据，所以每次使用视图时，都必须处理查询执行时需要的所有检索。如果你用多个联结和过滤创建了复杂的视图或者嵌套了视图，**性能可能会下降得很厉害**。因此，在部署使用了大量视图的应用前，应该进行测试。

规则：

- 与表一样，视图必须唯一命名（不能给视图取与别的视图或表相同的名字）。
- 对于可以创建的视图数目没有限制。
- 创建视图，必须具有足够的访问权限。这些权限通常由数据库管理人员授予。
- 视图可以嵌套，即可以利用从其他视图中检索数据的查询来构造视图。所允许的嵌套层数在不同的DBMS中有所不同（嵌套视图可能会严重降低查询的性能，因此在产品环境中使用之前，应该对其进行全面测试）。
- 许多DBMS禁止在视图查询中使用ORDER BY子句。
- 有些DBMS要求对返回的所有列进行命名，如果列是计算字段，则需要使用别名（关于列别名的更多信息，请参阅第7课）。
- 视图不能索引，也不能有关联的触发器或默认值（因为它本身不存储数据）。
- 有些DBMS把视图作为只读的查询，这表示可以从视图检索数据，但不能将数据写回底层表。详情请参阅具体的DBMS文档。
- 有些DBMS允许创建这样的视图，它不能进行导致行不再属于视图的插入或更新。例如有一个视图，只检索带有电子邮件地址的顾客。如果更新某个顾客，删除他的电子邮件地址，将使该顾客不再属于视图。这是默认行为，而且是允许的，但有的DBMS可能会防止这种情况发生。

把视图理解为一个SQL语句就好。 

## 创建和删除视图

```SQL
CREATE VIEW view_name AS ...
DROP VIEW view_name;
```

```SQL
CREATE VIEW products_customers AS
SELECT cust_name, cust_contact, prod_id
FROM customers, orders, orderitems
WHERE customers.cust_id = orders.cust_id
  AND orders.order_num = orderitems.order_num;
```

```SQL
-- 查询购买RGAN01的人
SELECT cust_name, cust_contact
FROM products_customers
WHERE prod_id = 'RGAN01';
```

## 用视图重新格式化检索出的数据

对于第7部分（计算字段）的一个SQL语句如下：

```SQL
SELECT CONCAT(vend_name, ' (', vend_country, ')')
  AS vend_title
FROM vendors
ORDER BY vend_name;
```

我们经常使用这个格式的结果，如果每次都进行拼接，必然是麻烦的，创建一个视图，就可以重复使用它了。

```SQL
CREATE VIEW vendor_location AS
SELECT CONCAT(vend_name, ' (', vend_country, ')')
  AS vend_title
FROM vendors
ORDER BY vend_name;


SELECT *
FROM vendor_location;
```


## 用视图过滤不想要的数据


```SQL
CREATE VIEW customer_emaillist AS
SELECT cust_id, cust_name, cust_email
FROM Customers
WHERE cust_email IS NOT NULL;


SELECT *
FROM customer_emaillist;
```


## 使用视图与计算字段

```SQL
CREATE VIEW order_items_expanded AS
SELECT order_num,
       prod_id,
       quantity,
       item_price,
       quantity*item_price AS expanded_price
FROM orderitems;


SELECT *
FROM order_items_expanded
WHERE order_num = 20008;
```



# 使用存储程序


> 关键词：

存储过程就是为以后使用而保存的一条或多条SQL语句。可将其视为批文件，虽然它们的作用不仅限于批处理。

使用存储过程有三个主要的好处，即**简单、安全、高性能**。

至于为何会简单、安全、高性能，请看下面：

- 通过把处理封装在一个易用的单元中，可以简化复杂的操作（如前面例子所述）。
- 由于不要求反复建立一系列处理步骤，因而保证了数据的一致性。如果所有开发人员和应用程序都使用同一存储过程，则所使用的代码都是相同的。这一点的延伸就是防止错误。需要执行的步骤越多，出错的可能性就越大。防止错误保证了数据的一致性。
- 简化对变动的管理。如果表名、列名或业务逻辑（或别的内容）有变化，那么只需要更改存储过程的代码。使用它的人员甚至不需要知道这些变化。这一点的延伸就是安全性。通过存储过程限制对基础数据的访问，减少了数据讹误（无意识的或别的原因所导致的数据讹误）的机会。
- 因为存储过程通常以编译过的形式存储，所以DBMS处理命令的工作较少，提高了性能。
- 存在一些只能用在单个请求中的SQL元素和特性，存储过程可以使用它们来编写功能更强更灵活的代码。




```SQL
-- MySQL版
DELIMITER //
CREATE PROCEDURE MailingListCount (OUT ListCount INT)
BEGIN
    SELECT COUNT(*) INTO ListCount
    FROM Customers
    WHERE cust_email IS NOT NULL;
END//
DELIMITER ;

-- 使用存储过程
CALL MailingListCount(@ReturnValue);
SELECT @ReturnValue;
```

MySQL的存储过程资料可以查看MySQL文档和网络资料，更改《SQL必知必会》中代码所参考的资料为：
[时光机1号](http://doc.mysql.cn/mysql5/refman-5.1-zh.html-chapter/stored-procedures.html#stored-procedure-syntax)、[时光机2号](http://blog.sina.com.cn/s/blog_52d20fbf0100ofd5.html)。

以上代码的意思是`：`声明//为分隔符，因为MySQL使用`;`作为SQL语句的分隔符，这样可以使用`//`作为存储程序的分隔符。其中`ListCount`是整形变量，要在SQL语句中使用，最后面为调用存储过程，获取结果。



# 事务


> 关键词：要么完全执行，要么完全不执行，来维护数据库的完整性。

- 可以回退的语句：INSERT, UPDATE, DELETE。不能回退CREATE、DROP。
- 事务处理中可以使用这些语句，但进行回退时，这些操作也不撤销。

管理事务的关键在于将SQL语句组分解为逻辑块，并明确规定数据何时应该回退，何时不应该回退。

默认情况下，MySQL采用autocommit模式运行。

## 事务

MySQL的代码：

```SQL
-- 注意行尾的分号
START TRANSACTION;
...
COMMIT;
```

## 回退

```SQL
-- 使用教材的 DELETE FROM orders 会出错，有外键限制。
DELETE FROM copyproducts;
ROLLBACK;
```

## 保留点

回滚到设置好的点。

```SQL
SAVEPOINT identifier
-- do something, but run error
ROALLBACK TO SAVEPOINT identifier
```

## 完整例子

```SQL
-- SQL Server例子
BEGIN TRANSACTION
INSERT INTO Customers(cust_id, cust_name)
VALUES('1000000010', 'Toys Emporium');
SAVE TRANSACTION StartOrder;
INSERT INTO Orders(order_num, order_date, cust_id)
VALUES(20100,'2001/12/1','1000000010');
IF @@ERROR <> 0 ROLLBACK TRANSACTION StartOrder;
INSERT INTO OrderItems(order_num, order_item, prod_id, quantity, item_price)
VALUES(20100, 1, 'BR01', 100, 5.49);
IF @@ERROR <> 0 ROLLBACK TRANSACTION StartOrder;
INSERT INTO OrderItems(order_num, order_item, prod_id, quantity, item_price)
VALUES(20100, 2, 'BR03', 100, 10.99);
IF @@ERROR <> 0 ROLLBACK TRANSACTION StartOrder;
COMMIT TRANSACTION
```

尝试把他转换成MySQL，但IF语句，以及插入出错的方式不会写，花了半小时没找到方案。

如果使用C语言或者其他语言与MySQL交互，因为可以判断执行结果，会简单多了。

下面给出使用Python交互的例子。

```python
cursor.excute("START TRANSACTION");
sql = "INSERT INTO Customers(cust_id, cust_name) VALUES('1000000010', 'Toys Emporium')"
cursor.excute(sql)
cursor.excute("SAVEPOINT startorder")
try:
  sqls = ["INSERT INTO orders (order_num, order_date, cust_id) VALUES (20100, '2016/3/22', '100000010');", 
      "INSERT INTO OrderItems(order_num, order_item, prod_id, quantity, item_price) VALUES(20100, 1, 'BR01', 100, 5.49)",
      "INSERT INTO OrderItems(order_num, order_item, prod_id, quantity, item_price) VALUES(20100, 2, 'BR03', 100, 10.99);"]
  for sql in sqls:
    cursor.excute(sql)
  db.commit()
except:
  # cursor.rollback() # rolls back any changes to the database since the last call to commit()
  cursor.excute("ROLLBACK TO SAVEPOINT startorder")

```


# 游标


> 游标（cursor）是一个存储在DBMS服务器上的数据库查询，它不是一条SELECT语句，而是被该语句检索出来的结果集。在检索出来的行中前进或后退一行或多行，这就是游标的用途所在。

不同的DBMS支持的游标选项和特性不同。常见功能如下：

- 能够标记游标为只读，使数据能读取，但不能更新和删除。
- 能控制可以执行的定向操作（向前、向后、第一、最后、绝对位置、相对位置等）。
- 能标记某些列为可编辑的，某些列为不可编辑的。
- 规定范围，使游标对创建它的特定请求（如存储过程）或对所有请求可访问。
- 指示DBMS对检索出的数据（而不是指出表中活动数据）进行复制，使数据在游标打开和访问期间不变化。

使用步骤：

- 在使用游标前，必须声明（定义）它。这个过程实际上没有检索数据，它只是定义要使用的SELECT语句和游标选项。
- 一旦声明，就必须打开游标以供使用。这个过程用前面定义的SELECT语句把数据实际检索出来。
- 对于填有数据的游标，根据需要取出（检索）各行。
- 在结束游标使用时，必须关闭游标，可能的话，释放游标（有赖于具体的DBMS）。

具体看MySQL教程。



# 高级SQL特性


> 约束、索引、触发器。

## 约束

管理如何插入或处理数据库数据的规则。

DBMS通过在数据库表上施加约束来实施引用完整性。

### 主键

主键是一种特殊的约束，用来保证一列（或一组列）中的值是唯一的，而且永不改动。

- 任意两行的主键值都不相同。
 - 每行都具有一个主键值（即列中不允许NULL值）。
- 包含主键值的列从不修改或更新。
- 主键值不能重用。如果从表中删除某一行，其主键值不分配给新行

```SQL
ALTER TABLE vendors 
ADD CONSTRAINT PRIMARY KEY (vend_id)
```

建立表后，为表增加主键约束，也可以创建时指定。在创建表后，统一的增加各种约束是一种良好的实践。

### 外键

外键是表中的一列，其值必须列在另一表的主键中。外键是保证引用完整性的极其重要部分。

```SQL
ALTER TABLE orders
ADD CONSTRAINT
FOREIGN KEY (cust_id) REFERENCES customers (cust_id)
```

外键的另外作用：在定义外键后，DBMS不允许删除在另一个表中具有关联行的行。例如，不能删除关联订单的顾客。删除该顾客的唯一方法是首先删除相关的订单（这表示还要删除相关的订单项）。由于需要一系列的删除，因而利用外键可以防止意外删除数据。

MySQL支持称为级联删除（cascading delete）的特性。如果启用，该特性在从一个表中删除行时删除所有相关的数据。例如，如果启用级联删除并且从Customers表中删除某个顾客，则任何关联的订单行也会被自动删除。

### 唯一约束

唯一约束用来保证一列（或一组列）中的数据是唯一的。它们类似于主键，但存在以下重要区别。


- 表可包含多个唯一约束，但每个表只允许一个主键。
- 唯一约束列可包含NULL值。
- 唯一约束列可修改或更新。
- 唯一约束列的值可重复使用。
- 与主键不一样，唯一约束不能用来定义外键。

```SQL
ALTER TABLE user
ADD UNIQUE(wechat_id)
```

### 检查约束

检查约束用来保证一列（或一组列）中的数据满足一组指定的条件。检查约束的常见用途有以下几点。

- 检查最小或最大值。例如，防止0个物品的订单（即使0是合法的数）。
- 指定范围。例如，保证发货日期大于等于今天的日期，但不超过今天起一年后的日期。
- 只允许特定的值。例如，在性别字段中只允许M或F。

```SQL
ALTER TABLE user
ADD CONSTRAINT CHECK (gender LIKE '[MF]')
```

## 索引

索引用来排序数据以加快搜索和排序操作的速度。

主键数据总是排序的，这是DBMS的工作。因此，按主键检索特定行总是一种快速有效的操作。但是，搜索其他列中的值通常效率不高。

解决方法是使用索引。可以在一个或多个列上定义索引，使DBMS保存其内容的一个排过序的列表。在定义了索引后，DBMS以使用书的索引类似的方法使用它。DBMS搜索排过序的索引，找出匹配的位置，然后检索这些行。


- 索引改善检索操作的性能，但降低了数据插入、修改和删除的性能。在执行这些操作时，DBMS必须动态地更新索引。
- 索引数据可能要占用大量的存储空间。
- 并非所有数据都适合做索引。取值不多的数据（如州）不如具有更多可能值的数据（如姓或名），能通过索引得到那么多的好处。
- 索引用于数据过滤和数据排序。如果你经常以某种特定的顺序排序数据，则该数据可能适合做索引。
- 可以在索引中定义多个列（例如，州加上城市）。这样的索引仅在以州加城市的顺序排序时有用。如果想按城市排序，则这种索引没有用处。

索引的效率随表数据的增加或改变而变化。许多数据库管理员发现，过去创建的某个理想的索引经过几个月的数据处理后可能变得不再理想了。最好定期检查索引，并根据需要对索引进行调整

```SQL
create index prod_name_ind
ON products (prod_name);
```

> 猜想
> 索引是索引列到主键的映射。索引列是有序非递减的，DBMS可以采用快速定位算法（如二分查找）索引的位置，然后得到主键，再根据主键去查找记录。


## 触发器

触发器是特殊的存储过程，它在特定的数据库活动发生时自动执行。触发器可以与特定表上的INSERT、UPDATE和DELETE操作（或组合）相关联。

与存储过程不一样（存储过程只是简单的存储SQL语句），触发器与单个的表相关联。与Orders表上的INSERT操作相关联的触发器只在Orders表中插入行时执行。类似地，Customers表上的INSERT和UPDATE操作的触发器只在表上出现这些操作时执行。

触发器内的代码具有以下数据的访问权：


- INSERT操作中的所有新数据；
- UPDATE操作中的所有新数据和旧数据；
- DELETE操作中删除的数据。


用途：

- 保证数据一致。例如，在INSERT或UPDATE操作中将所有州名转换为大写。
- 基于某个表的变动在其他表上执行活动。例如，每当更新或删除一行时将审计跟踪记录写入某个日志表。
- 进行额外的验证并根据需要回退数据。例如，保证某个顾客的可用资金不超限定，如果已经超出，则阻塞插入。
- 计算计算列的值或更新时间戳。


> 一般来说，约束的处理比触发器快，因此在可能的时候，应该尽量使用约束。因为约束只是检查是不是符合要求，而触发器是进行修改，约束是把任务交给了上层。

## 数据库安全

- 对数据库管理功能（创建表、更改或删除已存在的表等）的访问；
- 对特定数据库或表的访问；
- 访问的类型（只读、对特定列的访问等）；
- 仅通过视图或存储过程对表进行访问；
- 创建多层次的安全措施，从而允许多种基于登录的访问和控制；
- 限制管理用户账号的能力。



> 本文使用Markdown编写。