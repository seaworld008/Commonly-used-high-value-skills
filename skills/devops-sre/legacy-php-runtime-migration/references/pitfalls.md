# 踩坑记录

每条按"现象 → 原因 → 处理"写，处理方法都已在实际迁移中用过。前 17 条出现在测试主机上，后 15 条出现在生产主机上。

## 容器与转发脚本

| # | 现象 | 原因 | 处理 |
|---|---|---|---|
| 1 | 用 `bash -s` 远程执行的脚本，跑到第一个 `php` 就结束了 | `docker exec -i` 把调用方的标准输入全部读走，原生 php 不会这样 | 转发脚本只在交互终端下加 `-i`；需要管道输入时显式设置 `PHP72_STDIN=1`。否则 `while read …; do php …; done < 文件` 这类写法也会出错 |
| 2 | 脚本开头写了 `exec < /dev/null`，经 `bash -s` 执行时一行都没跑 | 脚本本身就是从标准输入读进来的 | 关闭标准输入的脚本要以文件方式执行 |
| 3 | 容器里的 memory_limit、上传上限、时区与宿主机不同 | 基础镜像自带的生产配置片段覆盖了 php.ini | 在镜像里删除这个片段 |
| 4 | 差异清单里出现 `msgpack.assoc`（宿主机为空，容器为 1） | 宿主机的 msgpack 2.x 没有这个指令，它是 3.0 新增的，默认值与 2.x 的行为一致 | 不能写成 Off，否则 map 会被解包成对象。"只有新环境才有"的指令只提示、不写入 |
| 5 | 关闭 sodium 时提示 ini 文件不存在 | sodium 编译在主程序里 | 接受这个差异，只是多出一组函数 |
| 6 | 容器 FPM 里加载了 readline | 发行版对所有 SAPI 都启用了它 | 只在 fpm 上关闭 |
| 7 | CLI 的 `session.save_path` 和两个 MySQL socket 默认值与宿主机不同 | 两边编译时的默认值不同 | 写进补齐文件 |
| 8 | 补齐文件的挂载点变成了目录 | 挂载时宿主机上还没有这个文件，docker 自动建了同名目录 | 挂载前先确认源文件存在 |
| 11 | `supervisorctl pid` 给出的进程号在宿主机上对不上 | 这是容器内的 PID | 用 `docker top php72-cli` 对应 |
| 18 | FPM 以错误的 uid 运行，或者容器起不来（`groupadd` 报错） | 镜像自带 nginx 999、application 1000 等账号，旧入口脚本遇到已存在的账号就跳过 | 入口脚本先删除与宿主机账号同名或同 id 的镜像账号，再按宿主机建立 |
| 19 | 容器第一次启动偶尔要 10 秒 | `useradd`、`userdel` 每次写入都 fdatasync，磁盘忙时一次要几秒 | 只影响第一次启动；重启时入口脚本不再调用账号工具 |
| 20 | `docker-compose: command not found` | 有的主机只有 compose v2 插件，有的只有 v1 | 自动选择（优先 v2）并记录下来；切换脚本和运维说明用同一个命令 |
| 23 | 慢日志只有 "executing too slow"，没有调用栈；FPM 日志报 `failed to ptrace(ATTACH) … Operation not permitted` | 容器默认没有 `CAP_SYS_PTRACE`（在 3.10 内核上实测） | 池配置开了 `request_slowlog_timeout` 时加 `cap_add: [SYS_PTRACE]` |
| 24 | 宿主机加载的扩展镜像里没有 | 基础镜像没装这些包 | 按同一修订号补装；不需要的主机用 `PHP_DISABLE_EXT` 关闭 |
| 25 | 业务用户执行 php 时补齐配置不生效，也没有报错 | 补齐文件权限是 0600，以业务用户运行的 CLI 读不到，PHP 会静默跳过 | 以 0644 安装；分别以 root 和业务用户导出配置来验证 |

## 主机与系统

