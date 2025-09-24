#!/bin/bash

# SSL证书设置脚本
# 使用Let's Encrypt获取免费SSL证书

DOMAIN="noimnotahuman.top"
EMAIL="your-email@example.com"  # 请替换为你的邮箱

echo "开始设置SSL证书..."

# 检查是否安装了certbot
if ! command -v certbot &> /dev/null; then
    echo "安装certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# 创建SSL目录
sudo mkdir -p ./ssl

# 获取证书（使用standalone模式，需要先停止nginx）
echo "获取SSL证书..."
sudo certbot certonly --standalone \
    --preferred-challenges http \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# 复制证书到项目目录
echo "复制证书文件..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./ssl/
sudo chown $USER:$USER ./ssl/*.pem
sudo chmod 644 ./ssl/*.pem

# 设置证书自动续期
echo "设置证书自动续期..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose restart nginx'") | crontab -

echo "SSL证书设置完成！"
echo "证书文件已复制到 ./ssl/ 目录"
echo "请确保在docker-compose.yml中正确挂载SSL目录"
