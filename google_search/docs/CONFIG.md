# Web Search API 配置文档

## 1. 环境变量

| 变量名         | 必填 | 默认值     | 说明                                |
| -------------- | ---- | ---------- | ----------------------------------- |
| `API_TOKEN`    | 否   | -          | API 认证令牌，设置后启用认证         |
| `GOOGLE_API_KEY` | 否 | -          | Google Custom Search API 密钥       |
| `GOOGLE_CSE_ID` | 否  | -          | Google Custom Search Engine ID      |
| `FLASK_ENV`    | 否   | production | 运行环境 (production/development)   |
| `SERVER_PORT`  | 否   | 25001      | 服务端口                            |

---

## 2. 部署配置

### 2.1 Docker Compose 部署

**创建 `.env` 文件：**

```bash
# API 认证令牌（可选，设置后所有请求需要带 token）
API_TOKEN=your-secret-token

# Google Custom Search API（可选）
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id

# 其他配置
FLASK_ENV=production
SERVER_PORT=25001
```

**启动服务：**

```bash
docker compose up -d
```

**查看日志：**

```bash
docker compose logs -f
```

**停止服务：**

```bash
docker compose down
```

### 2.2 直接运行

**安装依赖：**

```bash
pip install -r requirements.txt
```

**启动服务：**

```bash
# 默认配置
python -m server

# 自定义端口
python -m server --port 8080

# 调试模式
python -m server --debug

# 设置环境变量
API_TOKEN=your-token GOOGLE_API_KEY=key GOOGLE_CSE_ID=id python -m server
```

---

## 3. API 认证配置

### 3.1 启用认证

设置 `API_TOKEN` 环境变量后，所有请求（除 `/health` 外）需要提供认证令牌。

```bash
# 启用认证
export API_TOKEN=your-secret-token
python -m server
```

### 3.2 请求头格式

支持两种认证头：

**方式一：Bearer Token（推荐）**
```
Authorization: Bearer your-secret-token
```

**方式二：自定义 Header**
```
X-API-Token: your-secret-token
```

### 3.3 认证响应

**认证成功：** 正常返回接口数据

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

## 4. 高级配置

### 4.1 多引擎配置

**默认引擎顺序：** duckduckgo → bing → google_api → baidu

**自定义引擎顺序：**
```bash
# 只使用 duckduckgo 和 bing
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:25001/web_search?q=python&engines=duckduckgo,bing"

# 只使用 baidu（国内访问快）
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:25001/web_search?q=python&engines=baidu"
```

### 4.2 Google API 配置

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目并启用 Custom Search API
3. 创建 API Key
4. 在 [Programmable Search Engine](https://programmablesearchengine.google.com/) 创建搜索引擎
5. 获取 CSE ID
6. 设置环境变量：
   ```bash
   GOOGLE_API_KEY=your_api_key
   GOOGLE_CSE_ID=your_cse_id
   ```

### 4.3 性能调优

**修改 `enhanced_fetch.py` 中的常量：**

```python
DEFAULT_TIMEOUT_SECONDS = 15          # 请求超时时间
DEFAULT_MAX_CHARS = 50_000            # 返回最大字符数
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000  # 最大响应大小 (2MB)
DEFAULT_MAX_REDIRECTS = 3             # 最大重定向次数
DEFAULT_CACHE_TTL_SECONDS = 300       # 缓存 TTL (5 分钟)
```

### 4.4 缓存配置

**内存缓存：** 默认启用，5 分钟 TTL

**禁用缓存：**
```bash
curl -H "Authorization: Bearer TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "use_cache": false}' \
  http://localhost:25001/web_fetch
```

---

## 5. 安全配置

### 5.1 SSRF 防护

内置 SSRF 防护，阻止访问：

- `localhost` 及其变体
- `.local`、`.internal` 域名
- 私有 IP 地址（10.x.x.x, 192.168.x.x, 172.16-31.x.x）
- 保留 IP 地址

**测试 SSRF 防护：**
```bash
# 这些请求会被阻止
curl http://localhost:25001/web_fetch?url=http://localhost:8080
curl http://localhost:25001/web_fetch?url=http://192.168.1.1
# 返回：{"error": "Blocked hostname: localhost"}
```

### 5.2 访问日志

```bash
docker compose logs -f | grep "web_search\|web_fetch"
```

### 5.3 建议的安全措施

1. **始终设置 `API_TOKEN`**：生产环境必须启用认证
2. **使用 HTTPS**：通过反向代理（Nginx/Caddy）提供 HTTPS
3. **限制请求频率**：在反向代理层配置速率限制
4. **定期更新令牌**：定期更换 `API_TOKEN`

---

## 6. Nginx 反向代理配置

```nginx
server {
    listen 443 ssl;
    server_name search.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:25001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 速率限制
        limit_req zone=api burst=10 nodelay;
    }
}

# 速率限制区域
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

---

## 7. 监控与健康检查

### 7.1 健康检查接口

```bash
curl http://localhost:25001/health
# 返回：{"status": "ok", "service": "web-search-api"}
```

### 7.2 Docker 健康检查

Docker Compose 已配置健康检查：

- 检查间隔：30 秒
- 超时：10 秒
- 重试次数：3 次
- 启动宽限期：10 秒

### 7.3 日志级别

修改 `server.py` 中的日志级别：

```python
logging.basicConfig(
    level=logging.INFO,  # 可选：DEBUG, INFO, WARNING, ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## 8. 故障排查

### 8.1 常见问题

**问题 1：所有搜索都返回 0 结果**
- 检查网络连接
- 尝试只使用单个引擎：`engines=baidu`
- 查看日志：`docker compose logs | grep "No results"`

**问题 2：web_fetch 返回 403**
- 某些网站（如知乎）有反爬机制
- 尝试添加 User-Agent 或使用代理
- 这是正常行为，不是代码错误

**问题 3：认证失败**
- 确认 `API_TOKEN` 环境变量已设置
- 检查请求头格式：`Authorization: Bearer <token>`
- 重启服务使配置生效

### 8.2 查看日志

```bash
# 实时日志
docker compose logs -f

# 最近 100 行
docker compose logs --tail=100

# 搜索特定接口
docker compose logs | grep "web_search"
```

---

## 9. 版本历史

- **v2.0.0** (2026-03-16): 增强 web_fetch，添加 SSRF 防护、缓存、API 认证
- **v1.0.0** (2026-03-16): 初始版本，多引擎搜索、网页抓取
