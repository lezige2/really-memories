# 14B 就绪 + 重编 DLL 交付报告（executor）

撰写：2026-10-25 ｜ 产物目录 kvmem/m2_visibility/runs_m14b/ ｜ 全部数值均为本次实测

## 0 两条判定（先给结论）

| 项 | 判定 | 依据 |
|---|---|---|
| 14B 模型就绪 | **成立** | size 8988110240，全文件 sha256 = 0b319bd0...(上游 LFS oid) **MATCH** |
| 新 DLL 可用 | **成立** | 9edbafa1 打开 14B(n_ctx8192/n_seq8/gpu99/q8_0) 成功，并生成出 token（三块均在位时 fact_ok=True） |
| 全 offload 能否装下 | **能**（n_ctx 4096 与 8192 都实测通过） | 见 3.2 的 memory breakdown 原文 |
| KV 是否全在同一 Vulkan 装置 | **成立** | 48/48 层 dev = Vulkan0；单个 KV buffer 816.00 MiB 全在 Vulkan0 |
| 速度底线 10 tok/s | **不达标** | 实测 tg = 9.18~9.53 t/s（全 offload 已是本机上限） |

## 1 步骤1：完整性判定（判据升级前，供留档）

发现时不完整：零窗扫描（1 MiB/块，全文件）⇒ 全零块 1873 / 共 8571 块（21.9%），聚成 8 段，
缺口合计 1,963,699,616 B（1.83 GiB）。8 段正是 8 路 Range worker 各自区间的尾巴 ⇒ 上段后台在 00:11 被杀。

缺口 8 段（字节区间，1 MiB 粒度）：

    880803840-1123024896   2017460224-2246049792   3098542080-3370123264   4251975680-4493148160
    5362417664-5617221632   6515851264-6740246528   7596933120-7864320000   8754561024-8988110240(文件末)

残缺态 sha256（**已失效，不许当成品引用**）= d6965ce427c65757edda3cc1e1e841c38f7bb92345f2360d738c5a8569f291f0
（原始 json：zero_scan.json；脚本：zero_scan.py）

同时刻无写入进程（size/mtime 20 s 内不变）；也无任何下载进程。

## 2 GGUF 头与张量索引（零引擎，只读头）

脚本 gguf_head.py（自写；tools/block_info.py 不能复用：硬编码 HEADER=708 / STRIDE=30480 且不校验 magic，还把整文件 read 进内存）：

| 项 | 值 |
|---|---|
| magic | GGUF (47475546) |
| version | 3 |
| tensor_count | 579 |
| metadata_kv_count | 30 |
| architecture | qwen2 / DeepSeek R1 Distill Qwen 14B |
| block_count / embedding_length | 48 / 5120 |
| head_count / head_count_kv | 40 / 8 |
| context_length | 131072 |
| file_type / quant | 15 (Q4_K_M) |
| 张量类型分布 | Q4_K 289 / Q6_K 49 / F32 241 |
| **张量索引末尾**（元数据 KV 区在其之前结束，不叫 header_end） | 5,967,251 |
| data_offset（align 32） | 5,967,264 |
| 各张量末字节 | 8,982,142,976 |
| data_offset + 8,982,142,976 | **8,988,110,240 == 文件 size**（精确相等） |

## 3 步骤2：重下 + 权威 oracle 校验

重跑 python -X utf8 tools/dl_14b_par.py（脚本 size==total 故不 truncate，8 路逐块覆盖写）。

    脚本末两行原文：
      downloaded 8988110240 of 8988110240 in 470.0 s
      RENAMED D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf 8988110240

    实测均速 18.2~18.6 MB/s，总耗时 470.0 s，got == total，脚本自己 os.replace 成功。

