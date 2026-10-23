---
name: legacy-php-runtime-migration
description: 'Migrate end-of-life PHP on long-lived hosts (Remi, OneinStack, CentOS 7) to vendor-patched builds or same-path containers without changing code, nginx, cron or paths: parity, side-by-side FPM checks, staged cutover, rollback.'
zh_description: "在不改代码、nginx 配置、定时任务和目录的前提下，把宿主机上停止维护的 PHP 换成带补丁的版本或同路径容器：补丁证据、盘点、实际配置对齐、新旧 FPM 并行对比、可回滚的分步切换和切换后验证。"
version: "1.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
license: "MIT"
tags: '["php", "migration", "devops", "sre", "security-patching", "docker", "nginx", "legacy"]'
created_at: "2026-10-23"
updated_at: "2026-10-23"
quality: 4
complexity: "advanced"
---

# 旧版 PHP 运行时迁移（宿主机 → 补丁版 / 同路径容器）

把停止维护的 PHP（典型是 CentOS 7 上的 7.x）换成带安全回移的构建，同时让应用、nginx、crontab、队列和发布流程感觉不到变化。方法来自四台主机（两台测试、两台生产）的实际迁移：FPM 中断 0.8～2.2 秒，队列 1 秒内停止后在容器中恢复，切换后没有新增 5xx。

## 触发条件

适用：
- 宿主机 PHP 的来源已停更（Remi EL7、OneinStack 或手工编译），新 CVE 拿不到修复，但不能升级 PHP 大版本或框架。
- 需要回答"版本号相同的 PHP 到底有没有某个补丁"。
- 要把宿主机上的 php-fpm、supervisord 队列和 crontab 里的 php 一起迁到容器，并保持 uid、路径、会话、日志和监听地址不变。
- 源码编译的 nginx 需要换成新版本二进制，配置和目录不变（见 [nginx 平滑升级](references/nginx-hot-upgrade.md)）。

不适用：
- PHP 大版本或框架升级：这需要改代码和完整的业务回归。
- 已经跑在 Kubernetes 等编排平台里的容器：直接换基础镜像，走正常发布。
- 发行版仍在提供安全更新：直接升级系统包更简单。

## 核心原则

1. **证据先于结论**：补丁状态分为 `UNVERIFIED`（只核对了 changelog）、`VENDOR_MINIMAL_BACKPORT`、`VENDOR_FIXED_VERIFIED`。`php -v` 显示的版本号不能说明有没有补丁，要看包修订号、changelog 和源码补丁。
2. **零改动切换**：路径、uid/gid、监听地址、php.ini、FPM 池、supervisord 配置、crontab 原样沿用。新旧环境的差异用"补齐文件"消除，不改业务配置。
3. **以真实 SAPI 为准**：FPM 的实际生效配置用 FastCGI 请求导出，命令行分别以 root 和业务用户导出。`php -m`、`php -i` 只代表 CLI。
4. **先测试后生产**：测试主机完整走一遍并通过，生产一台验证完再做下一台。
5. **每步可验证、可回滚**：动手前备好回滚包（原包、原配置）；每一步先验证再继续，出错即停，停在可解释的状态。
6. **不改变业务数据和业务行为**：迁移中发现的既有问题先查清影响，再由负责人决定。涉及资金或数据的任务只报告或停用，不顺手"修复"（见 [生产操作安全](references/production-safety.md)）。

## 方案选择

| 现状 | 推荐方案 | 代价 |
|---|---|---|
| 发行版仍有安全更新 | 原地升级系统包 | 最小；注意运行用户和扩展是否齐全 |
| 来源已停更，主机还要用几年 | **同路径容器**（本技能主线） | 一次性工作量；以后跟随供应商更新重建镜像 |
| 来源已停更，主机即将下线 | 自行把补丁回移到源码包并重建 | 改动最小，但以后要自己维护这个包 |
| 已经是容器 | 换基础镜像，按正常发布流程上线 | 需要回归业务镜像 |

