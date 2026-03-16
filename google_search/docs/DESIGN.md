# Web Search API 功能设计文档

## 1. 项目概述

### 1.1 项目简介

Web Search API 是一个基于 Python Flask 的搜索服务，支持多引擎搜索和网页内容抓取，无需 API Key（可选支持 Google Custom Search API）。

### 1.2 核心功能

- **多引擎搜索**: 按顺序调用多个搜索引擎，提高搜索成功率，一但有结果返回则无需重复搜索，都没有搜索结果则返回错误提示
- **网页抓取**: 支持获取任意 URL 的页面内容
- **日志追踪**: 完整的请求日志，便于问题排查

### 1.3 技术栈

- Python 3.11
- Flask 2.0+
- requests
- beautifulsoup4
- lxml
- Docker + Docker Compose

---

## 2. 系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                                │
│  (curl / Postman / Frontend)                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask API Server                         │
│  Port: 25001                                                 │
├─────────────────────────────────────────────────────────────┤
│  /health     - 健康检查                                      │
│  /web_search - 搜索接口                                      │
│  /web_fetch  - 网页抓取                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ DuckDuck │ │  Bing   │ │  Baidu   │
    │   Go     │ │         │ │          │
    └──────────┘ └──────────┘ └──────────┘
          │           │           │
          └───────────┴───────────┘
                      │
                      ▼
          ┌─────────────────────┐
          │  Google Custom      │
          │  Search API (可选)  │
          └─────────────────────┘
