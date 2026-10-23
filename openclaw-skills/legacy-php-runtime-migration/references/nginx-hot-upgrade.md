# nginx 平滑升级（源码编译的 nginx，只换二进制）

适用于一键安装包或手工编译的 nginx：配置、目录和启动方式都不变，只把程序换成新版本。实测从 1.16.1 + OpenSSL 1.1.1d 升到 1.30.6 + OpenSSL 3.5.9，零中断，所有域名请求前后一致。

## 编译

1. 照搬 `nginx -V` 里的 `configure arguments`，包括第三方模块和 `--prefix`、`--user`、`--with-*`。
2. 在与目标主机相同的系统环境里编译，例如 CentOS 7 主机用 CentOS 7 容器，保证 gcc、glibc 一致。编完用 `ldd` 确认动态依赖与旧程序相同。
3. 正则继续用系统的 PCRE（`--without-pcre2`）；OpenSSL 选 LTS 版本静态编入（`--with-openssl=源码目录`）。OpenSSL 3.x 的 Configure 需要 Perl 模块，CentOS 7 上要装 `perl-core`。
4. nginx 和 OpenSSL 的源码包都要核对官方 PGP 签名。
5. 编译环境的网络问题：Docker Hub 拉 `centos:7` 卡住时，改用 `quay.io/centos/centos:centos7`；镜像源慢时，用 `vault.centos.org`。

## 切换前

```bash
./nginx-new -t -c /usr/local/nginx/conf/nginx.conf      # 用新程序测试现有配置
nginx -T > nginx-T.txt                                    # 备份完整配置
tar czf nginx-conf-backup.tgz -C /usr/local/nginx conf
# 生成"域名 × 端口"清单，记录基线：每个目标请求首页和一个不存在的地址
python3 tools/nginx_targets.py --probe nginx-T.txt > targets.tsv
bash tools/http_probe.sh < targets.tsv > baseline-before.tsv
head -n 30 targets.tsv > spot.tsv      # 切换时用来抽查的子集，也可以改为只挑核心域名
```

## 平滑切换

```bash
cp -p sbin/nginx sbin/nginx-旧版本.bak && install -m 755 nginx-new sbin/nginx
kill -USR2 $(cat logs/nginx.pid)          # 用新程序拉起新 master；旧 pid 文件改名为 nginx.pid.oldbin
sleep 2; kill -WINCH $(cat logs/nginx.pid.oldbin)   # 旧 worker 处理完手上的请求后退出
bash tools/http_probe.sh < spot.tsv > spot-check.tsv   # 抽查一批目标，与 baseline-before.tsv 中对应的行对比
kill -QUIT $(cat logs/nginx.pid.oldbin)   # 抽查一致后，退出旧 master
```

- 回退（旧 master 还在时）：`kill -HUP 旧master` 让旧 worker 重新起来，再 `kill -QUIT 新master`。
- 切换后：全站探测与基线对比；用外部 curl 记录每个 HTTPS 站点的 TLS 版本和 HTTP 版本。最后执行一次 `systemctl restart nginx`，按开机时的启动路径再实测一遍，并确认开机自启。

## 兼容性

- `listen … http2` 写法只会出现"已弃用"的警告，行为不变。
- 同一个端口上有的 server 写了 http2、有的没写，会出现 `protocol options redefined` 警告，整个端口的行为不变。
- OpenSSL 3 默认不再提供 TLSv1 和 TLSv1.1。没有显式设置 `ssl_protocols` 的站点会开始支持 TLS 1.3，要提前告诉使用老客户端的业务方。
