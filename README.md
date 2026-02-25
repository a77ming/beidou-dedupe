# Video Dedupe Desktop (Demo)

项目结构与入口说明见：`PROJECT_CODE.md`

## 开发运行

```bash
npm install
npm run dev
```

## 打包 Windows 安装包（后续）

```bash
npm run build
npm run dist
```

## 打包 macOS (Apple Silicon) DMG

当前版本默认会把 Python 处理器打成一个自包含二进制并打进 `.app`，这样用户机器上不需要预装 Python/pip。

```bash
npm install
npm run dist:mac:arm64
```

> 如需云端策略更新：设置环境变量 `STRATEGY_URL` 指向策略 JSON。

示例 JSON：

```json
{
  "source": "remote",
  "version": "2026-02-05",
  "strategies": [
    {
      "key": "hash-md5",
      "name": "MD5 指纹",
      "description": "对文件内容做 MD5 指纹，相同视为重复。",
      "atomic": true
    }
  ]
}
```
