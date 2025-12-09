# Docker Hub Proxy & Mirror Manager

一个轻量级、智能的 Docker 镜像加速与代理管理工具。

它提供了一个现代化的 Web UI，用于管理上游镜像源（Mirrors），支持自动测速、延迟择优、流量统计以及一键获取免费代理节点。旨在解决国内拉取 Docker 镜像慢、超时等问题。

## ✨ 功能特性

*   **⚡️ 智能路由与加速**：
    *   定期对所有代理节点进行**自动测速**。
    *   拉取镜像时，自动选择**延迟最低**的可用节点。
    *   超时自动熔断：如果节点超时（>10s），自动标记为不可用，待恢复后自动启用。
*   **🌐 多源支持**：
    *   不仅支持 **Docker Hub**，还支持 **GHCR** (GitHub), **GCR** (Google), **Quay**, **K8s** 等镜像仓库的代理。
    *   支持自定义路由前缀（如 `/ghcr/` 转发到 `ghcr.io`）。
*   **🔐 私有仓库免密拉取**：
    *   针对需要认证的私有仓库（如 Harbor、自建 Registry），支持在后台动态配置账号密码。
    *   配置后，Proxy 会自动接管上游认证逻辑，**本地客户端无需执行 `docker login`** 即可直接拉取受保护的镜像。
*   **🆓 一键获取节点**：
    *   内置爬虫功能，可一键从网络（基于 `anye.xyz`）抓取市面上免费、公开的镜像加速源。
    *   自动过滤付费、内网专用或需登录的节点。
    *   支持后台定时任务自动更新节点列表（每小时）。
*   **📊 流量与统计**：
    *   记录拉取历史、客户端 IP、镜像 Tag。
    *   实时展示总流量消耗与请求统计。
*   **🖥 现代化 UI**：
    *   提供镜像搜索功能（代理 Docker Hub 官方搜索）。
    *   生成详细的 `docker pull` 命令提示。
![img.png](img/img.png)
![img_1.png](img/img_1.png)
## 🚀 快速开始

### 方式一：Docker Compose (推荐)

1.  克隆本项目：
    ```bash
    git clone <repository_url>
    cd docker-hub
    ```

2.  启动服务：
    ```bash
    docker-compose up -d
    ```

3.  访问 Web UI：
    打开浏览器访问 `http://localhost:8000`

### 方式二：手动运行 (Python)

需要 Python 3.9+ 环境。

1.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

2.  运行服务：
    ```bash
    # 使用启动脚本
    sh start.sh
    
    # 或者直接运行 python
    python app/main.py
    ```

## 📖 使用指南

### 1. 配置 Docker 客户端 (推荐)

为了让 Docker 守护进程自动使用此代理，请修改 `/etc/docker/daemon.json` (Linux) 或 Docker Desktop 设置。

```json
{
  "registry-mirrors": [
    "http://<你的服务器IP>:8000"
  ]
}
```
*重启 Docker 后生效。*

### 2. 手动拉取 (命令行)

你也可以直接在命令行中指定代理地址进行拉取。点击 Web UI 列表中的 **(?)** 图标可查看具体命令。

*   **Docker Hub 官方镜像**:
    ```bash
    docker pull <服务器IP>:8000/library/nginx:latest
    docker pull <服务器IP>:8000/mysql:8.0
    ```

*   **GHCR (GitHub Container Registry)**:
    如果配置了前缀为 `ghcr` 的节点：
    ```bash
    docker pull <服务器IP>:8000/ghcr/owner/image:tag
    ```

*   **Quay.io**:
    如果配置了前缀为 `quay` 的节点：
    ```bash
    docker pull <服务器IP>:8000/quay/coreos/etcd:latest
    ```

## 🛠 配置说明

*   **端口**: 默认为 `8000`。
*   **数据库**: 使用 SQLite，数据存储在 `database.db`。
*   **定时任务**:
    *   **测速**: 每 60 分钟运行一次。
    *   **节点更新**: 每 60 分钟运行一次。

## 📂 项目结构

```
.
├── app/
│   ├── main.py            # 程序入口
│   ├── models.py          # 数据库模型
│   ├── database.py        # 数据库连接
│   ├── services/
│   │   ├── proxy_manager.py  # 核心逻辑：代理管理、测速、抓取
│   │   └── traffic_logger.py # 流量统计
│   ├── routers/
│   │   ├── web_ui.py         # 前端 API
│   │   └── docker_proxy.py   # Docker 代理拦截核心
│   └── templates/
│       └── index.html        # 前端页面
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📝 License

MIT License
