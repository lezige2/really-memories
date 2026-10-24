import os, sys, json, struct, hashlib

P = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf.dl"

# ggml type table: id -> (name, block_elems, block_bytes)
TYPES = {
 0:("F32",1,4),1:("F16",1,2),2:("Q4_0",32,18),3:("Q4_1",32,20),
 6:("Q5_0",32,22),7:("Q5_1",32,24),8:("Q8_0",32,34),9:("Q8_1",32,36),
 10:("Q2_K",256,84),11:("Q3_K",256,110),12:("Q4_K",256,144),13:("Q5_K",256,176),
 14:("Q6_K",256,210),15:("Q8_K",256,292),
 16:("IQ2_XXS",256,66),17:("IQ2_XS",256,74),18:("IQ3_XXS",256,98),19:("IQ1_S",256,50),
 20:("IQ4_NL",32,18),21:("IQ3_S",256,110),22:("IQ2_S",256,82),23:("IQ4_XS",256,136),
 24:("I8",1,1),25:("I16",1,2),26:("I32",1,4),27:("I64",1,8),28:("F64",1,8),
 29:("IQ1_M",256,56),30:("BF16",1,2),
}
VT = {0:"u8",1:"i8",2:"u16",3:"i16",4:"u32",5:"i32",6:"f32",7:"bool",8:"str",9:"arr",10:"u64",11:"i64",12:"f64"}
SCALAR = {0:("<B",1),1:("<b",1),2:("<H",2),3:("<h",2),4:("<I",4),5:("<i",4),6:("<f",4),7:("<?",1),10:("<Q",8),11:("<q",8),12:("<d",8)}

class R:
    def __init__(self, f): self.f=f; self.pos=0
    def take(self,n):
        b=self.f.read(n); 
        if len(b)!=n: raise EOFError("short read at %d want %d got %d"%(self.pos,n,len(b)))
        self.pos+=n; return b
    def u32(self): return struct.unpack("<I",self.take(4))[0]
    def u64(self): return struct.unpack("<Q",self.take(8))[0]
    def s(self):
        n=self.u64(); return self.take(n).decode("utf-8","replace")

def read_val(r, vt, depth=0):
    if vt==8: return ("str", r.s())
    if vt==9:
        et=r.u32(); n=r.u64()
        vals=[]
        for i in range(n):
            vals.append(read_val(r, et, depth+1))
        kind = VT.get(et,"?")
        if kind=="str":
            return ("arr_str", n, vals[:4])
        if depth>0 or n<=8:
            return ("arr", kind, n, vals)
        # large numeric array: keep head/tail only
        return ("arr", kind, n, (vals[:4], vals[-2:]))
    if vt in SCALAR:
        fmt,sz = SCALAR[vt]; return struct.unpack(fmt, r.take(sz))[0]
    raise ValueError("bad value type %d at %d"%(vt,r.pos))

f=open(P,"rb")
r=R(f)
magic=f.read(4); r.pos=4
version=r.u32(); n_tensors=r.u64(); n_kv=r.u64()
meta={}
for i in range(n_kv):
    k=r.s(); vt=r.u32(); v=read_val(r,vt)
    meta[k]=v
tensors=[]
for i in range(n_tensors):
    name=r.s(); nd=r.u32()
    dims=[r.u64() for _ in range(nd)]
    tt=r.u32(); off=r.u64()
    tensors.append({"name":name,"dims":dims,"type":tt,"off":off})
hdr_end=r.pos
align = meta.get("general.alignment", 32)
align = align[1] if isinstance(align,tuple) else align
data_off = (hdr_end + align - 1)//align*align

size=os.path.getsize(P)
worst=0; unknown=[]; tcount={}
for t in tensors:
    nm=t["type"]
    if nm not in TYPES: unknown.append(t["name"]); continue
    _,be,bb = TYPES[nm]
    nel=1
    for d in t["dims"]: nel*=d
    if nel % be: 
        unknown.append(t["name"]+"(uneven)"); continue
    nb = nel//be*bb
    t["nbytes"]=nb
    worst=max(worst, t["off"]+nb)
    tcount[TYPES[nm][0]]=tcount.get(TYPES[nm][0],0)+1

print(json.dumps({
 "file": P, "file_size": size,
 "magic": magic.decode("latin1"), "magic_hex": magic.hex(),
 "version": version, "n_tensors": n_tensors, "n_kv": n_kv,
 "header_end": hdr_end, "alignment": align, "data_offset": data_off,
 "data_area_bytes": size-data_off,
 "tensor_data_max_end": worst,
 "computed_total_expected": data_off+worst,
 "size_match_exact": (data_off+worst)==size,
 "size_delta": size-(data_off+worst),
 "tensor_type_hist": tcount,
 "unknown_types_for": unknown,
 "meta_keys": list(meta.keys()),
}, indent=1, ensure_ascii=False))

def show(k):
    if k in meta:
        v=meta[k]
        print(k,"=",v if not isinstance(v,tuple) or len(str(v))<200 else str(v)[:200])
for k in ["general.architecture","general.name","general.file_type","general.quantization_version",
          "qwen2.block_count","qwen2.embedding_length","qwen2.feed_forward_length","qwen2.attention.head_count",
          "qwen2.attention.head_count_kv","qwen2.attention.layer_norm_rms_epsilon","qwen2.context_length",
          "qwen2.rope.freq_base","tokenizer.ggml.model","tokenizer.ggml.bos_token_id","tokenizer.ggml.eos_token_id"]:
    show(k)
print("first8_tensors:", [(t["name"],t["dims"],TYPES.get(t["type"],("?",))[0],t["off"]) for t in tensors[:8]])
print("last3_tensors:", [(t["name"],t["dims"],TYPES.get(t["type"],("?",))[0],t["off"]) for t in tensors[-3:]])
print("tokenizer tokens count:", meta.get("tokenizer.ggml.tokens",("?",))[1] if isinstance(meta.get("tokenizer.ggml.tokens"),tuple) else "?")
