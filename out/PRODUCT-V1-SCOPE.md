# 产品 v1 范围与边界

## 1 是什么
- 单用户、本地、KV-cache 持久记忆助手；
- CLI + HTTP 127.0.0.1；本机 TTS（wav/播放）；
- 不依赖云、网盘、外部 API。

## 2 本版交付
- 记忆：写入、source_hash 判重、topk4、14B、verifier v1；
- meta-v1：条数/空间直答，零模型；
- P1 生命周期：200 软上限、独立 access/archive 表、月 zip、fallback、reheat、audit、backup/drill；
- CLI；本机 TTS；norm/shadow/alignment 能力保留但默认 off。

## 3 本版不承诺
- MT20 达标（11/20）；
- 多轮/冲突/多实体正确；
- QQ 语音、Web/桌面 UI；
- 70B/云端/多用户；
- 40k 生产容量。

## 4 质量边界
- 81 81/81；extra 17/19（L07/L09）；MT20 11/20；
- L05 已冻结 flaky；V9MT04/V9MT08 偶发；
- 默认检索线（K2/P2/subject）不再调参。

## 5 默认开关
- on：meta-v1、cap、access、archive、fallback、audit（决策类）；
- off：K2、v2.2、event、TTS、norm、shadow、confirm、JSON、audit-debug；
- 首次真实归档需用户 `--confirm-first-archive`。

## 6 交付判据
- 能力齐 → drill 过 → 验收清单逐项跑 → 边界文档签字；
- 只交代码不算落地。

## 7 出局项
- QQ 语音（桥只文本）；
- Web/UI；
- 70B/云；
- 多用户/owner；
- 40k 生产容量。