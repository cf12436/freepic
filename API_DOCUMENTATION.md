# FreePics 图床服务 API 文档

## 概述

FreePics 是一个轻量级的图床服务，提供图片上传、访问、管理等功能。支持多种图片格式，具备图片优化、API密钥验证等特性。

- **服务地址**: `http://noimnotahuman.top`
- **版本**: v1.0.0
- **支持格式**: PNG, JPG, JPEG, GIF, WebP, BMP
- **最大文件大小**: 10MB

## 认证

部分接口需要API密钥验证。在请求头中添加：

```
X-API-Key: your-api-key-here
```

## 接口列表

### 1. 健康检查

检查服务状态和基本信息。

**请求**
```
GET /health
```

**响应**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-24T10:47:01.249917",
  "version": "1.0.0"
}
```

**状态码**
- `200` - 服务正常

---

### 2. 获取配置信息

获取服务配置信息，包括支持的文件格式、大小限制等。

**请求**
```
GET /config
```

**响应**
```json
{
  "allowed_extensions": [
    "jpeg",
    "bmp", 
    "webp",
    "jpg",
    "gif",
    "png"
  ],
  "has_api_keys": false,
  "max_file_size": 10485760,
  "max_file_size_mb": 10
}
```

**状态码**
- `200` - 获取成功
- `401` - 需要API密钥（如果配置了密钥验证）

---

### 3. 上传图片

上传图片文件到服务器。

**请求**
```
POST /upload
Content-Type: multipart/form-data
X-API-Key: your-api-key-here (如果需要)

file: [图片文件]
optimize: true/false (可选，是否优化图片)
```

**请求示例 (curl)**
```bash
curl -X POST http://noimnotahuman.top/upload \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@image.jpg" \
  -F "optimize=true"
```

**请求示例 (Python)**
```python
import requests

url = "http://noimnotahuman.top/upload"
headers = {"X-API-Key": "your-api-key-here"}
files = {"file": open("image.jpg", "rb")}
data = {"optimize": "true"}

response = requests.post(url, headers=headers, files=files, data=data)
```

**响应**
```json
{
  "success": true,
  "filename": "20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg",
  "url": "http://noimnotahuman.top/image/20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg",
  "size": 7266,
  "hash": "a0490e5be8ba2866ae3e7aea126b0ac5",
  "upload_time": "2025-09-24T10:47:02.079025"
}
```

**状态码**
- `200` - 上传成功
- `400` - 请求错误（文件格式不支持、文件过大等）
- `401` - 需要API密钥
- `500` - 服务器错误

**错误响应示例**
```json
{
  "error": "不支持的文件类型，支持的格式: png, jpg, jpeg, gif, webp, bmp"
}
```

---

### 4. 访问图片

通过文件名访问已上传的图片。

**请求**
```
GET /image/{filename}
```

**参数**
- `filename` - 图片文件名（上传时返回的filename）

**请求示例**
```
GET /image/20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg
```

**响应**
- 直接返回图片文件内容
- Content-Type: image/jpeg (根据文件类型)

**状态码**
- `200` - 访问成功
- `404` - 文件不存在

---

### 5. 获取文件列表

获取已上传的文件列表。

**请求**
```
GET /list
X-API-Key: your-api-key-here
```

**响应**
```json
{
  "success": true,
  "total": 1,
  "files": [
    {
      "filename": "20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg",
      "size": 7266,
      "upload_time": "2025-09-24T10:47:02.079025",
      "url": "http://noimnotahuman.top/image/20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg"
    }
  ]
}
```

**状态码**
- `200` - 获取成功
- `401` - 需要API密钥

---

### 6. 删除图片

删除指定的图片文件。

**请求**
```
DELETE /delete/{filename}
X-API-Key: your-api-key-here
```

**参数**
- `filename` - 要删除的图片文件名

**请求示例 (curl)**
```bash
curl -X DELETE http://noimnotahuman.top/delete/20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg \
  -H "X-API-Key: your-api-key-here"
```

**响应**
```json
{
  "success": true,
  "message": "文件 20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg 删除成功",
  "delete_time": "2025-09-24T10:47:07.489888"
}
```

**状态码**
- `200` - 删除成功
- `401` - 需要API密钥
- `404` - 文件不存在
- `500` - 删除失败

---

### 7. 批量删除所有图片

一次性删除服务器上的所有图片文件。

**请求**
```
DELETE /delete-all
X-API-Key: your-api-key-here
```

**请求示例 (curl)**
```bash
curl -X DELETE http://noimnotahuman.top/delete-all \
  -H "X-API-Key: your-api-key-here"
