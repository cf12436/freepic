#!/bin/bash

# FreePics 一键部署脚本 - 支持Docker Hub镜像

set -e

# 配置
DOCKER_IMAGE="maomao12436/freepics:latest"  # 你的Docker Hub镜像
DOMAIN="noimnotahuman.top"  # 替换为你的域名
EMAIL="your-email@example.com"  # 替换为你的邮箱

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}   FreePics 一键部署脚本${NC}"
    echo -e "${BLUE}================================${NC}"
}

check_requirements() {
    print_info "检查系统要求..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_error "此脚本仅支持Linux系统"
        exit 1
    fi
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker未安装，正在安装..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_success "Docker安装完成"
    else
        print_success "Docker已安装"
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose未安装，正在安装..."
        sudo apt update
        sudo apt install -y docker-compose-plugin
        print_success "Docker Compose安装完成"
    else
        print_success "Docker Compose已安装"
    fi
}

create_project_structure() {
    print_info "创建项目目录结构..."
    
    # 创建必要的目录
    mkdir -p uploads config ssl logs/nginx
    
    # 创建默认配置文件
    if [ ! -f "config/config.json" ]; then
        cat > config/config.json << EOF
{
  "allowed_origins": [
    "https://$DOMAIN",
    "https://www.$DOMAIN",
    "http://localhost:3000"
  ],
  "api_keys": [
    "$(openssl rand -hex 32)"
  ],
  "max_file_size": 10485760,
  "allowed_extensions": ["png", "jpg", "jpeg", "gif", "webp", "bmp"]
}
EOF
        print_success "创建默认配置文件"
    fi
    
    # 创建nginx配置
    cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    upstream freepics_backend {
        server freepics:5000;
    }

    # HTTP服务器 - 重定向到HTTPS
    server {
        listen 80;
        server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        location / {
            proxy_pass http://freepics_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
            
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
            proxy_pass http://freepics_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location /health {
            proxy_pass http://freepics_backend/health;
            access_log off;
        }
    }
}
EOF
    
    # 替换域名占位符
    sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx.conf
    
    print_success "项目结构创建完成"
}

create_docker_compose() {
    print_info "创建Docker Compose配置..."
    
    cat > docker-compose.yml << EOF
version: '3.8'

services:
  freepics:
    image: $DOCKER_IMAGE
    container_name: freepics-server
    ports:
      - "127.0.0.1:5000:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./config:/app/config
      - ./ssl:/app/ssl
      - ./logs:/app/logs
    environment:
      - FLASK_ENV=production
      - UPLOAD_FOLDER=/app/uploads
      - CONFIG_PATH=/app/config
      - PORT=5000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: freepics-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - freepics
    restart: unless-stopped
EOF
    
    print_success "Docker Compose配置创建完成"
}

setup_ssl() {
    print_info "设置SSL证书..."
    
    # 检查是否安装了certbot
    if ! command -v certbot &> /dev/null; then
        print_info "安装certbot..."
        sudo apt update
        sudo apt install -y certbot python3-certbot-nginx
    fi
    
    # 临时启动nginx（仅HTTP）
    print_info "临时启动HTTP服务获取SSL证书..."
    docker run --rm -d --name temp-nginx -p 80:80 -v $(pwd)/nginx-temp.conf:/etc/nginx/nginx.conf nginx:alpine
    
    # 创建临时nginx配置
    cat > nginx-temp.conf << EOF
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name $DOMAIN www.$DOMAIN;
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location / {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
}
EOF
    
    # 获取SSL证书
    sudo certbot certonly --webroot \
        -w /var/lib/letsencrypt \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN \
        -d www.$DOMAIN
    
    # 停止临时nginx
    docker stop temp-nginx || true
    rm -f nginx-temp.conf
    
    # 复制证书
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./ssl/
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./ssl/
    sudo chown $USER:$USER ./ssl/*.pem
    sudo chmod 644 ./ssl/*.pem
    
    print_success "SSL证书设置完成"
}

deploy_service() {
    print_info "部署FreePics服务..."
    
    # 拉取最新镜像
    docker pull $DOCKER_IMAGE
    
    # 启动服务
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 15
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        print_success "服务部署成功！"
        
        # 显示API密钥
        api_key=$(cat config/config.json | grep -o '"[^"]*"' | sed -n '4p' | tr -d '"')
        
        echo ""
        echo -e "${GREEN}🎉 FreePics 图床服务部署完成！${NC}"
        echo ""
        echo -e "${BLUE}服务信息:${NC}"
        echo "- 域名: https://$DOMAIN"
        echo "- API密钥: $api_key"
        echo ""
        echo -e "${BLUE}API端点:${NC}"
        echo "- 上传图片: POST https://$DOMAIN/upload"
        echo "- 删除图片: DELETE https://$DOMAIN/delete/<filename>"
        echo "- 访问图片: GET https://$DOMAIN/image/<filename>"
        echo "- 健康检查: GET https://$DOMAIN/health"
        echo ""
        echo -e "${BLUE}管理命令:${NC}"
        echo "- 查看日志: docker-compose logs -f"
        echo "- 重启服务: docker-compose restart"
        echo "- 停止服务: docker-compose down"
        echo ""
        
    else
        print_error "服务部署失败，请检查日志:"
        docker-compose logs
        exit 1
    fi
}

main() {
    print_header
    
    # 检查参数
    if [ "$1" = "--skip-ssl" ]; then
        SKIP_SSL=true
        print_warning "跳过SSL设置，仅部署HTTP服务"
    fi
    
    check_requirements
    create_project_structure
    create_docker_compose
    
    if [ "$SKIP_SSL" != "true" ]; then
        setup_ssl
    else
        # 创建自签名证书用于测试
        mkdir -p ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout ssl/privkey.pem \
            -out ssl/fullchain.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    fi
    
    deploy_service
}

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "FreePics 一键部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --skip-ssl    跳过SSL设置，仅部署HTTP服务"
    echo "  --help, -h    显示此帮助信息"
    echo ""
    echo "部署前请确保:"
    echo "1. 修改脚本中的DOCKER_IMAGE、DOMAIN和EMAIL变量"
    echo "2. 域名已正确解析到服务器IP"
    echo "3. 服务器防火墙已开放80和443端口"
    exit 0
fi

main "$@"