全文件 sha256 复算（重命名后，对 .gguf）：

    size     = 8988110240
    sha256   = 0b319bd0572f2730bfe11cc751defe82045fad5085b4e60591ac2cd2d9633181
    expected = 0b319bd0572f2730bfe11cc751defe82045fad5085b4e60591ac2cd2d9633181
    结果     = MATCH
    耗时     = 6.9 s（吞吐 1247 MB/s，1 MiB 缓冲分块）
    mtime    = 2026-10-25 00:22:42

## 4 步骤3：加载可行性（llama-cli/llama-completion/llama-bench，build b1-8e5a58d）

装置：AMD Radeon RX 6750 GRE 10GB，Vulkan0 报 (10224 MiB, 起始 free 9426 MiB)。

注意：llama-cli 默认吞掉 loader 日志；必须加 -v（llama-completion）才能拿到 buffer 与逐层 dev。
另外 -no-cnv 在本构建是**非法参数**（会 exit 1），本构建默认开 chat template。

### 4.1 各组 (参数, 结果, 显存)

统一后缀：-ctk q8_0 -ctv q8_0 -fa on -t 8 --no-warmup -fit off

| # | 参数 | 结果 | 显存（llama 自报，MiB） |
|---|---|---|---|
| A | -ngl 99 -c 4096 | **成功**，exit 0 | Vulkan0: total 10224 = free 0 + (self 8897 = model 8148 + context 408 + compute 341) + unaccounted 1327；KV buffer 408.00 MiB |
| D | -ngl 99 -c 8192 | **成功**，exit 0 | Vulkan0: 10224 = 0 + (9309 = 8148 + 816 + 345) + 914；KV buffer 816.00 MiB |
| — | -fa off（配 q8_0 KV） | **非法组合** | llama_init_from_model: 'quantized V cache requires flash_attn to be enabled' |

**没有出现任何 OOM**：-ngl 99 在 4096 与 8192 两种 ctx 下一次就过，无需降档。
（原以为 10 GB 装不下 8.99 GB 权重 + KV + 计算缓冲，实测 8192 才用到 9309/10224 MiB，剩 915 MiB 余量。）

### 4.2 KV 是否全在同一 Vulkan 装置 —— 判定：**成立**

    loadD_ngl99_c8192.log:1558  llama_kv_cache:    Vulkan0 KV buffer size =   816.00 MiB
    loadC_ngl99_v.log:  grep -c 'dev = Vulkan0' = 48，且唯一的 dev 取值就是 Vulkan0（48 个）
    loadC 里的 breakdown 行：Vulkan0 的 context 一栏 = 408（无 Host context 项），即 48 层 KV 全在 Vulkan0

代码依据（不是猜）：
- llama-model.cpp:2936 把 cparams.offload_kqv 作为 offload 传给 llama_kv_cache；offload_kqv 默认 true（llama-context.cpp:4028），kvshim.cpp:157-167 未改它。
- llama-kv-cache.cpp:216-223：buft = offload ? ggml_backend_dev_buffer_type(model.dev_layer(il)) : cpu。
- 即 KV 缓冲**按层**跟该层的设备走。n_gpu_layers=99 >= 48 层 ⇒ 每层 dev_layer 都是 Vulkan0 ⇒ 单一 816 MiB Vulkan0 KV buffer。
- 推论（供下一单登记）：只要 n_gpu_layers < 48，未 offload 的层的 KV 就落在 CPU buffer，装置语义改变。本单实测配置不需要走到那一步。

### 4.3 速度实测（pp / tg 分开）

| 配置 | pp t/s | tg t/s | 备注 |
|---|---|---|---|
| -ngl 99 -p 512 -n 128 -r 3 | pp512 = 189.60 ± 21.32 | tg128 = 9.41 ± 0.11 | 浅 KV |
| -ngl 99 -p 64 -n 128 -r 2 -t 8 | pp64 = 174.74 | tg128 = 9.52 | 浅 KV |
| -ngl 99 -p 64 -n 128 -r 2 -t 12 | pp64 = 175.73 | tg128 = 9.53 | 线程翻倍无收益 |
| **-ngl 99 -p 512 -n 128 -d 4096 -r 2** | **pp512@d4096 = 38.19 ± 0.05** | **tg128@d4096 = 9.18 ± 0.11** | **最接近真实工况（4096 深度）** |
| 走 shim 实路（n_ctx 8192, pos 21/18/12, n_predict=24） | — | 8.24 / 8.39 / 8.26 | 含 tokenize 与 24 token 的固定开销 |