| # | 现象 | 原因 | 处理 |
|---|---|---|---|
| 9 | supervisord.log 里每 50 秒出现一组 "Included extra file"，但没有 "started" | 早年手工建的重复 `supervisor.service`（Restart=on-failure）一直在启动失败 | 迁移后它会和容器争抢 socket，必须移除 |
| 10 | 删除旧包后，`php-fpm` 仍显示为开机启用 | 一键安装包留下的 `/etc/init.d/php-fpm` 指向已不存在的旧路径，原来被原生 unit 盖住了 | 移除这个脚本 |
| 13 | 队列配置里写着 `stopwaitsecs=3600` | 允许每个进程最长花 1 小时收尾 | 按最坏情况准备：`timeout 300 supervisorctl stop all`，超时后由 `systemctl stop` 强制结束 |
| 14 | `scp 主机:/路径/{a,b}` 什么也没复制 | OpenSSH 9 的 scp 默认走 SFTP，不展开远程的花括号 | 逐个文件复制 |
| 16 | fail2ban 容器几个月没有封过 IP | 它只挂载了 `/var/log/secure` 这一个文件，日志轮转后一直在读旧 inode | 挂载 `/var/log` 目录 |
| 17 | `pkill -f 模式` 把执行它的命令自己也杀掉了 | 当前命令行本身也包含这个模式 | 按 PID 杀，或者把模式写成 `[x]yz` 的形式 |
| 22 | 迁移会让所有已登录用户掉线 | 原 FPM 用 drop-in 设置了 `PrivateTmp=no`，会话存放在宿主机的 /tmp；容器有自己的 /tmp | 检测到 `PrivateTmp=no` 时给 FPM 挂载 /tmp；CLI 容器默认就挂载 /tmp |
| 26 | 下载不到回滚用的原包 | 这些包来自默认禁用的仓库 | 从 `yum list installed` 识别包的来源仓库，只启用这个仓库下载 |
| 27 | SSH 会话 5 分钟没有输出就被服务器断开 | sshd 设置了 `ClientAliveInterval 300`、`ClientAliveCountMax 0` | 长步骤脱离 SSH 执行，SSH 只用来轮询；客户端加 `ServerAliveInterval` |
| 28 | rc.local 里有 `systemctl start php-fpm` | 早年手工加的 | 备份后注释掉 |
| 29 | 删除旧包到装好转发脚本之间，有几秒没有 `/usr/bin/php` | 删除 php-cli 时 rpm 会删掉这个文件，不能提前替换 | 等到某分钟的第 5 秒再开始删除，实测这段空窗为 3.8～5.3 秒 |

## 验证与排查

| # | 现象 | 原因 | 处理 |
|---|---|---|---|
| 12 | 每分钟有几次定时任务退出码为 1 | crontab 调用的命令在当前代码里不存在，迁移前就一直失败 | 查出具体命令，再用 `php think list` 核对 |
| 15 | 并行对比第一次全部"连接被拒绝" | SSH 隧道还没建好对比就开始了 | 等本地端口开始监听后再开始 |
| 21 | `nginx -T` 输出 0 行，或者找不到任何 PHP 站点 | 容器里的 nginx 以 `-p 前缀 -c conf/nginx.conf` 启动，root 是相对路径 | `nginx -T` 带上同样的参数；生成目标时按前缀补全 root |
| 30 | 切换后验证脚本报 "Could not open input file"；FPM 报 "Primary script unknown" | php 已经在容器里执行，看不到 /root 下的脚本；FPM 日志目录是 0770，worker 进不去 | 临时脚本放到 /tmp 这类挂载目录里，并且要让 worker 用户读得到 |
| 31 | 所有调用 php 的定时任务失败了约 2 分 40 秒 | 手写脚本用单引号把 `$变量` 原样写进了转发脚本的配置文件，cron 的干净环境里没有这个变量 | 这类文件只由切换脚本生成，并用 `env -i` 验证 |
| 32 | 切换后有定时任务退出码为 1 | 迁移前就在失败：脚本 cd 到已删除的目录；退款任务每次都卡在一条 0 元记录上 | 查出命令，再看任务自己的日志。cron 的输出邮件不能作为依据：邮箱早就满了，邮件一直被退回 |
