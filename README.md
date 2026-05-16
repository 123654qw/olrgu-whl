# olrgu

局域网文件分享工具。选个文件夹，输个端口，局域网内任意设备用浏览器访问即可。

---

## 功能

| 功能 | 说明 |
|------|------|
| 共享方式 | 选择文件夹或单个文件 |
| 端口 | 自定义四位数字（默认 8000）|
| 密码保护 | 可选，六位以内数字 |
| 在线预览 | 图片 / 文本 / PDF |
| 实例限制 | 最多同时运行 2 个服务 |

---

## 安装

**方式一：直接安装 wheel（推荐）**

```bash
pip install E:\PC\olrgu-whl\dist\olrgu-1.0.0-py3-none-any.whl
```

**方式二：从源码构建**

```bash
cd E:\PC\olrgu-whl
pip install build
python -m build
pip install dist\olrgu-1.0.0-py3-none-any.whl
```

**依赖：** Python 3.8+，`customtkinter>=5.2.0`（自动安装）

---

## 运行

安装完成后，任选一种方式启动：

```bash
# 方式一：命令行直接运行（GUI 模式）
olrgu

# 方式二：模块方式运行（GUI 模式）
python -m olrgu
```

---

## 纯代码 API

不想要 GUI？几行代码即可启动文件分享服务：

```python
import olrgu

# 最简用法：共享当前目录，阻塞运行（Ctrl+C 停止）
olrgu.share()

# 指定路径和端口
olrgu.share(r"E:\共享文件夹", port=8000)

# 密码保护
olrgu.share(r"E:\共享文件夹", port=8000, password="123456")

# 后台运行，返回 Server 对象
server = olrgu.share(r"E:\共享文件夹", port=8000, block=False)
print(server.url)        # 本地访问地址
print(server.lan_url)    # 局域网访问地址
# ... 做其他事情 ...
server.stop()            # 停止服务
```

**API 说明：**

| 函数/类 | 说明 |
|---------|------|
| `olrgu.share(path, port, password, block)` | 快速启动，`block=False` 时返回 Server |
| `olrgu.Server(path, port, password)` | 服务器控制对象 |
| `server.start(block=True)` | 启动服务 |
| `server.stop()` | 停止服务 |
| `server.url` | 本地访问地址 |
| `server.lan_url` | 局域网访问地址 |

---

## 使用步骤

1. **选择共享内容** — 点击「选择文件夹」或「选择文件」
2. **设置端口** — 输入四位数字（如 8000，默认已填写）
3. **设置密码（可选）** — 留空则无需密码直接访问
4. **启动服务** — 点击「启动服务」
5. **访问** — 用局域网内任意设备的浏览器访问显示的地址

```
本地访问:  http://localhost:端口
局域网访问: http://你的IP:端口
```

点击「打开浏览器」可快速在本地浏览器中打开。

---

## 支持预览的格式

| 类型 | 格式 |
|------|------|
| 图片 | jpg, jpeg, png, gif, webp |
| 文本 | txt, md, json, xml, html, css, js, py |
| 文档 | pdf |

不支持预览的格式可直接下载。

---

## 注意事项

- 防火墙需放行对应端口，否则局域网其他设备无法访问
- 密码保护仅为基础访问控制，不适用于高安全场景
- 停止服务：点击「停止服务」或直接关闭窗口
- 端口被占用时会提示更换，不会覆盖已有服务

---

## 技术栈

- Python 3.8+ / CustomTkinter（深色 UI）
- Python HTTPServer（内置，无额外依赖）
- 打包为 wheel，支持 `pip install`