同路径容器的形态：同一个镜像起两个容器，都使用 `network_mode: host` 和 `restart: always`。
- `php72-fpm`：监听宿主机原来的地址，nginx 配置不变。
- `php72-cli`：用宿主机原有的 `/etc/supervisord.conf` 运行队列，并挂载其 socket 和日志目录，所以宿主机上的 `supervisorctl`、管理端口和监控脚本照常可用。
- 宿主机的 `/usr/bin/php` 换成转发脚本：`docker exec -u 调用者uid:gid -w 当前目录 php72-cli php …`。非 root 用户经过一条只放行该脚本的 sudo 规则执行。crontab 不用改。

最小骨架如下，路径、用户和扩展都按盘点结果替换：

```yaml
x-php: &php
  image: <registry>/php-fpm:7.2-hostcompat     # 带回移补丁的构建，锁定包修订号
  network_mode: host
  restart: always
  environment:
    HOST_USERS: "nginx:1000:1000:48"            # 与宿主机一致的 名称:uid:gid[:附加gid]
    PHP_DISABLE_EXT: "amqp apcu imap ldap"      # 镜像多出、宿主机没有加载的扩展
services:
  php72-fpm:
    <<: *php
    command: ["php-fpm"]                        # 入口脚本执行 php-fpm7.2 -F，前台运行
    cap_add: [SYS_PTRACE]                       # 只在池配置开了慢日志时需要
    volumes:
      - /srv/www:/srv/www                       # 代码、上传、业务日志，按原路径挂载
      - /var/log/php-fpm:/var/log/php-fpm
      - /var/lib/php/session:/var/lib/php/session
      - ./conf/php-fpm.conf:/etc/php/7.2/fpm/php-fpm.conf:ro     # [global] daemonize = no，pid、error_log 指向容器内路径
      - ./conf/php.ini:/etc/php/7.2/fpm/php.ini:ro               # 宿主机原文件的副本
      - ./conf/www.conf:/etc/php/7.2/fpm/pool.d/www.conf:ro
      - ./conf/zz-host-parity-fpm.ini:/etc/php/7.2/fpm/conf.d/99-zz-host-parity.ini:ro
  php72-cli:
    <<: *php
    command: ["supervisord"]                    # 入口脚本执行 supervisord -n，前台运行
    volumes:
      - /srv/www:/srv/www
      - /tmp:/tmp                               # 宿主机上的命令行 PHP 本来就和其他程序共用 /tmp
      - ./conf/php.ini:/etc/php/7.2/cli/php.ini:ro
      - ./conf/zz-host-parity-cli.ini:/etc/php/7.2/cli/conf.d/99-zz-host-parity.ini:ro
      - /etc/supervisord.conf:/etc/supervisord.conf:ro
      - /etc/supervisord.d:/etc/supervisord.d:ro
      - /var/run/supervisor:/var/run/supervisor  # 宿主机的 supervisorctl 通过同一个 socket 管理
      - /var/log/supervisor:/var/log/supervisor
```

两个容器的主进程都必须在前台运行：tini 作为 1 号进程，入口脚本建好账号后执行 `php-fpm7.2 -F` 或 `supervisord -n`。如果直接用发行版默认配置启动（`daemonize = yes`），FPM 会转入后台，主进程退出，容器随之停止，nginx 就找不到监听端口。

转发脚本的核心（`/usr/bin/php` 以 root 身份直接调用它，其他用户经 sudo 调用）：

```bash
#!/bin/bash
# /usr/local/bin/php72-exec：在 php72-cli 里以调用者的身份、在当前目录执行 php
. /etc/php72-exec.conf              # MOUNTS="/srv/www /tmp"  CONTAINER=php72-cli
U=${SUDO_UID:-$(id -u)}; G=${SUDO_GID:-$(id -g)}; W=/
for m in $MOUNTS; do case "$PWD/" in "${m%/}"/*) W=$PWD ;; esac; done
I=""                                # 默认不接管标准输入：docker exec -i 会把调用方的输入全部读走
if [ -t 0 ]; then I=-i; if [ -t 1 ]; then I=-it; fi
elif [ "${PHP72_STDIN:-0}" = 1 ]; then I=-i; fi
exec /usr/bin/docker exec $I -u "$U:$G" -w "$W" "$CONTAINER" php "$@"
```