**tg 上限 ≈ 9.2~9.5 t/s < 用户底线 10 tok/s**。全 offload 已是本机最好情形；部分 offload 只会更慢。
所以不存在「KV 同装置 vs ≥10 t/s」的二选一：只有一个可行装置，它速度略低于底线（差约 8%）。

### 4.4 推荐启动参数（一行，实测跑通）

    D:/llama-mem/build-vulkan/bin/llama-cli.exe -m D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf -ngl 99 -c 8192 -ctk q8_0 -ctv q8_0 -fa on -t 8 --no-warmup -fit off -p "2+2=" -n 8

（对应实验路径的等价一组：kvshim_open(model, n_ctx=8192, n_seq=8, n_gpu_layers=99, kv_q8=1)，
 即 probe 的 P.N_CTX=8192 / P.GPU=99 / P.KV=q8_0，源码常量见 kvshim.cpp:157-167。日志 tail 见 loadD_ngl99_c8192.log 末 4 行。）

## 5 步骤4：DLL 登记与归档

| 项 | 编前 | 编后 |
|---|---|---|
| build-vulkan/src/libllama.a | size 8622856, mtime 2026-10-24 23:43:27, sha 3bdbac810054da52 | **完全相同（未变）** |
| tools/kvshim_vk.dll | size 50007552, mtime 2026-10-24 23:59:42, sha 3a726dbd9e264fac... | size 50007552, mtime 2026-10-25 00:30:27, sha **9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c** |

编译两步输出原文（build_14b.log）：

    STEP1: [1/4] Performing build step for 'vulkan-shaders-gen' / ninja: no work to do. / STEP1_EXIT=0
    STEP2: == building kvshim_vk.dll / ok -> D:\llama-mem\tools\kvshim_vk.dll / STEP2_EXIT=0

**必须照实说的一点**：STEP1 报 ninja: no work to do ⇒ **libllama.a 的 mtime 没有变**。
原因是本单没有任何源码改动（边界也不允许改），所以库里没有该编的东西；所谓「针对 14B 重编」在代码层面是空操作。
DLL 的 sha 变了（3a726dbd -> 9edbafa1），size 一字不差，属于**重链接**（链接时间戳/构建 id），不是功能改动。
因此验收判据里「libllama.a mtime 变了 且 新 DLL 的 sha256 ≠ 3a726dbd」这条：前半**不成立**（本来就没有可编内容），后半成立。
是否算通过请你定；我的结论是：二进制确实重新产出了 9edbafa1，但它与 3a726dbd 的差异不是代码差异。

### 5.1 归档（§8.7 首次真正执行）

| 归档文件 | size | sha256 | 二次复算 |
|---|---|---|---|
| runs_m14b/dll_archive/kvshim_vk_9edbafa1.dll | 50007552 | 9edbafa1...b2e5c | **两次相同**，且等于源文件 |
| runs_m14b/dll_archive/kvshim_vk_c7ea09bb_DLL_THAT_PRODUCED_EF.dll | 49877504 | c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8 | **两次相同** |

**重要发现**：HANDOFF §8.7 说「产出 E/F 的 c7ea09bb 全盘已无副本 ⇒ 那批不可复跑」。
这次在 kvmem/m2_visibility/runs_mask/kvshim_vk.dll.bak 找到了一份，sha 逐位等于 c7ea09bb...，已复制归档（只复制，未动 runs_mask/）。
⇒ E/F 的二进制 provenance 可以恢复，「不可复跑」这条结论应当撤回或降级。

