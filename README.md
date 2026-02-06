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
