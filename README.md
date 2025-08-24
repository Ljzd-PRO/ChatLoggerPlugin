# Chat Logger

### 概述
ChatLoggerPlugin 是一个 LangBot 插件，用于将群聊消息和机器人回复内容记录到数据库。它支持多种数据库，能自由配置群聊黑白名单过滤，便于个性化管理和多场景应用。

### 功能特色
- **多数据库支持**：兼容 SQLite、PostgreSQL、MySQL 及其他 SQLAlchemy 支持的数据库。
- **群组选择性记录**：可通过白名单/黑名单灵活选择记录哪些群组。
- **机器人消息控制**：可配置是否记录机器人的回复消息。
- **自动结构管理**：自动创建所需的数据库表，无需手动操作。
- **异步操作**：所有数据库操作均为异步，确保系统高性能。
- **信息完整记录**：记录用户ID、昵称、消息内容、时间戳和群组标识等信息。
  - 目前不包含图片

### 安装步骤
1. 在 LangBot WebUI 中安装，或使用管理员账号向机器人发送命令：
   ```
   !plugin get https://github.com/Ljzd-PRO/ChatLoggerPlugin
   ```

2. 安装所需依赖（选择您的数据库类型安装相关驱动）
   - 修改 LangBot 安装目录下的 `plugins/ChatLoggerPlugin/requirements.txt` 依赖文件
     - 不需要的驱动可以注释掉
   ```requirements.txt
   # ORM 框架，默认已包含，无需在意
   sqlalchemy[asyncio]

   # SQLite 驱动（默认）
   aiosqlite

   # PostgreSQL 驱动
   asyncpg

   # MySQL 驱动
   aiomysql
   ```

3. 重启 LangBot，依赖自动安装

### 配置方法
请在 LangBot WebUI 中配置

#### 常见数据库连接地址示例
- **SQLite**：`sqlite+aiosqlite:///./chat_logs.db`
- **PostgreSQL**：`postgresql+asyncpg://用户名:密码@主机:端口/数据库名`
  - 使用 `public` 架构（Schema）
- **MySQL**：`mysql+aiomysql://用户名:密码@主机:端口/数据库名`

### 数据库结构说明
插件会自动创建一个名为 `chat_records` 的表，其结构如下：

```sql
CREATE TABLE group_msg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datetime DATETIME,
    user_id TEXT NOT NULL,
    nickname TEXT,
    message TEXT,
    group_id TEXT NOT NULL
);

```

### 常见问题排查
1. **数据库连接失败**：请确认连接URL格式和帐号密码是否正确。
3. **依赖缺失**：请根据所用数据库安装正确的驱动（aiosqlite、asyncpg、aiomysql）。
4. **插件无法加载**：检查插件配置是否正确。

### 技术支持
如有疑问或需帮助，请访问 [GitHub 仓库](https://github.com/Ljzd-PRO/ChatLoggerPlugin) 反馈 Issue 或查阅相关文档。
