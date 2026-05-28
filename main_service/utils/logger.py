import logging
import sys
from pathlib import Path
from config.settings import Settings


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """设置日志记录器"""

    # 创建日志目录
    log_dir = Settings.LOG_DIR/Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 创建记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 如果记录器已经有处理器，直接返回
    if logger.handlers:
        return logger

    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 文件处理器
    file_handler = logging.FileHandler(log_dir / f"{name}.log", encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
