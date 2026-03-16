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

### 2.1 认证

**如果设置了 `API_TOKEN` 环境变量**，所有请求（除 `/health` 外）需要提供认证令牌。

**支持的认证头：**

```
Authorization: Bearer your-api-token
```

或

```
X-API-Token: your-api-token
```

### 2.2 请求头

```
Content-Type: application/json
Accept: application/json
Authorization: Bearer your-api-token  # 如果启用了认证
```

### 2.3 响应格式

**成功响应：**

```json
{
  "success": true,
  ...
}
```

**错误响应：**

```json
{
  "error": "错误信息"
}
```

**认证失败（401）：**

```json
{
  "error": "Missing API token. Provide via 'Authorization: Bearer <token>' or 'X-API-Token: <token>' header"
}
```

或

```json
{
  "error": "Invalid API token"
}
```

---

## 3. 接口列表

### 3.1 健康检查

#### GET /health

检查服务是否正常运行。**此接口无需认证。**

**请求示例：**

```bash
curl http://localhost:25001/health
```

**响应示例：**

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

**参数说明：**

| 参数    | 类型   | 必填 | 默认值                           | 说明                   |
| ------- | ------ | ---- | -------------------------------- | ---------------------- |
| q       | string | 是   | -                                | 搜索关键词             |
| num     | int    | 否   | 10                               | 返回结果数量 (1-50)    |
| engines | string | 否   | duckduckgo,bing,google_api,baidu | 搜索引擎列表，逗号分隔 |
| api_key | string | 否   | -                                | Google API Key (临时)  |
| cse_id  | string | 否   | -                                | Google CSE ID (临时)   |

**支持的搜索引擎：**

- `duckduckgo` - DuckDuckGo（免费，无需配置）
- `bing` - Bing 搜索（免费，需网络通畅）
- `google_api` - Google Custom Search API（需要 API Key）
- `baidu` - 百度搜索（免费，国内访问快）

**请求示例：**

```bash
# 基本搜索
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:25001/web_search?q=python&num=5"

# 指定搜索引擎
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:25001/web_search?q=python&engines=duckduckgo,baidu"

# 只使用 Google API
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:25001/web_search?q=python&engines=google_api&api_key=KEY&cse_id=CSE_ID"

# POST 请求
curl -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"q": "python tutorial", "num": 5, "engines": ["bing", "baidu"]}' \
  http://localhost:25001/web_search
```

**响应示例：**

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

**结果字段说明：**

| 字段    | 类型   | 说明     |
| ------- | ------ | -------- |
| rank    | int    | 排名     |
| title   | string | 标题     |
| url     | string | 链接     |
| snippet | string | 摘要     |
| engine  | string | 来源引擎 |

**搜索策略：**

- 按顺序调用引擎，一旦获取足够结果就停止
- 自动去重（URL 唯一性）
- 引擎间有 0.5-1.5 秒延迟防止请求过快

---

### 3.3 网页抓取

#### POST /web_fetch

获取指定 URL 的页面内容（返回原始 HTML）。

**参数说明：**

| 参数        | 类型    | 必填 | 默认值 | 说明                |
| ----------- | ------- | ---- | ------ | ------------------- |
| url         | string  | 是   | -      | 要抓取的网址        |
| timeout     | int     | 否   | 15     | 超时时间 (秒)       |
| max_chars   | int     | 否   | 50000  | 最大返回字符数      |
| use_cache   | boolean | 否   | true   | 是否使用缓存        |

**SSRF 防护：**

以下网址会被阻止：
- `localhost` 及其变体
- `.local`、`.internal` 域名
- 私有 IP 地址（10.x.x.x, 192.168.x.x, 172.16-31.x.x）

**请求示例：**

```bash
# 基本抓取
curl -H "Authorization: Bearer TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org"}' \
  http://localhost:25001/web_fetch

# 禁用缓存
curl -H "Authorization: Bearer TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org", "use_cache": false}' \
  http://localhost:25001/web_fetch

# 增加超时
curl -H "Authorization: Bearer TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "timeout": 30}' \
  http://localhost:25001/web_fetch
```

