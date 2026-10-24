# 归档说明 · M2（2026-10-25）

## 这个包里是什么
`M2-2026-10-25.tar.gz` 打包了 `m2/` 与 `mine/` 两个目录（23 个文件），即 M2 的可复现驱动、四跑原始 json、README、evidence，
以及队长与检测员的全部判定文件（预登记、盲判据、验收台账、交付记录）。

**不含**：模型权重（*.gguf）、KV 记忆块（*.kvmem）、DLL —— 这些被 .gitignore 排除，不在归档内，也不在 git 里。

## 为什么归档
今晚因「二进制没归档就被覆盖」永久丢失过一个 DLL（3a726dbd）。结论可以重跑，二进制和原始产物不能。
所以凡是支撑结论的产物，一律打包 + 逐文件 sha256 留档。

## 怎么校验
`MANIFEST.sha256` 第一段是 tarball 自身的 sha256，其后是包内每个文件的 sha256。
tarball sha256：`05e30c5b68d2448812cc6b26ad0f6c4fcde0cd7f5f4b6a2fdf656954a7a1ac12`

## 校验方法
```
python -X utf8 -c "import hashlib;h=hashlib.sha256();f=open(r'archive/M2-2026-10-25.tar.gz','rb');[h.update(b) for b in iter(lambda: f.read(1<<20), b'')];print(h.hexdigest())"
```

## 与本归档配套的外部产物（不在包内）
- 14B 块：`kvmem/m2_v1_14b/{home,project,habit,project_paraphrase18,g18_bos_c18_14b}.kvmem`
- DLL 归档：`kvmem/m2_visibility/runs_m14b/dll_archive/{kvshim_vk_9edbafa1, kvshim_vk_c7ea09bb_DLL_THAT_PRODUCED_EF, kvshim_vk_ed91cbe0}.dll`
- 模型：`D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`（sha256 0b319bd0…）

## 结论一句话（与 DELIVERY-M2.md 一致）
14B + 本装置下三条 KV 驻留记忆在同一会话内依次答出、多跑逐字节可复现；
但负对照（问车牌）落在 fabricate —— 模型无记忆时同样自信编造 ⇒「答得出 ⇒ 从 KV 读出」不成立，
来源只剩 Q1 那个不可猜住址串被锁定。