## 工作流程

### 1. 盘点（只读）

逐项记录，后面每一步都要用到：
- FPM：池配置（用户、监听地址、`pm.*`、慢日志、`php_admin_value`），以及 systemd 的 `PrivateTmp`（`systemctl show php-fpm -p PrivateTmp`）。
- 实际生效配置：FPM 通过 FastCGI 导出，CLI 直接导出，都保存成 JSON（方法见 [验证方法](references/verification.md)）。
- 扩展及版本，尤其是 redis、mongodb、swoole 这类直接影响业务的扩展。
- supervisord：各程序的运行用户、命令路径、日志路径、`stopwaitsecs`、`numprocs`。
- 各用户的 crontab，以及 cron 调用的脚本：脚本里写死的 PHP 路径、`cd` 到的目录是否还存在。
- 调用 php 的其他位置：systemd 单元、rc.local、发布脚本、监控脚本、`#!/usr/bin/env php` 开头的工具（例如 composer）。
- 代码里的外部命令（`exec`、`popen`、反引号）、`mail()`、MySQL socket，以及 `localhost` 写法的数据库主机。
- 会话存放位置：`session.save_path`；为空时就在 `/tmp`。
- nginx：`nginx -T` 的完整输出。nginx 在容器里运行时，要带上与启动命令相同的 `-p`、`-c`。
- docker 和 compose 的版本（v1 与 v2）、磁盘空间、sshd 的空闲断开设置（`ClientAliveInterval` / `ClientAliveCountMax`）。

验收：每个使用 PHP 的入口都能对应到迁移后的执行位置；运行用户和需要挂载的目录都列清楚了。

### 2. 补丁证据

- 下载供应商的包，查看 changelog 中对应 CVE 的条目；能拿到源码包时，再看 `debian/patches/series` 或 SRPM 中的补丁。
- 已经停更的源（例如 Remi EL7 最后一次构建在 2024-06）要明确记为"不包含"，不要因为版本号相同就推断已修复。
- 结论写进发布说明，按原则 1 的分级填写，不写"已修复 / 已验证"之类没有证据支撑的说法。

### 3. 镜像与扩展

- 基础镜像选择带回移补丁的发行版构建（例如 Debian 12 + Sury），版本锁定到包修订号。
- 扩展对比：宿主机有、镜像没有的数量必须为 0；镜像多出的扩展在启动时关闭（`PHP_DISABLE_EXT`）。缺的扩展按同一修订号补装。
- 入口脚本按 `HOST_USERS="名称:uid:gid[:附加gid]"` 建立与宿主机一致的账号。镜像自带的同名或同 id 账号（例如 nginx 999）先让位，否则 FPM 会以错误的 uid 运行，或者容器直接起不来。重启时不要再调用 `useradd` 这类工具：它们每次写入都 fdatasync，磁盘忙时一次要几秒。
- 去掉基础镜像里会覆盖 php.ini 的生产配置片段；如果宿主机的 FPM 没有加载 readline，容器里也要关闭。

### 4. 实际配置对齐

1. 在隔离的环境里启动候选容器，挂载宿主机的 php.ini 和池配置，按真实 SAPI 导出实际生效配置。
2. 与宿主机的导出逐项对比，生成补齐文件，例如 `include_path`、`realpath_cache_ttl`、MySQL socket 默认值、`opcache.memory_consumption`、CLI 的 `session.save_path`。
3. 只在新环境才有的指令（例如 msgpack 3.0 的 `msgpack.assoc`）只给提示、不写入；`extension_dir` 这类路径差异列入预期差异。
4. 带上补齐文件再导出一次，确认只剩预期差异，并分别以 root 和业务用户验证。补齐文件必须所有人可读：命令行 PHP 以业务用户运行时，读不到的 ini 会被静默跳过。

