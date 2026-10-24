# 14B 四块重建 —— 交付报告（executor）

2026-10-25 ｜ 产物 kvmem/m2_v1_14b/ ｜ 明细 runs_m14b/blocks_14b.json ｜ 全部数值实测

## 0 判定：4 块全部通过写在跑之前的每一条断言

size 断言式 **size == 1188 + 104464 * n** 在四块上**逐字节成立**（这是本单最硬的一条：
1188 / 104464 此前只是推导，现在有了产物）。（104464 = 每格 4+12 元数据 + 48 层 x 2 x 1088 B/行；
104448 是 KV pool 每 token 步长，两者不同 —— 你纠正得对，我上一单把它写混了。）

| 块 | cells | 内容 token | 首 token | BOS | size | 1188+104464n | sha256 |
|---|---|---|---|---|---|---|---|
| home | 21 | 20 | 151646 | 是 | 2,194,932 | 2,194,932 OK | 73843fc55efd1ab3b587854d49f531c09a347acf003979cfa28e4346f35b0378 |
| project | 18 | 17 | 151646 | 是 | 1,881,540 | 1,881,540 OK | 536eac03f288bb09413efff45608f35e4ce5e9f926ac8854af32ca56baf20016 |
| habit | 12 | 11 | 151646 | 是 | 1,254,756 | 1,254,756 OK | f6f8e85cc55bd4b9759dd71140b88a7e147bd98957aba8f6c8ca19903e0ae9bf |
| project_paraphrase18 | 18 | 17 | 151646 | 是 | 1,881,540 | 1,881,540 OK | a4cf0888467a0f46780ae459eb5d650544918521ee4d80ae332cef74693f8b82 |

路径：D:/llama-mem/kvmem/m2_v1_14b/{home,project,habit,project_paraphrase18}.kvmem
E 格的「project 副本」按你的指示复用同一个 project 块摆两次，**没有**新建副本文件。

## 1 回读 header 五字段（我自己的零引擎解析器，非 block_info.py）

| 块 | n_layer | n_rot_k | n_rot_v | k_type | k_size_row | v_type | v_size_row | v_trans | 解析吃到 EOF |
|---|---|---|---|---|---|---|---|---|---|
| home | 48 | 128 | 64 | 8 (q8_0) | 1088 | 8 | 1088 | 0 | True |
| project | 48 | 128 | 64 | 8 | 1088 | 8 | 1088 | 0 | True |
| habit | 48 | 128 | 64 | 8 | 1088 | 8 | 1088 | 0 | True |
| project_paraphrase18 | 48 | 128 | 64 | 8 | 1088 | 8 | 1088 | 0 | True |

四块解析器都**正好消费到文件末尾**（consumed == size），没有剩余字节、没有截断。

## 2 两次独立编码（两个独立进程）

pass1 -> kvmem/m2_v1_14b/ ；pass2 -> runs_m14b/encode_pass2/（另开进程、另开引擎）

| 块 | pass1 sha | pass2 sha | 与磁盘文件 sha | 三者相同 |
|---|---|---|---|---|
| home | 73843fc5... | 73843fc5... | 73843fc5... | **是** |
| project | 536eac03... | 536eac03... | 536eac03... | **是** |
| habit | f6f8e85c... | f6f8e85c... | f6f8e85c... | **是** |
| project_paraphrase18 | a4cf0888... | a4cf0888... | a4cf0888... | **是** |

**另外还有第三次**：第一次跑因为我自己写错比较式（拿含 BOS 的块 token 去比不含 BOS 的 tokenize 结果）而中止，
中止前已经把 home 写好（runs_m14b/aborted_run1_home.kvmem），它的 sha 也是 73843fc5...，三次逐字节相同。
=> 「逐字节相同」这条证据在 14B 上仍然有意义。

## 3 意外收获：14B 与 7B 的**内容 token id 逐字节相同**

| 块 | 7B 块 tokens | 14B 内容 tokens | 7B[1:] == 14B tokenize | 首 token(7B) |
|---|---|---|---|---|
| home | 21 | 20 | **True** | 151646 |
| project | 18 | 17 | **True** | 151646 |
| habit | 12 | 11 | **True** | 151646 |
| project_paraphrase18 | 18 | 17 | **True** | 151646 |

