# FreePics 图床服务

一个基于 Flask 的轻量级图床服务，支持 Docker 一键部署、SSL 加密、跨域访问控制和白名单配置。

## 功能特性

- ✅ **图片上传/删除** - 通过 REST API 上传和删除图片
- ✅ **SSL 支持** - 自动配置 HTTPS 和 SSL 证书
- ✅ **跨域控制** - 可配置的 CORS 白名单
- ✅ **Docker 部署** - 一键部署，包含 Nginx 反向代理
- ✅ **图片优化** - 可选的图片压缩和尺寸优化
- ✅ **API 密钥验证** - 可配置的 API 访问控制
- ✅ **健康检查** - 服务状态监控
- ✅ **配置外挂** - 支持外部配置文件

## 快速开始

### 方式一：Docker Hub 一键部署（推荐）

```bash
# 下载一键部署脚本
curl -O https://raw.githubusercontent.com/your-repo/freepics/main/quick-deploy.sh

# 编辑配置（修改域名、邮箱、Docker镜像地址）
nano quick-deploy.sh

# 运行一键部署
chmod +x quick-deploy.sh
./quick-deploy.sh
```

### 方式二：本地构建部署

#### 1. 克隆项目

```bash
git clone <repository-url>
cd freepics
```

#### 2. 选择部署方式

**开发环境：**
```bash
docker-compose up -d
```

**生产环境：**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**使用Docker Hub镜像：**
```bash
docker-compose -f docker-compose.hub.yml up -d
```

#### 3. 配置服务

编辑 `config/config.json` 文件：

```json
{
  "allowed_origins": [
    "https://noimnotahuman.top",
    "https://www.noimnotahuman.top",
    "http://localhost:3000"
  ],
  "api_keys": [
    "your-secure-api-key-here"
  ],
  "max_file_size": 10485760,
  "allowed_extensions": ["png", "jpg", "jpeg", "gif", "webp", "bmp"]
}
```

#### 4. 配置 SSL 证书

```bash
# 编辑 setup-ssl.sh 中的邮箱地址
nano setup-ssl.sh

# 运行 SSL 设置脚本
./setup-ssl.sh
```

## API 文档

### 基础信息

- **基础 URL**: `https://noimnotahuman.top`
- **认证方式**: API Key（通过 Header `X-API-Key` 或查询参数 `api_key`）

### 接口列表

#### 1. 健康检查

```http
GET /health
```

**响应示例:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0"
}
```

#### 2. 上传图片

```http
POST /upload
Content-Type: multipart/form-data
X-API-Key: your-api-key
```

**参数:**
- `file`: 图片文件（必需）
- `optimize`: 是否优化图片 (`true`/`false`，可选)

**响应示例:**
```json
{
  "success": true,
  "filename": "20240101_120000_uuid.jpg",
  "url": "https://noimnotahuman.top/image/20240101_120000_uuid.jpg",
  "size": 1024000,
  "hash": "md5-hash-here",
  "upload_time": "2024-01-01T12:00:00"
}
```

#### 3. 删除图片

```http
DELETE /delete/{filename}
X-API-Key: your-api-key
```

**响应示例:**
```json
{
  "success": true,
  "message": "文件 filename.jpg 删除成功",
  "delete_time": "2024-01-01T12:00:00"
}
```

#### 4. 访问图片

```http
GET /image/{filename}
```

直接返回图片文件。

#### 5. 列出所有图片

```http
GET /list
X-API-Key: your-api-key
```

**响应示例:**
```json
{
  "success": true,
  "files": [
    {
      "filename": "20240101_120000_uuid.jpg",
      "url": "https://noimnotahuman.top/image/20240101_120000_uuid.jpg",
      "size": 1024000,
      "modified_time": "2024-01-01T12:00:00"
    }
  ],
  "total": 1
}
```

#### 6. 获取配置信息

```http
GET /config
X-API-Key: your-api-key
```

**响应示例:**
```json
{
  "allowed_extensions": ["png", "jpg", "jpeg", "gif", "webp", "bmp"],
  "max_file_size": 10485760,
  "max_file_size_mb": 10,
  "has_api_keys": true
}
```

## 使用示例

### cURL 示例

```bash
# 上传图片
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -F "file=@image.jpg" \
  -F "optimize=true" \
  https://noimnotahuman.top/upload

# 删除图片
curl -X DELETE \
  -H "X-API-Key: your-api-key" \
  https://noimnotahuman.top/delete/filename.jpg

# 获取图片列表
curl -H "X-API-Key: your-api-key" \
  https://noimnotahuman.top/list
```

### JavaScript 示例

```javascript
// 上传图片
const uploadImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('optimize', 'true');

  const response = await fetch('https://noimnotahuman.top/upload', {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key'
    },
    body: formData
  });

  return await response.json();
};

// 删除图片
const deleteImage = async (filename) => {
  const response = await fetch(`https://noimnotahuman.top/delete/${filename}`, {
    method: 'DELETE',
    headers: {
      'X-API-Key': 'your-api-key'
    }
  });

  return await response.json();
};
```

### Python 示例

```python
import requests

# 上传图片
def upload_image(file_path, api_key):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'optimize': 'true'}
        headers = {'X-API-Key': api_key}
        
        response = requests.post(
            'https://noimnotahuman.top/upload',
            files=files,
            data=data,
            headers=headers
        )
        
        return response.json()

# 删除图片
def delete_image(filename, api_key):
    headers = {'X-API-Key': api_key}
    response = requests.delete(
        f'https://noimnotahuman.top/delete/{filename}',
        headers=headers
    )
    
    return response.json()
