# -*- coding: utf-8 -*-
"""评测已训练的 14B 关系 adapter（test 内部 + held-out）。"""
import argparse, json, re, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

SYS = ("你是记忆写入的关系判定器。只输出一个 JSON，不要解释。"
       '格式：{"relation":"correct|new_subject|ambiguous"}')
USER = """旧事实：{old}
新事实：{new}

判定：
- correct：同一主体、同一属性，新值取代旧值；
- new_subject：同族但不同主体，两条都保留；
- ambiguous：线索不足，不能确定。
只输出 JSON。"""

def parse(t):
    m = re.search(r"\{.*?\}", t, re.S)
    if not m: return None
    try: d = json.loads(m.group(0))
    except Exception: return None
    r = str(d.get("relation", ""))
    return r if r in ("correct", "new_subject", "ambiguous") else None

def eval_set(model, tok, path, tag):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    res = []
    for i, r in enumerate(rows):
        msgs = [{"role":"system","content":SYS},
                {"role":"user","content":USER.format(old=r["old"], new=r["new"])}]
        p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inp = tok(p, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inp, max_new_tokens=24, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        txt = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)
        res.append({"id": r.get("id", "%s-%03d" % (tag, i)), "label": r["label"],
                    "pred": parse(txt)})
    valid = [x for x in res if x["pred"]]
    correct = sum(1 for x in valid if x["pred"] == x["label"])
    cat = [x["id"] for x in valid if {x["pred"], x["label"]} == {"correct","new_subject"}]
    bad = [x["id"] for x in valid if x["label"]=="ambiguous" and x["pred"]=="correct"]
    amb = [x for x in valid if x["label"]=="ambiguous"]
    s = {"n": len(res), "valid": len(valid), "parse_fail": len(res)-len(valid),
         "correct": correct, "acc": correct/max(1,len(valid)),
         "catastrophic": len(cat), "catastrophic_ids": cat,
         "bad_hide": len(bad), "bad_hide_ids": bad,
         "ambiguous_recall": sum(1 for x in amb if x["pred"]=="ambiguous")/max(1,len(amb)),
         "confusion": {l: {q: sum(1 for x in valid if x["label"]==l and x["pred"]==q)
                           for q in ("correct","new_subject","ambiguous")}
                       for l in ("correct","new_subject","ambiguous")},
         "per_class_precision": {q: (sum(1 for x in valid if x["pred"]==q and x["label"]==q) /
                                     max(1, sum(1 for x in valid if x["pred"]==q)))
                                 for q in ("correct","new_subject","ambiguous")}}
    return s, res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--heldout", required=True)
    ap.add_argument("--probe", required=False, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rule-correct", type=int, default=36)
    a = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
    base = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True)
    model = PeftModel.from_pretrained(base, a.adapter)
    model.eval()
    st, rt = eval_set(model, tok, a.test, "test")
    sh, rh = eval_set(model, tok, a.heldout, "held")
    sp, rp = (eval_set(model, tok, a.probe, "probe") if a.probe else (None, None))
    net = sh["correct"] - a.rule_correct
    safe = net - 2 * sh["bad_hide"] - sh["catastrophic"]
    out = {"test": st, "heldout": sh, "probe": sp,
           "rule_v2_heldout_correct": a.rule_correct,
           "net_gain_heldout": net, "safe_gain": safe,
           "verdict_pre_registered": "not_established" if safe < 5 else "established"}
    json.dump({"summary": out, "test_results": rt, "heldout_results": rh, "probe_results": rp},
              open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()