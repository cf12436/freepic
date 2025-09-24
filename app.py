from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import hashlib
from datetime import datetime
import json
import logging
from werkzeug.utils import secure_filename
from PIL import Image
import io

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置文件路径
CONFIG_PATH = os.getenv('CONFIG_PATH', './config')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONFIG_PATH, exist_ok=True)

def load_config():
    """加载配置文件"""
    config_file = os.path.join(CONFIG_PATH, 'config.json')
    default_config = {
        "allowed_origins": ["*"],
        "api_keys": [],
        "max_file_size": MAX_FILE_SIZE,
        "allowed_extensions": list(ALLOWED_EXTENSIONS)
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            # 创建默认配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return default_config

# 加载配置
config = load_config()

# 配置CORS
CORS(app, origins=config.get('allowed_origins', ['*']))

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.get('allowed_extensions', ALLOWED_EXTENSIONS)

def verify_api_key():
    """验证API密钥"""
    api_keys = config.get('api_keys', [])
    if not api_keys:  # 如果没有配置API密钥，则不验证
        return True
    
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    return api_key in api_keys

def generate_filename(original_filename):
    """生成唯一的文件名"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{unique_id}.{ext}"

def optimize_image(image_data, max_size=(1920, 1080), quality=85):
    """优化图片大小和质量"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # 如果图片过大，进行缩放
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 转换为RGB模式（如果需要）
        if image.mode in ('RGBA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # 保存优化后的图片
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except Exception as e:
        logger.error(f"图片优化失败: {e}")
        return image_data

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """上传图片接口"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'不支持的文件类型，支持的格式: {", ".join(config.get("allowed_extensions", ALLOWED_EXTENSIONS))}'
            }), 400
        
        # 检查文件大小
        file_data = file.read()
        if len(file_data) > config.get('max_file_size', MAX_FILE_SIZE):
            return jsonify({'error': f'文件大小超过限制 ({config.get("max_file_size", MAX_FILE_SIZE) // 1024 // 1024}MB)'}), 400
        
        # 生成文件名
        filename = generate_filename(secure_filename(file.filename))
        
        # 优化图片（可选）
        optimize = request.form.get('optimize', 'false').lower() == 'true'
        logger.info(f"上传文件: {file.filename}, 大小: {len(file_data)}, 优化: {optimize}")
        
        if optimize and file.content_type and file.content_type.startswith('image/'):
            try:
                original_size = len(file_data)
                file_data = optimize_image(file_data)
                logger.info(f"图片优化: {original_size} -> {len(file_data)} bytes")
            except Exception as e:
                logger.warning(f"图片优化失败，使用原图: {e}")
                # 继续使用原始图片数据
        
        # 保存文件
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        logger.info(f"保存文件到: {file_path}")
        
        try:
            # 确保上传目录存在
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"文件保存成功: {filename}")
            
        except Exception as e:
            logger.error(f"文件保存失败: {e}", exc_info=True)
            return jsonify({'error': f'文件保存失败: {str(e)}'}), 500
        
        # 生成访问URL
        base_url = request.url_root.rstrip('/')
        file_url = f"{base_url}/image/{filename}"
        
        # 计算文件哈希
        file_hash = hashlib.md5(file_data).hexdigest()
        
        logger.info(f"文件上传成功: {filename}")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': file_url,
            'size': len(file_data),
            'hash': file_hash,
            'upload_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        return jsonify({'error': f'文件上传失败: {str(e)}'}), 500

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """删除图片接口"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        # 安全检查文件名
        filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 删除文件
        os.remove(file_path)
        
        logger.info(f"文件删除成功: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 删除成功',
            'delete_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"文件删除失败: {e}")
        return jsonify({'error': '文件删除失败'}), 500

@app.route('/image/<filename>')
def serve_image(filename):
    """提供图片访问接口"""
    try:
        filename = secure_filename(filename)
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        logger.error(f"图片访问失败: {e}")
        return jsonify({'error': '图片不存在'}), 404

@app.route('/list', methods=['GET'])
def list_files():
    """列出所有图片接口（管理用）"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        files = []
        base_url = request.url_root.rstrip('/')
        
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    'filename': filename,
                    'url': f"{base_url}/image/{filename}",
                    'size': stat.st_size,
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        }), 200
        
    except Exception as e:
        logger.error(f"文件列表获取失败: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500

@app.route('/config', methods=['GET'])
def get_config():
    """获取配置信息（不包含敏感信息）"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        safe_config = {
            'allowed_extensions': config.get('allowed_extensions', list(ALLOWED_EXTENSIONS)),
            'max_file_size': config.get('max_file_size', MAX_FILE_SIZE),
            'max_file_size_mb': config.get('max_file_size', MAX_FILE_SIZE) // 1024 // 1024,
            'has_api_keys': len(config.get('api_keys', [])) > 0
        }
        
        return jsonify(safe_config), 200
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return jsonify({'error': '获取配置失败'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"图床服务启动中...")
    logger.info(f"上传目录: {UPLOAD_FOLDER}")
    logger.info(f"配置目录: {CONFIG_PATH}")
    logger.info(f"端口: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