### 5. 并行验证（不影响线上）

- 新 FPM 先监听测试地址（例如 `127.0.0.1:19000`），与宿主机 FPM 同时运行。
- 经 SSH 隧道，对新旧 FPM 发送相同的只读 FastCGI GET 请求，逐个入口对比状态码、大小和跳转。目标从 `nginx -T` 生成；root 是相对路径时要按 nginx 的前缀补全。
- 有差异时，对旧环境连续请求两次：如果两次结果也不同，就是动态内容（例如 SSO 跳转里的随机 token），不算迁移造成的差异。
- 慢日志开着时，发一个超过阈值的请求，确认慢日志里有调用栈。容器需要 `SYS_PTRACE`，否则只会记录 `failed to ptrace(ATTACH)`。

### 6. 切换

按以下顺序执行，每一步验证通过才继续。生产主机上要脱离 SSH 会话执行（`setsid nohup … > 日志 &`），再轮询日志：
1. 保存回滚用的原包（只从包原来的仓库下载；默认禁用的仓库要显式启用），数量不足就停止。
2. 记录基线：全站探测、队列状态、业务指标。
3. FPM：监听地址改回原地址，停宿主机 FPM，重启容器，确认端口由容器进程接管；接管失败就立即启动宿主机 FPM 并停止。记录中断时长。
4. 队列：`timeout 300 supervisorctl stop all`，停用宿主机 supervisord，移除重复的 unit，启动 `php72-cli`，等到 RUNNING 数与基线相同。
5. 安装转发脚本、sudo 规则和挂载路径配置；删除原包。要等到某分钟的第 5 秒再开始删除，避开整分钟触发的定时任务，因为删包到装好转发脚本之间没有 `/usr/bin/php`。
6. 注释掉 rc.local 里启动旧服务的行（先备份），检查开机启动项。
7. 用 `env -i PATH=/usr/bin:/bin` 模拟 cron 的干净环境，分别以 root 和业务用户执行 php，确认能用。

### 7. 切换后验证与观察

- 全站探测与切换前对比；实际生效配置与原宿主机对比。
- `php think list` 这类命令在 root 和业务用户下的输出相同；队列的 RUNNING 数和程序名与切换前一致。
- 定时任务：观察 `docker events` 的 `exec_die` 退出码；出现非 0 时，查出具体命令，再查任务自己的日志，判断迁移前是否就在失败。
- 业务指标：5xx、P95 耗时、PHP 错误日志新增行数、框架 error 级日志、宿主机 CPU（`sar`）。切换后的头几分钟 opcache 在预热，P95 可能短暂升高。
- 会话：确认会话文件仍在更新，属主正确，用户没有被踢下线。
- 发布流程：确认发布脚本不调用 php、不重启 php-fpm；`opcache.validate_timestamps=1` 时新代码会自动生效。迁移后至少看一次真实发布的结果。

### 8. 清理与沉淀

- 删除旧安装目录前，先确认没有进程在用、没有配置引用、不是挂载点；原配置和文件清单留档。最后一层回滚备份可以保留几天再删。
- 运维说明写到主机上（例如运行目录下的 `README.txt`）：容器、命令、维护方法、限制、回滚步骤。
- 把踩到的坑补进团队文档（见 [踩坑记录](references/pitfalls.md)）。

## 回滚

每台大约 1 分钟：停止并删除两个容器 → 本地安装切换前保存的原包 → 解开配置备份包（包括 rc.local）→ 删除 sudo 规则和转发脚本 → 启用并启动原来的 php-fpm 和 supervisord。原来那些让会话留在 /tmp 的 systemd drop-in 不要删，回滚后还要用。

## 日常维护（迁移后）