**响应示例：**

```json
{
  "success": true,
  "url": "https://www.python.org/",
  "finalUrl": "https://www.python.org/",
  "status": 200,
  "contentType": "text/html",
  "title": "Welcome to Python.org",
  "text": "<!doctype html><html>...",
  "truncated": false,
  "length": 52518,
  "fetchedAt": "2026-03-16T15:17:28Z",
  "tookMs": 1329
}
```

**响应字段说明：**

| 字段         | 类型   | 说明                      |
| ------------ | ------ | ------------------------- |
| success      | bool   | 是否成功                  |
| url          | string | 请求的 URL                |
| finalUrl     | string | 最终 URL（重定向后）      |
| status       | int    | HTTP 状态码               |
| contentType  | string | 内容类型                  |
| title        | string | 页面标题                  |
| text         | string | 原始 HTML 内容            |
| truncated    | bool   | 是否被截断                |
| length       | int    | 内容长度（字节）          |
| fetchedAt    | string | 抓取时间（ISO 8601）      |
| tookMs       | int    | 耗时（毫秒）              |

**错误响应：**

```json
{
  "success": false,
  "error": "HTTP 403",
  "url": "https://example.com"
}
```

或

```json
{
  "success": false,
  "error": "Blocked hostname: localhost",
  "url": "http://localhost:8080"
}
```

---

### 3.4 搜索 (别名)

#### GET /search

`/web_search` 的别名，功能完全相同。

**请求示例：**

```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:25001/search?q=python"
```

---

## 4. 使用示例

### 4.1 Python 调用

```python
import requests

API_TOKEN = "your-api-token"
BASE_URL = "http://localhost:25001"

headers = {"Authorization": f"Bearer {API_TOKEN}"}

# 搜索
response = requests.get(
    f"{BASE_URL}/web_search",
    headers=headers,
    params={"q": "python", "num": 5}
)
print(response.json())

# 抓取网页
response = requests.post(
    f"{BASE_URL}/web_fetch",
    headers=headers,
    json={"url": "https://www.python.org", "use_cache": False}
)
print(response.json())

# 指定搜索引擎
response = requests.get(
    f"{BASE_URL}/web_search",
    headers=headers,
    params={"q": "python", "engines": "duckduckgo,bing"}
)
print(response.json())
```

### 4.2 JavaScript 调用

```javascript
const API_TOKEN = "your-api-token";
const BASE_URL = "http://localhost:25001";

const headers = {
  "Authorization": `Bearer ${API_TOKEN}`,
  "Content-Type": "application/json"
};

// 搜索
fetch(`${BASE_URL}/web_search?q=python&num=5`, { headers })
  .then((res) => res.json())
  .then((data) => console.log(data));

// 抓取
fetch(`${BASE_URL}/web_fetch`, {
  method: "POST",
  headers,
  body: JSON.stringify({ url: "https://www.python.org" }),
})
  .then((res) => res.json())
  .then((data) => console.log(data));

// 使用 async/await
async function search(query) {
  const response = await fetch(`${BASE_URL}/web_search?q=${encodeURIComponent(query)}`, {
    headers,
  });
  return await response.json();
}

async function fetchUrl(url) {
  const response = await fetch(`${BASE_URL}/web_fetch`, {
    method: "POST",
    headers,
    body: JSON.stringify({ url }),
  });
  return await response.json();
}
```

### 4.3 cURL 调用

```bash
TOKEN="your-api-token"
BASE_URL="http://localhost:25001"
AUTH_HEADER="Authorization: Bearer $TOKEN"

# 健康检查（无需认证）
curl "$BASE_URL/health"

# 搜索
curl -H "$AUTH_HEADER" "$BASE_URL/web_search?q=python&num=10"

# 搜索指定引擎
curl -H "$AUTH_HEADER" "$BASE_URL/web_search?q=python&engines=baidu,bing"

# 抓取网页
curl -H "$AUTH_HEADER" -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org"}' \
  "$BASE_URL/web_fetch"

# 抓取网页（禁用缓存）
curl -H "$AUTH_HEADER" -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org", "use_cache": false}' \
  "$BASE_URL/web_fetch"
```