```

## 配置说明

### config/config.json

```json
{
  "allowed_origins": [
    "https://noimnotahuman.top",
    "https://www.noimnotahuman.top"
  ],
  "api_keys": [
    "your-secure-api-key-1",
    "your-secure-api-key-2"
  ],
  "max_file_size": 10485760,
  "allowed_extensions": ["png", "jpg", "jpeg", "gif", "webp", "bmp"]
}
```

**配置项说明:**
- `allowed_origins`: 允许跨域访问的域名列表
- `api_keys`: API 密钥列表（为空则不验证）
- `max_file_size`: 最大文件大小（字节）
- `allowed_extensions`: 允许的文件扩展名

### 环境变量

- `UPLOAD_FOLDER`: 上传目录路径（默认: `./uploads`）
- `CONFIG_PATH`: 配置文件目录（默认: `./config`）
- `PORT`: 服务端口（默认: `5000`）
- `DEBUG`: 调试模式（默认: `false`）

## Docker Compose 文件说明

项目包含多个Docker Compose配置文件，适用于不同场景：

| 文件 | 用途 | 特点 |
|------|------|------|
| `docker-compose.yml` | 开发/测试环境 | Flask直接暴露5000端口，配置简单 |
| `docker-compose.prod.yml` | 生产环境 | 安全配置，日志管理，监控支持 |
| `docker-compose.hub.yml` | Docker Hub镜像部署 | 使用预构建镜像，快速部署 |

## Docker Hub 镜像发布

### 1. 构建并推送镜像

```bash
# 编辑Docker Hub用户名
nano build-and-push.sh

# 登录Docker Hub
docker login

# 构建并推送镜像
chmod +x build-and-push.sh
./build-and-push.sh
```

### 2. 使用Docker Hub镜像部署

```bash
# 方式1：使用一键部署脚本
./quick-deploy.sh

# 方式2：使用Docker Hub配置文件
docker-compose -f docker-compose.hub.yml up -d

# 方式3：直接运行Docker命令
docker run -d \
  --name freepics \
  -p 5000:5000 \
  -v ./uploads:/app/uploads \
  -v ./config:/app/config \
  your-dockerhub-username/freepics:latest
```

## 目录结构

```
freepics/
├── app.py                    # 主应用文件
├── requirements.txt          # Python 依赖
├── Dockerfile               # Docker 镜像配置
├── docker-compose.yml       # 开发环境配置
├── docker-compose.prod.yml  # 生产环境配置
├── docker-compose.hub.yml   # Docker Hub镜像配置
├── nginx.conf               # Nginx 配置
├── deploy.sh                # 本地构建部署脚本
├── quick-deploy.sh          # 一键部署脚本（Docker Hub）
├── build-and-push.sh        # 镜像构建推送脚本
├── setup-ssl.sh             # SSL 设置脚本
├── test_api.py              # API 测试脚本
├── monitoring.sh            # 监控脚本
├── backup.sh                # 备份脚本
├── README.md                # 说明文档
├── .dockerignore            # Docker 忽略文件
├── config/                  # 配置目录（外挂）
│   └── config.json          # 主配置文件
├── uploads/                 # 上传目录（外挂）
└── ssl/                     # SSL 证书目录（外挂）
    ├── fullchain.pem
    └── privkey.pem
```

## 部署指南

### 系统要求

- Ubuntu 24.04 LTS
- Docker 20.10+
- Docker Compose 2.0+

### 详细部署步骤

1. **准备服务器**
   ```bash
   # 更新系统
   sudo apt update && sudo apt upgrade -y
   
   # 安装 Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # 安装 Docker Compose
   sudo apt install docker-compose-plugin
   ```

2. **配置域名**
   - 将域名 `noimnotahuman.top` 和 `www.noimnotahuman.top` 解析到服务器 IP

3. **部署服务**
   ```bash
   # 克隆项目
   git clone <repository-url>
   cd freepics
   
   # 配置服务
   nano config/config.json
   
   # 部署
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **配置 SSL**
   ```bash
   # 编辑邮箱地址
   nano setup-ssl.sh
   
   # 运行 SSL 设置
   ./setup-ssl.sh
   
   # 重启服务
   docker-compose restart
   ```

### 安全建议

1. **API 密钥管理**
   - 使用强密码生成器生成 API 密钥
   - 定期更换 API 密钥
   - 不要在客户端代码中硬编码 API 密钥

2. **访问控制**
   - 配置 `allowed_origins` 限制跨域访问
   - 使用防火墙限制服务器访问
   - 定期检查访问日志

3. **文件安全**
   - 定期备份上传的文件
   - 监控磁盘使用情况
   - 考虑实现文件扫描功能

## 故障排除

### 常见问题

1. **服务无法启动**
   ```bash
   # 查看日志
   docker-compose logs -f
   
   # 检查端口占用
   sudo netstat -tlnp | grep :80
   sudo netstat -tlnp | grep :443
   ```

2. **SSL 证书问题**
   ```bash
   # 检查证书文件
   ls -la ssl/
   
   # 重新获取证书
   ./setup-ssl.sh
   ```

3. **跨域访问被拒绝**
   - 检查 `config/config.json` 中的 `allowed_origins` 配置
   - 确保请求的 Origin 在白名单中

4. **文件上传失败**
   - 检查文件大小是否超过限制
   - 检查文件格式是否支持
   - 验证 API 密钥是否正确

### 日志查看

```bash
# 查看应用日志
docker-compose logs freepics

# 查看 Nginx 日志
docker-compose logs nginx

# 实时查看日志
docker-compose logs -f
```

## 更新和维护

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建和部署
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 备份数据

```bash
# 备份上传的文件
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/

# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/
```

## 许可证

MIT License

## 支持

如有问题或建议，请创建 Issue 或联系维护者。