```

**响应**
```json
{
  "success": true,
  "message": "批量删除完成: 成功删除 5 个文件",
  "deleted_count": 5,
  "failed_count": 0,
  "deleted_files": [
    "20250924_104702_5adc6a68-c4cb-49f3-823f-5ac22b55afae.jpg",
    "20250924_105030_b1e2f3a4-d5c6-47e8-9f0a-1b2c3d4e5f6g.png",
    "20250924_105145_c2f3g4h5-i6j7-48k9-al1m-2n3o4p5q6r7s.gif"
  ],
  "delete_time": "2025-09-25T08:15:30.123456"
}
```

**错误响应示例（部分文件删除失败）**
```json
{
  "success": true,
  "message": "批量删除完成: 成功删除 3 个文件，2 个文件删除失败",
  "deleted_count": 3,
  "failed_count": 2,
  "deleted_files": [
    "file1.jpg",
    "file2.png",
    "file3.gif"
  ],
  "failed_files": [
    {
      "filename": "file4.jpg",
      "error": "Permission denied"
    },
    {
      "filename": "file5.png", 
      "error": "File is locked"
    }
  ],
  "delete_time": "2025-09-25T08:15:30.123456"
}
```

**状态码**
- `200` - 批量删除完成（包括部分失败的情况）
- `401` - 需要API密钥
- `500` - 批量删除失败

**注意事项**
- 此操作不可逆，请谨慎使用
- 如果上传目录不存在，会返回成功状态
- 即使部分文件删除失败，也会返回200状态码，需要检查响应中的详细信息

---

## 错误处理

所有错误响应都采用统一格式：

```json
{
  "error": "错误描述信息"
}
```

常见错误：
- `没有选择文件` - 上传请求中缺少文件
- `不支持的文件类型` - 文件格式不在支持列表中
- `文件大小超过限制` - 文件超过10MB限制
- `无效的API密钥` - API密钥验证失败
- `文件不存在` - 访问或删除不存在的文件

## 使用示例

### JavaScript (Fetch API)

```javascript
// 上传图片
async function uploadImage(file, apiKey) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('optimize', 'true');
  
  const response = await fetch('http://noimnotahuman.top/upload', {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey
    },
    body: formData
  });
  
  return await response.json();
}

// 删除图片
async function deleteImage(filename, apiKey) {
  const response = await fetch(`http://noimnotahuman.top/delete/${filename}`, {
    method: 'DELETE',
    headers: {
      'X-API-Key': apiKey
    }
  });
  
  return await response.json();
}

// 批量删除所有图片
async function deleteAllImages(apiKey) {
  const response = await fetch('http://noimnotahuman.top/delete-all', {
    method: 'DELETE',
    headers: {
      'X-API-Key': apiKey
    }
  });
  
  return await response.json();
}
```

### Python (requests)

```python
import requests

class FreePicsClient:
    def __init__(self, base_url="http://noimnotahuman.top", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
    
    def upload_image(self, file_path, optimize=True):
        """上传图片"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'optimize': 'true' if optimize else 'false'}
            response = self.session.post(f"{self.base_url}/upload", 
                                       files=files, data=data)
        return response.json()
    
    def get_file_list(self):
        """获取文件列表"""
        response = self.session.get(f"{self.base_url}/list")
        return response.json()
    
    def delete_image(self, filename):
        """删除图片"""
        response = self.session.delete(f"{self.base_url}/delete/{filename}")
        return response.json()
    
    def delete_all_images(self):
        """批量删除所有图片"""
        response = self.session.delete(f"{self.base_url}/delete-all")
        return response.json()

# 使用示例
client = FreePicsClient(api_key="your-api-key-here")
result = client.upload_image("image.jpg")
print(f"上传成功: {result['url']}")

# 批量删除示例
delete_result = client.delete_all_images()
print(f"删除了 {delete_result['deleted_count']} 个文件")
```

## 注意事项

1. **文件命名**: 上传的文件会自动重命名为带时间戳和UUID的格式，确保唯一性
2. **图片优化**: 启用优化后，图片会被压缩和调整尺寸以节省存储空间
3. **跨域访问**: 服务支持CORS，可在前端直接调用
4. **API密钥**: 根据服务配置，可能需要API密钥才能访问某些接口
5. **文件存储**: 文件存储在服务器的Docker数据卷中，重启服务不会丢失

## 部署信息

- **Docker镜像**: `maomao12436/freepics:latest`
- **端口**: 5000 (内部), 80 (外部)
- **数据持久化**: 使用Docker数据卷
- **反向代理**: Nginx

## 更新日志

### v1.0.0 (2025-09-24)
- 初始版本发布
- 支持图片上传、访问、删除功能
- 支持多种图片格式
- 集成图片优化功能
- API密钥验证
- Docker一键部署
