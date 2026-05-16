"""olrgu - 局域网文件分享工具"""
__version__ = "1.0.0"
__author__ = "yuanbao"

from .app import OlrguApp, Server, share

__all__ = ["OlrguApp", "Server", "share", "__version__"]
