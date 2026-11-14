# -*- coding: utf-8 -*-
"""A10: 14B 4-bit prompt 关系判定（只读合成金标，不训练）。"""
import argparse, json, re, sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

SYS = ("你是记忆写入的关系判定器。只输出一个 JSON，不要解释。"
       '格式：{"relation":"correct|new_subject|ambiguous","confidence":0.0}')
USER = """旧事实：{old}
新事实：{new}

判定：
- correct：同一主体、同一属性，新值取代旧值；
- new_subject：同族但不同主体（两辆车/两个手机号/父母老家），两条都保留；
- ambiguous：线索不足，不能确定是纠正还是新增。
只输出 JSON。"""

def parse(txt):
    m = re.search(r"\{.*?\}", txt, re.S)
    if not m:
        return None, None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None, None
    rel = str(d.get("relation", "")).strip()
    if rel not in ("correct", "new_subject", "ambiguous"):
        return None, None
    try:
        conf = float(d.get("confidence"))
    except Exception:
        conf = None
    return rel, conf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.gold, encoding="utf-8")]
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=bnb, device_map="auto", trust_remote_code=True)
    model.eval()

    res = []
    for i, r in enumerate(rows, 1):
        msgs = [{"role": "system", "content": SYS},
                {"role": "user", "content": USER.format(old=r["old"], new=r["new"])}]
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inp = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inp, max_new_tokens=24, do_sample=False,
                                 temperature=None, top_p=None, top_k=None,
                                 pad_token_id=tok.eos_token_id)
        txt = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)
        rel, conf = parse(txt)
        res.append({"id": r["id"], "label": r["label"], "pred": rel,
                    "confidence": conf, "raw": txt.strip()[:120]})
        ok = rel == r["label"]
        print(f"[{i}/{len(rows)}] {r['id']} gold={r['label']} pred={rel} {'OK' if ok else 'X'}", flush=True)

    parse_fail = sum(1 for x in res if x["pred"] is None)
    valid = [x for x in res if x["pred"] is not None]
    acc = sum(1 for x in valid if x["pred"] == x["label"]) / max(1, len(valid))
    cat = [x for x in valid if {x["pred"], x["label"]} == {"correct", "new_subject"}]
    amb = [x for x in valid if x["label"] == "ambiguous"]
    amb_rec = sum(1 for x in amb if x["pred"] == "ambiguous") / max(1, len(amb))
    summary = {"n": len(res), "parse_fail": parse_fail, "valid": len(valid),
               "acc": acc, "catastrophic": len(cat), "catastrophic_ids": [x["id"] for x in cat],
               "ambiguous_recall": amb_rec,
               "confusion": {l: {p: sum(1 for x in valid if x["label"] == l and x["pred"] == p)
                                 for p in ("correct", "new_subject", "ambiguous")}
                             for l in ("correct", "new_subject", "ambiguous")}}
    out = {"model": args.model, "gold": args.gold, "temp": 0,
           "summary": summary, "results": res}
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()