| 操作 | 方法 |
|---|---|
| 新增、修改、删除队列 | 与以前一样：编辑 `/etc/supervisord.d/*.conf`，再执行 `supervisorctl reread && supervisorctl update` |
| 定时任务 | 与以前一样，`crontab -e`。命令里的 php 会在容器中以原用户、原当前目录执行 |
| 修改 php.ini 或池配置 | 编辑运行目录下的副本，然后 `docker compose restart php72-fpm php72-cli` |
| 新增运行用户 | 修改 `HOST_USERS` 并重建容器；如果这个用户的 cron 要调用 php，再在 sudo 规则里加一行 |
| 管道输入 | `echo x \| PHP72_STDIN=1 php …`：`docker exec -i` 会把调用方的标准输入全部读走，所以转发脚本默认不接管 |

限制：
- 队列里只能放 PHP 程序。
- 程序和脚本的路径必须在挂载目录下面，/root 下的脚本在容器里看不到。
- `#!/usr/bin/env php` 开头、又不在挂载目录里的工具（例如 composer）要另外处理。

## 示例

**示例 1：判断同版本号的 PHP 有没有补丁**
- 两个来源都显示 `php -v` = 7.2.34。
- Remi `php-7.2.34-22.el7.remi` 的 changelog 最后一条是 2024-06-04，结论为"不包含 2026-10 的补丁"。
- Sury `7.2.34-66+0~20261021…` 的 changelog 列出了这两个 CVE，结论为 `UNVERIFIED`（只核对了 changelog，补丁没有逐行审计）。

**示例 2：有 54 个队列、每分钟 31 个定时任务的后台主机**
- 盘点：
  - nginx 在容器里以 `-p` 启动，root 是相对路径，生成探测目标时要用 `--prefix` 补全。
  - FPM 原来使用私有 /tmp，所以容器 FPM 不挂载 /tmp。
  - 主机上只有 compose v2。
- 并行验证：5 个入口里 3 个完全一致，2 个只差 SSO token。
- 切换：
  - FPM 中断 0.9 秒。
  - 没有 `/usr/bin/php` 的时间是 3.8 秒，结束在整分钟之前。
  - 切换后 35 分钟内 14374 个请求，0 个 5xx。
  - 宿主机 CPU 多了约 1.5%：每个定时任务多出 sudo 和 `docker exec` 两层进程。

**示例 3：会话存放在 /tmp、开了慢日志的主机**
- 盘点：原来的 php-fpm 设置了 `PrivateTmp=no`，会话文件都在宿主机的 /tmp。
- 配置：容器 FPM 必须挂载 /tmp，否则所有用户都会被踢下线；慢日志需要 `cap_add: [SYS_PTRACE]`。
- 切换后：会话文件照常更新，慢日志里有完整的调用栈。

## 边界

- 本技能不做漏洞利用验证，也不把 changelog 当成补丁已审计的证据。
- 生产变更、读取生产数据库、停用业务任务、推送镜像仓库，都要在已获授权的范围内进行。授权不清楚时，先完成只读部分，再说明需要谁来决定什么。
- 静态检查和探测对比不能代替登录、下单这类业务流程的回归，也不能代替压测；报告时要写清楚验证范围。

## 参考

- [踩坑记录](references/pitfalls.md)：32 条"现象 → 原因 → 处理"。
- [验证方法与命令](references/verification.md)：实际生效配置导出、FastCGI 对比、定时任务退出码、业务指标。
- [nginx 平滑升级](references/nginx-hot-upgrade.md)：同参数编译，`USR2` / `WINCH` / `QUIT`。
- [生产操作安全](references/production-safety.md)：脱离 SSH 执行、只读诊断、"卡住的任务可能正在起保护作用"、cron 邮件、发布兼容性。
- 参考实现（入口脚本、`kit/` 切换工具包、对比工具及其单元测试）：[php-fpm-nginx-images v20261023.1](https://github.com/seaworld008/php-fpm-nginx-images/tree/v20261023.1)，其中 `docs/13`、`variants/php72-host-compat`、`tools/` 三个目录。
