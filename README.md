# Docker Hub Proxy & Mirror Manager

一个轻量级、智能的 Docker 镜像加速与代理管理工具。

它提供了一个现代化的 Web UI，用于管理上游镜像源（Mirrors），支持自动测速、延迟择优、流量统计以及一键获取免费代理节点。旨在解决国内拉取 Docker 镜像慢、超时等问题。

## ✨ 功能特性

*   **⚡️ 智能路由与加速**：
    *   定期对所有代理节点进行**自动测速**，并在拉取镜像时自动选择**延迟最低**的可用节点。
    *   支持**部分测速**和异步并发测速，实时在前端展示每个节点的测速状态。
    *   超时自动熔断：如果节点超时（>10s），自动标记为不可用，待恢复后自动启用。
*   **🌐 多源支持与快速筛选**：
    *   不仅支持 **Docker Hub**，还支持 **GHCR** (GitHub), **GCR** (Google), **Quay**, **K8s** 等镜像仓库的代理。
    *   提供前端 Tab 页快速分类切换，支持节点列表分页。
    *   支持自定义路由前缀（如 `/ghcr/` 转发到 `ghcr.io`）。
*   **🔐 访问管控与安全 (增强)**：
    *   **Web UI 鉴权**：支持通过配置 `ADMIN_USER` 和 `ADMIN_PASS` 保护控制面板。
    *   **IP 白名单**：支持配置 `IP_WHITELIST` 限制仅允许特定 IP 进行拉取，防止公网被刷流量滥用。
    *   **镜像过滤**：支持基于正则表达式的黑白名单（`IMAGE_WHITELIST_REGEX`, `IMAGE_BLACKLIST_REGEX`），精准控制允许代理拉取的镜像范围。
    *   **私有仓库免密**：配置账号密码后，本地客户端无需执行 `docker login` 即可直接拉取上游受保护的镜像。
*   **🆓 节点管理**：
    *   **一键获取免费节点**：内置爬虫功能，一键抓取网络上免费公开的加速源。
    *   **导入/导出配置**：支持将现有的节点列表一键导出为 JSON 文件，并支持快速导入备份。
*   **📊 流量可视化**：
    *   集成 **ECharts**，直观展示近 7 天流量消耗趋势折线图。
    *   记录详细的拉取历史（包含时间、镜像、标签、客户端 IP）。

## 🚀 快速开始

### 方式一：Docker Compose (推荐)

1.  克隆本项目：
    ```bash
    git clone https://github.com/xingfeng7788/docker-hub-proxy.git
    cd docker-hub-proxy
    ```

2.  配置环境变量（可选）：
    ```bash
    cp .env.example .env
    # 编辑 .env 修改面板密码、限制 IP 等
    ```

3.  启动服务：
    ```bash
    docker-compose up -d
    ```

4.  访问 Web UI：
    打开浏览器访问 `http://localhost:8000`

### 方式二：手动运行 (Python)

需要 Python 3.9+ 环境。

1.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

2.  配置与运行：
    ```bash
    cp .env.example .env
    # 编辑 .env 文件
    
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

## 🛠 配置说明 (.env)

项目支持通过 `.env` 文件或环境变量进行高度定制：

| 变量名 | 说明 | 默认值 |
|---|---|---|
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8000` |
| `ADMIN_USER` | Web 面板登录账号（留空则公开免密） | 空 |
| `ADMIN_PASS` | Web 面板登录密码 | 空 |
| `IP_WHITELIST` | 允许拉取的 IP 白名单 (多个用逗号分隔) | 空 (允许所有) |
| `IMAGE_WHITELIST_REGEX` | 允许拉取镜像的正则白名单 | 空 (不限制) |
| `IMAGE_BLACKLIST_REGEX` | 禁止拉取镜像的正则黑名单 | 空 (不限制) |
| `PROXY_TIMEOUT` | 测速与转发的超时时间 (秒) | `10.0` |

## 📂 项目结构

```
.
├── app/
│   ├── config.py          # 环境变量与配置管理
│   ├── main.py            # 程序入口
│   ├── models.py          # 数据库模型
│   ├── database.py        # 数据库连接
│   ├── services/          # 核心业务逻辑 (测速、代理策略等)
│   ├── routers/           # API 接口与路由
│   └── templates/         # 前端 Vue 页面
├── data/                  # SQLite 数据文件存储目录
├── .env.example           # 环境变量示例文件
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📝 License

MIT License