含义：14B 与 7B 用同一套分词器、同样 BOS 口径，**换模型只换了 KV 载荷**。
=> 规格书 §3.2 预期的「14B 上 control 文本重建为同一 start=3886、同一 target_n=210」有了硬支撑（内容 token 数完全相同）；
=> 四格几何 [4075,4096) / [4014,4032) / [3956,3968) / [3886,3904) 与 7B 完全同构。

## 4 装置（本单实测）

| 项 | 值 |
|---|---|
| model | D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf (8,988,110,240 B) |
| loaded_path | D:\llama-mem\tools\kvshim_vk.dll（引擎自报 _name 回读） |
| DLL sha256 | 9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c |
| DLL mtime | 2026-10-25 00:30:27 |
| bytes_per_token | 104448（= KV pool 每 token 步长，**不是**块文件每格字节） |
| 引擎参数 | n_ctx 8192 / n_seq 8 / gpu 99 / kv q8_0（probe 常量，kvshim.cpp:157-167） |

## 5 文本来源（未重打一个字）

| 块 | 取自 | 校验 |
|---|---|---|
| home / project / habit | tools/m2_visibility_probe.py 的 P.FULL[...]["text"]（:107 / :109 / :111） | 运行时读取 |
| project_paraphrase18 | kvmem/m2_visibility/fixtures.json blocks.variant.project_paraphrase18.text | 脚本内断言 text_sha256 == 03835830816bd7de75b9d86ef2e5225f310fb2260fae5316004c3f8983db54aa（该 sha 是我从 fixtures.json 独立算出、与你/检测员给的串一致） |

注：make_t032_blocks.py 里**没有** pp18 文本（它只有 habit_para12 / filler_bos_c21 / G_bos_c18），
所以 pp18 的原文我从 fixtures.json 取，并加了 sha 哨兵；这一点与你在派单里的写法略有出入，特此说明。

## 6 为什么不能用 block_info.py 判这四块（实测数字）

| 块 | size | (size-708) mod 30480 | 商 | (size-1188) mod 104464 | 商 |
|---|---|---|---|---|---|
| home | 2,194,932 | 30,144 | 71 | **0** | **21** |
| project | 1,881,540 | 21,552 | 61 | **0** | **18** |
| habit | 1,254,756 | 4,368 | 41 | **0** | **12** |
| project_paraphrase18 | 1,881,540 | 21,552 | 61 | **0** | **18** |

块头 n_tokens 与 size 推出的格数一致（21/18/12/18），所以四块**不是**「能被解析但格式错」的那类。

## 7 过程里我停过一次（诚实记录）

第一次跑在 home 上 STOP，原因**不是**格式，是我自己的比较式写错：
我把「含 BOS 的块 token 序列」直接和「kvshim_tokenize 的结果（不含 BOS）」比。
改成 make_t032_blocks.py:107-108 的口径（rb_list[1:] == txt_list 且 rb_list[0] == BOS）后四块全过。
关键：**中止时 size 断言已经通过**（2194932 = 1188 + 104464*21），即格式推导当时就被证实，
没有为了让它过而调过任何常数。

## 8 未验证清单

1. 这四块**尚未**在任何四格 layout 里摆过（本单只到「造块 + 断言」）。位置/门禁/答案全部未跑。
2. **没有**建 runs_m14b/fixtures_14b.json（本单验收不含它）。下一步要用它，且 cells 必须填 21/18/12/18。
3. 14B 块喂给 **7B** 引擎会怎样：未测（按规格书 §2.1 会是 C++ 异常打断进程、无 traceback，故不做这种探测）。
4. n_ctx 8192 下 8 次连跑是否会被桌面占用挤爆显存：未压测（上一单已注明余量 915 MiB）。
5. 块的 KV 数值本身是否正确（即 14B 真按这段文本编码）：只由「重载回 tokens 一致 + fact 召回」间接支持，没有逐张量数值比对。