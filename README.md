# ComfyUI-SaveImage-GenInfo

ComfyUI で生成した画像に A1111 互換の生成情報を JSON で埋め込むカスタムノードです。

## インストール

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/RyoheiTanaka/ComfyUI-SaveImage-GenInfo.git
```

追加パッケージは不要です。

## ノード

### Save Image (GenStash)

標準の Save Image の代わりに使用します。ワークフローから以下の情報を自動抽出し、PNG メタデータに JSON として埋め込みます。

| 項目            | 取得元ノード                        |
| --------------- | ----------------------------------- |
| prompt          | CLIPTextEncode (positive)           |
| negative_prompt | CLIPTextEncode (negative)           |
| seed            | KSampler / KSamplerAdvanced         |
| steps           | KSampler / KSamplerAdvanced         |
| cfg             | KSampler / KSamplerAdvanced         |
| sampler         | KSampler (sampler_name + scheduler) |
| denoise         | KSampler                            |
| model           | CheckpointLoaderSimple              |
| width / height  | EmptyLatentImage                    |
| clip_skip       | CLIPSetLastLayer                    |

### パラメータ

| パラメータ      | デフォルト | 説明                                         |
| --------------- | ---------- | -------------------------------------------- |
| filename_prefix | GenStash   | ファイル名のプレフィックス                   |
| foldername      | (空)       | サブフォルダ名。空の場合は output 直下に保存 |
| save_metadata   | true       | PNG メタデータへの埋め込みの ON/OFF          |

### 配線

`images` に VAE Decode の出力をつなぐだけです。設定値はワークフローから自動取得されるため、追加の配線は不要です。

```
[VAE Decode] ──images──▶ [Save Image (GenStash)]
```

### 出力例（PNG メタデータ）

キー: `generation_info`

```json
{
  "prompt": "1girl, masterpiece, best quality",
  "negative_prompt": "worst quality, low quality",
  "seed": 12345,
  "steps": 25,
  "cfg": 7.0,
  "sampler_name": "dpmpp_2m",
  "scheduler": "karras",
  "sampler": "dpmpp_2m karras",
  "denoise": 1.0,
  "model": "animagine-xl-3.1.safetensors",
  "width": 1024,
  "height": 1536,
  "size": "1024x1536",
  "clip_skip": 2
}
```

ComfyUI のワークフロー JSON (`workflow`, `prompt`) も従来通り保存されます。

## ライセンス

MIT
