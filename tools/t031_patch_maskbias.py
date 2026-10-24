
import io, sys
p = r'D:\llama-mem\llama.cpp\src\llama-kv-cache.cpp'
s = io.open(p, encoding='utf-8').read()

anchor1 = """    for (uint32_t s = 0; s < n_stream; ++s) {
        // bookkeeping of the KQ mask cells that could change for other tokens of the same sequence
        std::unordered_map<llama_seq_id, uint32_t>              seq_srct;"""

ins1 = """    // [MASKBIAS] optional diagnostic: add a constant bias to the allowed mask cells whose REAL
    // position lies in [lo, hi]. Inactive unless LLAMA_KV_MASK_BIAS="lo:hi:b" is set, so with
    // the variable unset nothing below changes behaviour. Only cells whose value is exactly
    // mask_keep are touched; cells written with mask_drop never are, and positions come from
    // cells.pos_get (a row index is not a position).
    int64_t bias_lo      = 0;
    int64_t bias_hi      = -1;
    double  bias_bval    = 0.0;
    T       bias_add     = llama_cast<T>(0.0f);
    bool    bias_on      = false;
    int64_t bias_touched = 0;
    {
        const char * mbias = getenv("LLAMA_KV_MASK_BIAS");
        if (mbias != nullptr && mbias[0] != '\\0') {
            int    lo = 0;
            int    hi = -1;
            double b  = 0.0;
            if (sscanf(mbias, "%d:%d:%lf", &lo, &hi, &b) == 3) {
                bias_lo   = lo;
                bias_hi   = hi;
                bias_bval = b;
                bias_add  = llama_cast<T>((float) b);
                bias_on   = true;
            } else {
                fprintf(stderr, "[MASKBIAS] malformed LLAMA_KV_MASK_BIAS=%s (want lo:hi:b), ignored\\n", mbias);
            }
        }
    }

""" + anchor1

anchor2 = """                continue;
skip:
                data[idst + j] = mask_drop;
            }

            // [MASKDBG] optional mask trace"""

ins2 = """                continue;
skip:
                data[idst + j] = mask_drop;
            }

            // [MASKBIAS] bump this row. mask_keep is 0.0f in every supported mask type, so
            // "allowed cell + b" is exactly llama_cast<T>(b). Applying it after the row is
            // written also covers a row copied from a previous token of the same sequence.
            if (bias_on && !alibi) {
                for (int64_t j2 = 0; j2 < n_kv; ++j2) {
                    if (cells.is_empty(j2)) {
                        continue;
                    }
                    if (data[idst + j2] != mask_keep) {
                        continue;
                    }
                    const llama_pos p2 = cells.pos_get(j2);
                    if (p2 < bias_lo || p2 > bias_hi) {
                        continue;
                    }
                    data[idst + j2] = bias_add;
                    ++bias_touched;
                }
            }

            // [MASKDBG] optional mask trace"""

anchor3 = """                        fflush(stderr);
                    }
                }
            }
        }
    }
}

template<typename T, bool causal, bool swa, bool is_2d>
static void set_input_kq_mask_impl(const args_set_input_kq_mask & args, T * data) {"""

ins3 = """                        fflush(stderr);
                    }
                }
            }
        }
    }

    if (bias_on) {
        fprintf(stderr, "[MASKBIAS] lo=%lld hi=%lld b=%g n_cells_touched=%lld type=%s\\n",
                (long long) bias_lo, (long long) bias_hi, bias_bval,
                (long long) bias_touched, sizeof(T) == 2 ? "f16" : "f32");
        fflush(stderr);
    }
}

template<typename T, bool causal, bool swa, bool is_2d>
static void set_input_kq_mask_impl(const args_set_input_kq_mask & args, T * data) {"""

for name, a, b in (("anchor1", anchor1, ins1), ("anchor2", anchor2, ins2), ("anchor3", anchor3, ins3)):
    n = s.count(a)
    if n != 1:
        sys.exit("%s occurs %d times" % (name, n))
    s = s.replace(a, b)

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print("patched ok")
