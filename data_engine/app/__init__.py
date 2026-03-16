from flask import Flask
from flask_caching import Cache
from app.config import Config
import os

cache = Cache()

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    # Khởi tạo Cache
    cache.init_app(app)

    # Đăng ký Blueprint
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    return app
