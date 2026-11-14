# -*- coding: utf-8 -*-
"""ocr_image.py — 本地 Tesseract OCR（chi_sim+eng，离线，单进程）。
用法：
  python -X utf8 tools/ocr_image.py --image out/xxx.png [--psm 6] [--out out/xxx.txt] [--json]
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESS = os.environ.get("TESSERACT_EXE", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA = os.environ.get("TESSDATA_DIR", os.path.join(ROOT, "out", "tessdata"))


def ocr(image, lang="chi_sim+eng", psm=6):
    if not os.path.exists(image):
        raise SystemExit("image not found: %s" % image)
    if not os.path.exists(TESS):
        raise SystemExit("tesseract not found: %s" % TESS)
    cmd = [TESS, image, "stdout", "-l", lang, "--psm", str(psm),
           "--tessdata-dir", TESSDATA]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    if p.returncode != 0:
        raise SystemExit("tesseract rc=%s: %s" % (p.returncode, p.stderr[-500:]))
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--lang", default="chi_sim+eng")
    ap.add_argument("--psm", type=int, default=6)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    text = ocr(a.image, a.lang, a.psm)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    if a.json:
        print(json.dumps({"image": a.image, "lang": a.lang, "psm": a.psm,
                          "chars": len(text), "text": text},
                         ensure_ascii=False, indent=1))
    else:
        print(text)


if __name__ == "__main__":
    main()