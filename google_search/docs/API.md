# Web Search API 接口文档

## 1. 基础信息

| 项目     | 值                       |
| -------- | ------------------------ |
| 基础 URL | `http://localhost:25001` |
| 协议     | HTTP                     |
| 编码     | UTF-8                    |
| 响应格式 | JSON                     |

---

## 2. 通用说明

### 2.1 请求头

```
Content-Type: application/json
Accept: application/json
```

### 2.2 响应格式

成功响应:

```json
{
  "success": true,
  "query": "搜索关键词",
  "total": 10,
  "results": [...]
}
```

错误响应:

```json
{
  "error": "错误信息",
  "query": "搜索关键词"
}
```

---

## 3. 接口列表

### 3.1 健康检查

#### GET /health

检查服务是否正常运行。

**请求示例:**

```bash
curl http://localhost:25001/health
```

**响应示例:**

```json
{
  "status": "ok",
  "service": "web-search-api"
}
```

---

### 3.2 网页搜索

#### GET /web_search

搜索网页内容，支持多个搜索引擎自动切换。

**参数说明:**

| 参数    | 类型   | 必填 | 默认值                           | 说明                   |
| ------- | ------ | ---- | -------------------------------- | ---------------------- |
| q       | string | 是   | -                                | 搜索关键词             |
| num     | int    | 否   | 10                               | 返回结果数量 (1-50)    |
| engines | string | 否   | duckduckgo,bing,google_api,baidu | 搜索引擎列表，逗号分隔 |
| api_key | string | 否   | -                                | Google API Key (临时)  |
| cse_id  | string | 否   | -                                | Google CSE ID (临时)   |

**请求示例:**

```bash
# 基本搜索
curl "http://localhost:25001/web_search?q=python&num=5"

# 指定搜索引擎
curl "http://localhost:25001/web_search?q=python&engines=duckduckgo,baidu"

# POST 请求
curl -X POST -H "Content-Type: application/json" \
  -d '{"q": "python tutorial", "num": 5}' \
  http://localhost:25001/web_search
```

**响应示例:**

```json
{
  "success": true,
  "query": "python",
  "total": 5,
  "results": [
    {
      "rank": 1,
      "title": "Welcome to Python.org",
      "url": "https://www.python.org/",
      "snippet": "Python is a programming language that lets you work quickly...",
      "engine": "duckduckgo"
    },
    {
      "rank": 2,
      "title": "Python Tutorial - W3Schools",
      "url": "https://www.w3schools.com/python/",
      "snippet": "Python is a widely used general-purpose, high-level programming language...",
      "engine": "bing"
    }
  ]
}
```

**结果字段说明:**

| 字段    | 类型   | 说明     |
| ------- | ------ | -------- |
| rank    | int    | 排名     |
| title   | string | 标题     |
| url     | string | 链接     |
| snippet | string | 摘要     |
| engine  | string | 来源引擎 |

---

### 3.3 网页抓取

#### POST /web_fetch

获取指定 URL 的页面内容。

**参数说明:**

| 参数    | 类型   | 必填 | 默认值 | 说明         |
| ------- | ------ | ---- | ------ | ------------ |
| url     | string | 是   | -      | 要抓取的网址 |
| timeout | int    | 否   | 15     | 超时时间(秒) |

**请求示例:**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org"}' \
  http://localhost:25001/web_fetch
```

**响应示例:**

```json
{
  "success": true,
  "url": "https://www.python.org/",
  "title": "Python.org",
  "content_type": "text/html; charset=utf-8",
  "text": "Python is a programming language that lets you work quickly and integrate...",
  "raw_html": "<!doctype html>..."
}
```

**响应字段说明:**

| 字段         | 类型   | 说明                      |
| ------------ | ------ | ------------------------- |
| success      | bool   | 是否成功                  |
| url          | string | 实际访问的 URL            |
| title        | string | 页面标题                  |
| content_type | string | 内容类型                  |
| text         | string | 提取的文本内容 (最大10KB) |
| raw_html     | string | 原始 HTML (最大50KB)      |

**错误响应:**

```json
{
  "success": false,
  "error": "Timeout",
  "url": "https://example.com"
}
```

---

### 3.4 搜索 (别名)

#### GET /search

`/web_search` 的别名，功能完全相同。

```bash
curl "http://localhost:25001/search?q=python"
```

---

## 4. 使用示例

### 4.1 Python 调用

```python
import requests

# 搜索
response = requests.get("http://localhost:25001/web_search", params={
    "q": "python",
    "num": 5
})
print(response.json())

# 抓取网页
response = requests.post("http://localhost:25001/web_fetch", json={
    "url": "https://www.python.org"
})
print(response.json())
```

### 4.2 JavaScript 调用

```javascript
// 搜索
fetch("http://localhost:25001/web_search?q=python&num=5")
  .then((res) => res.json())
  .then((data) => console.log(data));

// 抓取
fetch("http://localhost:25001/web_fetch", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ url: "https://www.python.org" }),
})
  .then((res) => res.json())
  .then((data) => console.log(data));
```

### 4.3 cURL 调用

```bash
# 搜索
curl "http://localhost:25001/web_search?q=python教程&num=10"

# 搜索指定引擎
curl "http://localhost:25001/web_search?q=python&engines=baidu,bing"

# 抓取网页
curl -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org", "timeout": 10}' \
  http://localhost:25001/web_fetch

# 批量搜索 (需要实现)
curl -X POST -H "Content-Type: application/json" \
  -d '{"queries": ["python", "java", "go"], "num": 5}' \
  http://localhost:25001/web_batch
```

---

## 5. 错误码

| HTTP 状态码 | 说明           |
| ----------- | -------------- |
| 200         | 成功           |
| 400         | 请求参数错误   |
| 404         | 接口不存在     |
| 500         | 服务器内部错误 |
| 504         | 请求超时       |

---

## 6. 注意事项

1. **搜索限制**: 建议每次请求间隔 1 秒以上
2. **结果数量**: 最大支持 50 条/请求
3. **超时设置**: 搜索引擎默认 15 秒超时
4. **中文编码**: URL 中的中文需要 URL 编码
5. **Google API**: 需要自行申请 API Key 和 CSE ID

---

## 7. 环境变量

| 变量名         | 说明            | 获取方式                   |
| -------------- | --------------- | -------------------------- |
| GOOGLE_API_KEY | Google API 密钥 | Google Cloud Console       |
| GOOGLE_CSE_ID  | 搜索引擎 ID     | Programmable Search Engine |
| SERVER_PORT    | 服务端口        | 默认 25001                 |
