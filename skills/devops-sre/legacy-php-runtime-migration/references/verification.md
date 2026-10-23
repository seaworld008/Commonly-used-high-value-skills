# 验证方法与命令

下面的命令都在实际迁移中用过。路径和端口按主机替换。完整的、带单元测试的工具见 [php-fpm-nginx-images v20261023.1](https://github.com/seaworld008/php-fpm-nginx-images/tree/v20261023.1/tools)。

## 1. 导出实际生效的配置（按真实 SAPI）

探针脚本 `ini_dump.php`，放在 FPM worker 读得到的目录里（迁移后放 /tmp 这类挂载目录）：

```php
<?php
$out = array('sapi' => PHP_SAPI, 'version' => PHP_VERSION,
    'uid' => function_exists('posix_geteuid') ? posix_geteuid() : null,
    'tmp' => sys_get_temp_dir(), 'ini_files' => php_ini_loaded_file() . ' | ' . php_ini_scanned_files());
foreach (ini_get_all(null, false) as $k => $v) { $out['ini'][$k] = $v; }
foreach (get_loaded_extensions() as $e) { $out['ext'][strtolower($e)] = phpversion($e); }
echo json_encode($out);
```

- CLI：`php ini_dump.php > cli.json`。迁移后还要以业务用户执行一次：`sudo -u 业务用户 php …`。
- FPM：通过 FastCGI 直接请求，不经过 nginx。有 `cgi-fcgi`（fcgi 包）时：

```bash
SCRIPT_FILENAME=/tmp/ini_dump.php REQUEST_METHOD=GET \
  cgi-fcgi -bind -connect 127.0.0.1:9000 | sed '1,/^\r\?$/d' > fpm.json
```

  没有 `cgi-fcgi` 时，可以用参考实现里的 PHP 或 Python FastCGI 客户端。
- 对比两份 JSON：逐个键比较 `ini` 和 `ext`。只在新环境才有的指令只提示；`extension_dir` 等路径差异列为预期差异。参考实现的 `tools/ini_parity.py` 可以直接生成补齐文件。

## 2. 新旧 FPM 并行对比

```bash
# 本地端口映射到远端的旧 FPM（9000）和新 FPM（19000）
ssh -N -o ExitOnForwardFailure=yes -L 29000:127.0.0.1:9000 -L 29001:127.0.0.1:19000 root@主机 &
# 等本地端口开始监听后再开始对比
until ss -ltn | grep -q ':29001 '; do sleep 0.5; done
python3 tools/fcgi_compare.py --http --old 127.0.0.1:29000 --new 127.0.0.1:29001 --targets targets.tsv
# 判断是不是动态内容：旧环境自己对比自己
python3 tools/fcgi_compare.py --http --old 127.0.0.1:29000 --new 127.0.0.1:29000 --targets targets.tsv
```

- `targets.tsv` 每行一个目标：`host<TAB>document_root<TAB>/index.php[<TAB>query]`。可以从 `nginx -T` 生成，参见 `tools/nginx_targets.py --fcgi [--prefix nginx前缀]`。
- 加上框架路由（`s=/模块/控制器/方法`）、后台入口和一个不存在的地址。不要请求安装、支付回调、测试这类有副作用的脚本。

## 3. 经 nginx 的全站探测

```bash
python3 tools/nginx_targets.py --probe nginx-T.txt > probe-targets.tsv   # scheme  port  host
PROBE_PATHS='/ /index.php /__upgrade_check__.html' bash tools/http_probe.sh < probe-targets.tsv > before.tsv
# ……切换……
PROBE_PATHS='/ /index.php /__upgrade_check__.html' bash tools/http_probe.sh < probe-targets.tsv > after.tsv
python3 tools/probe_compare.py before.tsv after.tsv
```

只要 TLS 端口上有一个 server 写了 `ssl`，同一端口上其他 server 的探测也要走 https：nginx 是按 socket 启用 TLS 的。

## 4. 定时任务的退出码

php 在容器里执行后，每次 cron 调用都会在 docker 中产生一个 exec：

```bash
timeout 190 docker events --filter container=php72-cli --filter event=exec_die \
  --format '{{.Actor.Attributes.exitCode}} {{.Actor.Attributes.execID}}' > exec.txt
awk '{print $1}' exec.txt | sort | uniq -c            # 退出码分布
# 把失败的 exec 对应到具体命令（exec 实例被回收之前都能查到）
for id in $(awk '$1!=0{print $2}' exec.txt); do
  curl -s --unix-socket /var/run/docker.sock "http://localhost/exec/$id/json" \
    | grep -oE '"(ExitCode|user)":[^,}]*|"arguments":\[[^]]*\]'
done
```

查出命令后，再看这个任务自己的日志，判断迁移前是否就在失败。cron 的输出邮件常常因为邮箱已满被退回，不能作为依据。

## 5. 业务指标（切换前后各取一次）

- **nginx combined 格式**：最近 N 分钟的状态码分布。

  ```bash
  awk -v s="$(date -d '-10 min' '+%d/%b/%Y:%H:%M')" '{t=substr($4,2,17)} t>=s {c[substr($9,1,1)"xx"]++} END{for(k in c) print k, c[k]}' access.log
  ```

- **JSON 格式**：从 `"time":"…"`、`"status":…`、`"request_time":…` 取值，算出请求数、5xx 数、平均耗时和 P95。切换后的头几分钟 opcache 在预热，P95 可能短暂升高，要和稳定后的时段一起看。
- **错误日志**：PHP-FPM 错误日志、池的 error_log 新增了多少行；框架当天 error 级日志的行数（例如 ThinkPHP `runtime/log/年月/日.log` 里的 `[ error ]`）。
- **宿主机 CPU**：`sar -u -s 时间`（10 分钟一档），对比切换前后的 user/sys；`sar -w` 看进程创建速率。每个 cron 调用多出 sudo 和 `docker exec` 两层进程，所以定时任务多的主机，CPU 会略有上升。

## 6. 队列与命令行

```bash
supervisorctl status | awk '{print $2}' | sort | uniq -c                    # RUNNING 数
diff <(awk '{print $1}' before.txt) <(supervisorctl status | awk '{print $1}')   # 程序名一致
cd 代码目录 && php think list | grep -cE '^  [a-z]'                          # root
cd 代码目录 && sudo -u 业务用户 php think list | grep -cE '^  [a-z]'           # 业务用户
env -i PATH=/usr/bin:/bin sudo -u 业务用户 /usr/bin/php -r 'echo posix_geteuid();'   # cron 的干净环境
```

`docker stats` 里队列容器的 CPU 看起来很高，不一定是新增的负载。例如 `think queue:listen` 每处理一个任务都会新启动一个 `sh -c php think queue:work` 子进程。要以宿主机 `sar` 的前后对比为准。

## 7. 会话与慢日志

- 会话：切换后统计 `find 会话目录 -newer 切换时间标记 -name 'sess_*'` 的数量和属主，确认会话仍在写入、用户没有掉线。
- 慢日志：发一个睡眠时间超过 `request_slowlog_timeout` 的探针请求，确认慢日志里有 `script_filename` 和调用栈，FPM 日志里有 `about to trace`、没有 `ptrace` 报错。
