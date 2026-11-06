# 组级配对真实链路 debug

- query: 我下周去哪？
- kept_group_ids: ['001']
- kept_block_ids/顺序: [2, 1]
- mounted_blocks: [{'seq': 1, 'source_id': 2, 'name': 'mem-d3c98555d713'}, {'seq': 2, 'source_id': 1, 'name': 'mem-b411ba23ac45'}]
- duplicate_blocks: 0
- result: **pass** 

## 组内拼接文本
```
北京开会地点在国贸
下周一我要去北京开会
```

## 每块 intervals/anchor/phrase/reason
- block 2: intervals=[{'kind': 'R', 'start': '2026-11-09', 'end': '2026-11-15', 'phrase': '下周', 'spec': 3}] anchor=2026-11-06T09:00:00 phrase=['下周'] reason=time+topic
- block 1: intervals=[{'kind': 'R', 'start': '2026-11-09', 'end': '2026-11-15', 'phrase': '下周', 'spec': 3}] anchor=2026-11-06T09:00:00 phrase=['下周'] reason=time+topic

## 架构说明
prompt 只含指令+问题；记忆以 KV 块挂载；不存在把完整上下文原文拼进 prompt；本文件只记录 block_ids、块文本与挂载顺序。
