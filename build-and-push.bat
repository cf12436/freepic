@echo off
REM Docker Hub 镜像构建和推送脚本 (Windows版本)

setlocal enabledelayedexpansion

REM 配置
set DOCKER_USERNAME=maomao12436
set IMAGE_NAME=freepics
set VERSION=latest
set FULL_IMAGE_NAME=%DOCKER_USERNAME%/%IMAGE_NAME%:%VERSION%

echo [INFO] 开始构建Docker镜像: %FULL_IMAGE_NAME%

REM 检查Docker是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker未运行或未安装，请启动Docker Desktop
    pause
    exit /b 1
)

REM 构建镜像
echo [INFO] 构建镜像中...
docker build -t %FULL_IMAGE_NAME% .

if errorlevel 1 (
    echo [ERROR] 镜像构建失败
    pause
    exit /b 1
)

echo [SUCCESS] 镜像构建成功

REM 推送到Docker Hub
echo [INFO] 推送镜像到Docker Hub...
docker push %FULL_IMAGE_NAME%

if errorlevel 1 (
    echo [ERROR] 镜像推送失败，请检查是否已登录Docker Hub
    echo 运行: docker login
    pause
    exit /b 1
)

echo [SUCCESS] 镜像推送成功
echo [INFO] 镜像地址: https://hub.docker.com/r/%DOCKER_USERNAME%/%IMAGE_NAME%
echo [INFO] 拉取命令: docker pull %FULL_IMAGE_NAME%

echo [SUCCESS] Docker Hub 镜像发布完成！
pause