### 5.2 loaded_path

驱动实测加载路径 = D:\llama-mem\tools\kvshim_vk.dll（ctypes WinDLL 的 _name 原样回读，见 dll_smoke_14b.json 的 loaded_path），
该路径文件 sha256 = 9edbafa1...（打开后回读复算，不是猜）。build-vulkan/bin/kvshim_vk.dll 不存在。

## 6 用新 DLL 打开 14B 的实测（验收「二进制可用」）

dll_smoke_14b.json / dll_smoke_gen_14b.json

| 项 | 实测 |
|---|---|
| kvshim_open 14B | 成功，5.3 s |
| bytes_per_token | **104448**（= 检测员规格书 §2.2 推导值 104,448，逐字节吻合） |
| pool_bytes | 855638016 = 104448 x 8192 |
| home 编码格数 | **21**（7B 也是 21，14B 分词器未变格数） |
| project / habit 格数 | **18 / 12**（与 7B 相同） |
| pos_max（home） | 20 ⇒ 首 token 在位置 0，BOS 口径未变 |
| 生成 token | **成功**：home / project / habit 三块各生成 24 token，fact_ok 全为 True |
| 生成速度（走 shim） | 8.24 / 8.39 / 8.26 t/s |

附带证实一条已知规则：把提问放在 pos=4096 而 KV 只填了 0..20（gap≠0）时，返回值是**空串、0.0 s、无任何诊断** ——
与 HANDOFF §3 事实 1 一致，不是 DLL 故障。（dll_smoke_14b.json 那次就是这个情形。）

## 7 对下一单（14B 四格）的直接影响

1. 规格书 §3.1 的 fixtures_14b.json 用 n_ctx=8192 —— **实测装得下，不必降 P.GPU，不必降 n_ctx**。
2. 规格书 §2.4 担心的「14B 分词器是否给出 21/18/12/18 格」已由实测提前确认：**是**（home 21 / project 18 / habit 12）。
3. 规格书 §2.2 的每格 104,464 B 已被 kvshim 实测 bytes_per_token = 104448 证实。
4. 四格不会被速度卡住：P.N_PREDICT = 24，按 9.2 t/s 单格生成约 2.6 s；控制门禁要 prefill 210 token，按 pp@d4096 38 t/s 约 5.5 s。
   用户 10 tok/s 的底线只影响「日常对话」体感，不影响四格重跑的可行性。

## 8 未验证清单（不许当已知）

1. 8192 ctx 下剩余 915 MiB 余量是否够**桌面长期占用**：本单测试时桌面占用未知；若用户开浏览器/游戏，可能挤爆。未做压力测试。
2. 8 路并行下载的 8 段缺口是否可能**内容正确而只是看来为零**：不可能（全零 1 MiB 块 memcmp 相等），但未做反向证明。
3. 新 DLL 9edbafa1 与旧 3a726dbd 的**功能等价性**：未有旧文件可比（已被覆盖），只能从「同一份 libllama.a + 无源码改动」推断，属推导不是实测。
4. n_ctx 8192 下连续长时间生成（>2000 token）是否触发 Vulkan 显存碎片/降速：未测。
5. 部分 offload（n_gpu_layers < 48）下的实际速度与 KV 分裂行为：本单不需要，**未测**。
6. 旧 DLL 3a726dbd 已从磁盘消失（我编前只记了 sha 未先归档，这是我的流程疏漏）：无法再复算该二进制。

## 9 本单未做的事（边界）

- 未改任何源码；未动 blocks/、m2_v1/、fixtures.json、_gate.py、E10-NEXT2.md、别人的 runs_*。
- 未跑 7B 任何实验；未并发跑两个引擎（每次只有一个进程，串行）。
- 规格书要求的造块/四格重跑：**未开工**，等 lead 确认派单。