```

### 2.2 模块设计

#### 2.2.1 search_engine.py - 搜索引擎模块

| 类名             | 功能                     | 依赖                           |
| ---------------- | ------------------------ | ------------------------------ |
| DuckDuckGoSearch | DuckDuckGo HTML 搜索     | requests, beautifulsoup4       |
| BingSearch       | Bing 搜索                | requests, beautifulsoup4       |
| BaiduSearch      | Baidu 搜索               | requests, beautifulsoup4, lxml |
| GoogleSearchAPI  | Google Custom Search API | requests (需要 API Key)        |

**核心函数:**

```python
def search(keyword, num_results, engines, google_api_key, google_cse_id)
def fetch_url(url, timeout)
```

#### 2.2.2 server.py - API 服务模块

| 路由        | 方法     | 功能     |
| ----------- | -------- | -------- |
| /health     | GET      | 健康检查 |
| /web_search | GET/POST | 搜索     |
| /web_fetch  | GET/POST | 网页抓取 |

---

## 3. 功能详情

### 3.1 多引擎搜索

#### 3.1.1 引擎列表与优先级

| 顺序 | 引擎名称   | 说明                     | 需要配置 |
| ---- | ---------- | ------------------------ | -------- |
| 1    | duckduckgo | 免费，无需配置           | 否       |
| 2    | bing       | 免费，需网络通畅         | 否       |
| 3    | google_api | Google Custom Search API | 是       |
| 4    | baidu      | 免费，国内访问快         | 否       |

#### 3.1.2 搜索流程

```
1. 接收搜索关键词
2. 按顺序遍历引擎列表
3. 每个引擎尝试获取结果
4. 去重（URL 唯一性）
5. 返回结果
```

#### 3.1.3 去重策略

- 使用 URL 作为唯一标识
- 已使用的 URL 放入集合，后续结果跳过

### 3.2 网页抓取

#### 3.2.1 支持内容类型

- HTML 页面（提取 title 和 text）
- 二进制内容（返回大小信息）

#### 3.2.2 响应字段

```json
{
  "success": true,
  "url": "实际访问的URL",
  "title": "页面标题",
  "content_type": "text/html",
  "text": "提取的文本内容",
  "raw_html": "原始HTML(前50KB)"
}
```

### 3.3 日志系统

#### 3.3.1 日志级别

- INFO: 正常请求日志
- WARNING: 引擎调用失败
- ERROR: 程序异常

#### 3.3.2 日志格式

```
2026-03-16 20:23:05,776 - google_search.search_engine - INFO - Starting search for: python
2026-03-16 20:23:05,776 - google_search.search_engine - INFO - Using engines: ['baidu']
2026-03-16 20:23:09,834 - google_search.search_engine - INFO - [baidu] Got 1 results, total unique: 1
```

---

## 4. 部署设计

### 4.1 Docker 部署

#### 4.1.1 基础镜像

```dockerfile
python:3.11-slim
```

#### 4.1.2 资源限制 (2C2G 建议)

- CPU: 1 core
- Memory: 512MB
- Disk: 5GB

### 4.2 环境变量

| 变量名         | 默认值     | 说明                   |
| -------------- | ---------- | ---------------------- |
| GOOGLE_API_KEY | -          | Google API Key（可选） |
| GOOGLE_CSE_ID  | -          | Google CSE ID（可选）  |
| FLASK_ENV      | production | 运行环境               |
| SERVER_PORT    | 25001      | 服务端口               |

### 4.3 端口映射

- 宿主机：25001
- 容器：25001

### 4.4 环境变量

| 变量名         | 默认值     | 说明                   |
| -------------- | ---------- | ---------------------- |
| API_TOKEN      | -          | API 认证令牌（可选）   |
| GOOGLE_API_KEY | -          | Google API Key（可选） |
| GOOGLE_CSE_ID  | -          | Google CSE ID（可选）  |
| FLASK_ENV      | production | 运行环境               |
| SERVER_PORT    | 25001      | 服务端口               |

---

## 5. 错误处理

### 5.1 错误码

| 状态码 | 说明           |
| ------ | -------------- |
| 200    | 成功           |
| 400    | 参数错误       |
| 401    | 认证失败       |
| 500    | 服务器内部错误 |

### 5.2 错误响应格式

```json
{
  "error": "错误信息"
}
```

### 5.3 认证错误

**缺少 Token：**
```json
{
  "error": "Missing API token. Provide via 'Authorization: Bearer <token>' or 'X-API-Token: <token>' header"
}
```

**无效 Token：**
```json
{
  "error": "Invalid API token"
}
```

---

## 6. 安全设计

### 6.1 API 认证

- 支持 `Authorization: Bearer <token>` 头
- 支持 `X-API-Token: <token>` 头
- `/health` 接口无需认证
- 通过 `API_TOKEN` 环境变量配置

### 6.2 SSRF 防护

**阻止访问：**
- `localhost` 及其变体
- `.local`、`.internal` 域名
- 私有 IP 地址（10.x.x.x, 192.168.x.x, 172.16-31.x.x）
- 保留 IP 地址

**实现方式：**
- DNS 解析前检查主机名
- DNS 解析后检查 IP 地址
- 失败关闭原则（fail closed）

---

## 7. 性能考虑

### 7.1 超时设置

- 搜索引擎请求：15 秒
- 网页抓取：15 秒（可配置）

### 7.2 请求间隔

- 引擎间：0.5-1.5 秒随机延迟
- 防止请求过快被封

### 7.3 结果限制

- 默认返回 10 条
- 最大支持 50 条

### 7.4 缓存机制

- 内存缓存，默认 5 分钟 TTL
- 最多保留 100 条缓存
- 可通过 `use_cache: false` 禁用

---

## 8. 模块更新

### 8.1 enhanced_fetch.py - 增强网页抓取模块

**新增功能：**
- SSRF 防护
- 内存缓存
- 原始 HTML 返回
- 重定向限制
- 响应大小限制

**核心函数：**
```python
def fetch_url(
    url: str,
    timeout: int = 15,
    max_chars: int = 50000,
    max_redirects: int = 3,
    extract_mode: str = "markdown",
    use_cache: bool = True,
    cache_ttl: int = 300
) -> Dict[str, Any]
```

### 8.2 server.py - API 服务模块更新

**新增路由：**
| 路由        | 方法     | 功能     | 认证 |
| ----------- | -------- | -------- | ---- |
| /health     | GET      | 健康检查 | 否   |
| /web_search | GET/POST | 搜索     | 是   |
| /web_fetch  | GET/POST | 网页抓取 | 是   |
| /search     | GET/POST | 搜索别名 | 是   |

**认证中间件：**
```python
@app.before_request
def authenticate():
    if request.path == "/health":
        return None
    # 检查 API_TOKEN
```

---

## 9. 未来扩展

### 9.1 计划功能

- [ ] 添加代理支持
- [ ] 添加 Redis 缓存
- [ ] 添加速率限制
- [ ] 添加更多搜索引擎 (Yahoo, Yandex)
- [ ] 异步请求支持 (asyncio)
- [ ] 批量搜索接口

### 9.2 监控集成

- [ ] Prometheus 指标
- [ ] Grafana 仪表板
- [ ] 日志收集 (ELK)