### 4.4 Node.js (Axios)

```javascript
const axios = require('axios');

const API_TOKEN = 'your-api-token';
const BASE_URL = 'http://localhost:25001';

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Authorization': `Bearer ${API_TOKEN}`,
    'Content-Type': 'application/json'
  }
});

// 搜索
async function search(query, num = 10) {
  const response = await client.get('/web_search', {
    params: { q: query, num }
  });
  return response.data;
}

// 抓取
async function fetchUrl(url) {
  const response = await client.post('/web_fetch', { url });
  return response.data;
}

// 使用示例
search('python', 5).then(console.log);
fetchUrl('https://www.python.org').then(console.log);
```

---

## 5. 错误码

| HTTP 状态码 | 说明                                    |
| ----------- | --------------------------------------- |
| 200         | 成功                                    |
| 400         | 请求参数错误（缺少必需参数）            |
| 401         | 认证失败（缺少或无效的 API Token）      |
| 404         | 接口不存在                              |
| 500         | 服务器内部错误                          |
| 504         | 请求超时                                |

**常见错误信息：**

| 错误信息                                           | 说明                 |
| -------------------------------------------------- | -------------------- |
| `Missing required parameter: q`                   | 搜索缺少关键词       |
| `Missing required parameter: url`                 | 抓取缺少 URL         |
| `Missing API token...`                            | 缺少认证令牌         |
| `Invalid API token`                               | 认证令牌无效         |
| `Blocked hostname: localhost`                     | SSRF 防护阻止访问    |
| `HTTP 403`                                        | 目标网站拒绝访问     |
| `Timeout`                                         | 请求超时             |
| `Too many redirects`                              | 重定向次数过多       |

---

## 6. 注意事项

1. **认证**: 生产环境建议设置 `API_TOKEN` 启用认证
2. **搜索限制**: 建议每次请求间隔 1 秒以上，避免请求过快
3. **结果数量**: 最大支持 50 条/请求
4. **超时设置**: 搜索引擎默认 15 秒超时，网页抓取可自定义
5. **中文编码**: URL 中的中文需要 URL 编码
6. **Google API**: 需要自行申请 API Key 和 CSE ID
7. **反爬网站**: 某些网站（如知乎）有严格反爬，可能返回 403
8. **缓存**: web_fetch 默认启用 5 分钟缓存，可通过 `use_cache: false` 禁用
9. **SSRF 防护**: 禁止访问内网地址，防止服务器被利用

---

## 7. 最佳实践

### 7.1 错误处理

```python
import requests
from requests.exceptions import RequestException

def safe_search(query):
    try:
        response = requests.get(
            "http://localhost:25001/web_search",
            headers={"Authorization": f"Bearer {TOKEN}"},
            params={"q": query},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return data["results"]
        else:
            print(f"Search failed: {data.get('error')}")
            return []
    except RequestException as e:
        print(f"Request error: {e}")
        return []
```

### 7.2 批量搜索

```python
def batch_search(queries, num=5):
    results = {}
    for query in queries:
        results[query] = safe_search(query)
    return results

# 使用
queries = ["python", "javascript", "go"]
all_results = batch_search(queries)
```

### 7.3 缓存利用

```python
# 第一次请求（缓存）
response1 = requests.post(url, json={"url": "https://example.com"})

# 第二次请求（命中缓存，更快）
response2 = requests.post(url, json={"url": "https://example.com"})

# 强制刷新
response3 = requests.post(url, json={"url": "https://example.com", "use_cache": False})
```

---

## 8. 相关文档

- [配置文档](CONFIG.md) - 部署配置、环境变量、安全设置
- [设计文档](DESIGN.md) - 系统架构、模块设计
