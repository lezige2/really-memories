# 预登记（PREREG）— T-G18 单变量对照

写入时间：跑 G18 之前。跑完不许改本文件。

## 问题
iso_fac_pp18（slot4 = project 同一事实的改写副本，18 格）问 home 会翻。
在**同一个 18 格位置**上，把 slot4 换成一块**无关的第三件真事实**（blk_G_bos_c18, 18 格 = 1 BOS + 17 内容 token），
问 home 还翻不翻？——只改一个变量：slot4 的内容；格数（18）、位置（[3886,3904)）、间距（64）、
home 仍是 [4075,4096)、提问点仍是 4096 全部不变。

## 块
- 路径：D:\llama-mem\kvmem\m2_v1\blk_G_bos_c18.kvmem
- 文本：我的雨伞放在书桌边，伞骨断了一根还留着。
- 18 格 = 1 BOS(151646) + 17 内容 token；与 home(住址) / project(上线日期) / habit(咖啡) 三块不重叠；
  无数字/日期/里程槽位；不含 楼下/阳台/绿萝/小区/家/咖啡/项目/上线。
- 构型：iso_fac_G18（= iso_fac_pp18 的 slot4 换成该块，其余完全相同）

## 预登记的判读（跑前写定，跑完不改）
- **通过** ⇒ 在 18 格这个位置上，副本与无关真事实都通过 ⇒ 只有"同一事实的改写"才翻 ⇒ 该解释得到支持；
- **失败** ⇒ 在 18 格这个位置上，只有副本能通过，任何非副本内容都翻 ⇒ "副本 vs 非副本"才是判别量，
  "改写"的说法不成立（那只是非副本的一种）。

## 判据（跑前就定死）
- 通过 = 两次 iso_fac_G18 问 home 都 ok==True，且答案不含 home 的事实（不含"广陵路"之外的语义即 ok 由 fact_ok 判定），
  即 home 未被 slot4 内容压掉。
- 失败 = 两次都 ok==False（与 iso_fac_pp18 同向）。
- 两次答案不一致（一次通过一次失败）= 不确定，原样上报，不判通过也不判失败。
- 几何必须同时满足：home [4075,4096)、提问点 4096、head_gap_cells==0、slot4 [3886,3904) 18 格、cells_on_live==69。
  几何不满足 ⇒ 本次跑无效，重新跑，不用它判读。

## 同时会核（非判据，防止把基线漂移读成结论）
- iso_dup4 问 home 两次（跑前、跑后各一次）：answer sha256 必须 == 7ec1430d972d949e…
- trace_gate_cpp_sha256：先测。跑前实测 sha256(llama.cpp/src/llama-kv-cache.cpp) =
  c0b1fd4a1193384ea54e83c203c861a5d96d493cdbc8f7dc1dbc15eff164f5ec，
  而历史产物（evidence/score_at/reg_dup4_home.json）记的是 1f140a9b8defd62aa7e42d625a490ab52ad94feb3b41da42c881ffe51d98c7a5。
  两者**不一致**，且 gate 所在行号也已从 2031 挪到 2080。原样记录，不当成我的改动。
- DLL sha256 取自 fixtures.json 的 engine.dll_sha256，两次跑必须一致
