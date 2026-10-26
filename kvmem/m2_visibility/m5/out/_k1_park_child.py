# -*- coding: utf-8 -*-
"""K1 park child: self-managed Vulkan instance/device, park (destroy device),
then pure-file save cycles.  NO model, NO kill, NO GPU after `parked`.

Vulkan is used directly through vulkan-1.dll so the process can truly reach
"device destroyed, process alive"; this is the point the frozen llama path
cannot reach (ggml's global vk_instance destroys devices only at static
destruction / process exit, and kvshim_close does not destroy the device).

State log: one `[STATE name t_mono=... t_wall=...] {...}` line per transition,
flushed to stdout AND the state-log file (the parent polls the file, not stdout).
"""
import argparse
import ctypes
import hashlib
import json
import os
import shutil
import struct
import sys
import threading
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
K1 = OUT / "kill_k1"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
from session_state import _durable_replace  # noqa: E402
import session_state as _ss  # noqa: E402

T0 = time.monotonic()
VK = ctypes.WinDLL("vulkan-1.dll")

# ---- K1 STALL-LOCATE instrumentation (log/timing only; no semantic change) ----
PHASE = {"name": "start", "detail": {}}
PHASE_LOCK = threading.Lock()
PHASE_HISTORY = []
SYS = []
SYS_LOCK = threading.Lock()
TRACE_F = None
TRACE_LOCK = threading.Lock()
TRACE_PATH = None
TRACE_COUNT = 0
_ORIG_MOVEFILE = None


def start_trace(path):
    global TRACE_F, TRACE_PATH, TRACE_COUNT
    TRACE_PATH = str(path)
    TRACE_F = open(path, "w", encoding="utf-8", buffering=1)
    TRACE_COUNT = 0
    line = json.dumps({"op": "trace_start", "t": time.perf_counter(), "path": TRACE_PATH},
                      ensure_ascii=False, separators=(",", ":"))
    TRACE_F.write(line + "\n")
    TRACE_F.flush()
    os.fsync(TRACE_F.fileno())


def stop_trace():
    global TRACE_F
    if TRACE_F is None:
        return
    try:
        line = json.dumps({"op": "trace_end", "t": time.perf_counter(), "count": TRACE_COUNT},
                          ensure_ascii=False, separators=(",", ":"))
        with TRACE_LOCK:
            TRACE_F.write(line + "\n")
            TRACE_F.flush()
            os.fsync(TRACE_F.fileno())
    except Exception:  # noqa: BLE001
        pass
    try:
        with TRACE_LOCK:
            TRACE_F.close()
    except Exception:  # noqa: BLE001
        pass
    TRACE_F = None


def set_phase(name, **detail):
    t = time.perf_counter()
    with PHASE_LOCK:
        PHASE["name"] = name
        PHASE["detail"] = dict(detail)
        PHASE_HISTORY.append({"t": t, "phase": name, "detail": dict(detail)})


def phase_snapshot():
    with PHASE_LOCK:
        return PHASE["name"], dict(PHASE["detail"])


def record_sys(op, t0, t1, **extra):
    global TRACE_COUNT
    rec = {"op": op, "t0": t0, "t1": t1, "elapsed_ms": round((t1 - t0) * 1000.0, 3)}
    rec.update(extra)
    with SYS_LOCK:
        SYS.append(rec)
    if TRACE_F is not None:
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        with TRACE_LOCK:
            TRACE_F.write(line + "\n")
            TRACE_F.flush()
            os.fsync(TRACE_F.fileno())
            TRACE_COUNT += 1


def install_movefile_trace():
    global _ORIG_MOVEFILE
    if _ORIG_MOVEFILE is not None:
        return
    orig = _ss._movefile_ex_write_through

    def traced(tmp, dst):
        t0 = time.perf_counter()
        record_sys("MoveFileExW_begin", t0, t0, tmp=str(tmp), dst=str(dst))
        try:
            ok = orig(tmp, dst)
        finally:
            t1 = time.perf_counter()
            record_sys("MoveFileExW_end", t0, t1, tmp=str(tmp), dst=str(dst), ok=bool(ok) if 'ok' in locals() else None)
        return ok

    _ss._movefile_ex_write_through = traced
    _ORIG_MOVEFILE = orig


class Heartbeat:
    def __init__(self, log, interval=0.2):
        self.log = log
        self.interval = interval
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, name="k1-heartbeat", daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        while not self.stop.wait(self.interval):
            name, detail = phase_snapshot()
            try:
                self.log.beat(name, **detail)
            except Exception:  # noqa: BLE001
                pass

    def shutdown(self):
        self.stop.set()
        self.thread.join(timeout=2.0)


VK = ctypes.WinDLL("vulkan-1.dll")
VK_API_VERSION_1_0 = (1 << 22)


def wall():
    return time.strftime("%Y-%m-%dT%H:%M:%S") + (".%03d" % (int(time.time() * 1000) % 1000)) + time.strftime("%z")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def parse_header(path):
    with open(path, "rb") as f:
        h = f.read(12)
    n = struct.unpack("<i", h[8:12])[0]
    return {"n_tokens": int(n), "bytes": os.path.getsize(path), "sha16": sha16(path)}


class Logger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, "a", encoding="utf-8", buffering=1)
        self._lock = threading.RLock()

    def st(self, state_name, **detail):
        rec = {"state": state_name, "t_mono": round(time.monotonic() - T0, 6), "t_wall": wall(), **detail}
        line = "[STATE %s t_mono=%.6f t_wall=%s] %s" % (state_name, rec["t_mono"], rec["t_wall"],
                                                       json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
        with self._lock:
            print(line, flush=True)
            self.f.write(line + "\n")
            self.f.flush()
        return rec

    def beat(self, phase, **detail):
        t = round(time.monotonic() - T0, 6)
        line = "[HEARTBEAT t_mono=%.6f t_wall=%s phase=%s] %s" % (
            t, wall(), phase, json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
        with self._lock:
            self.f.write(line + "\n")
            self.f.flush()

    def close(self):
        try:
            with self._lock:
                self.f.close()
        except Exception:
            pass


class VkApplicationInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p),
                ("pApplicationName", ctypes.c_char_p), ("applicationVersion", ctypes.c_uint32),
                ("pEngineName", ctypes.c_char_p), ("engineVersion", ctypes.c_uint32),
                ("apiVersion", ctypes.c_uint32)]


class VkInstanceCreateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("pApplicationInfo", ctypes.c_void_p), ("enabledLayerCount", ctypes.c_uint32),
                ("ppEnabledLayerNames", ctypes.c_void_p), ("enabledExtensionCount", ctypes.c_uint32),
                ("ppEnabledExtensionNames", ctypes.c_void_p)]


class VkQueueFamilyProperties(ctypes.Structure):
    _fields_ = [("queueFlags", ctypes.c_uint32), ("queueCount", ctypes.c_uint32),
                ("timestampValidBits", ctypes.c_uint32), ("minImageTransferGranularity", ctypes.c_uint32 * 3)]


class VkDeviceQueueCreateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("queueFamilyIndex", ctypes.c_uint32), ("queueCount", ctypes.c_uint32),
                ("pQueuePriorities", ctypes.POINTER(ctypes.c_float))]


class VkDeviceCreateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("queueCreateInfoCount", ctypes.c_uint32), ("pQueueCreateInfos", ctypes.c_void_p),
                ("enabledLayerCount", ctypes.c_uint32), ("ppEnabledLayerNames", ctypes.c_void_p),
                ("enabledExtensionCount", ctypes.c_uint32), ("ppEnabledExtensionNames", ctypes.c_void_p),
                ("pEnabledFeatures", ctypes.c_void_p)]


class VkBufferCreateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("size", ctypes.c_uint64), ("usage", ctypes.c_uint32), ("sharingMode", ctypes.c_uint32),
                ("queueFamilyIndexCount", ctypes.c_uint32), ("pQueueFamilyIndices", ctypes.c_void_p)]


class VkMemoryRequirements(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint64), ("alignment", ctypes.c_uint64), ("memoryTypeBits", ctypes.c_uint32)]


class VkMemoryAllocateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p),
                ("allocationSize", ctypes.c_uint64), ("memoryTypeIndex", ctypes.c_uint32)]


class VkMemoryType(ctypes.Structure):
    _fields_ = [("propertyFlags", ctypes.c_uint32), ("heapIndex", ctypes.c_uint32)]


class VkMemoryHeap(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint64), ("flags", ctypes.c_uint32)]


class VkPhysicalDeviceMemoryProperties(ctypes.Structure):
    _fields_ = [("memoryTypeCount", ctypes.c_uint32), ("memoryTypes", VkMemoryType * 32),
                ("memoryHeapCount", ctypes.c_uint32), ("heaps", VkMemoryHeap * 16)]


class VkCommandPoolCreateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("queueFamilyIndex", ctypes.c_uint32)]


class VkCommandBufferAllocateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("commandPool", ctypes.c_void_p),
                ("level", ctypes.c_uint32), ("commandBufferCount", ctypes.c_uint32)]


class VkCommandBufferBeginInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("pInheritanceInfo", ctypes.c_void_p)]


class VkFenceCreateInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32)]


class VkSubmitInfo(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_uint32), ("pNext", ctypes.c_void_p),
                ("waitSemaphoreCount", ctypes.c_uint32), ("pWaitSemaphores", ctypes.c_void_p),
                ("pWaitDstStageMask", ctypes.c_void_p), ("commandBufferCount", ctypes.c_uint32),
                ("pCommandBuffers", ctypes.POINTER(ctypes.c_void_p)),
                ("signalSemaphoreCount", ctypes.c_uint32), ("pSignalSemaphores", ctypes.c_void_p)]


def _proto(name, argtypes, restype):
    f = getattr(VK, name)
    f.argtypes = argtypes
    f.restype = restype
    return f


def _call(calls, name, fn, *args):
    t = time.perf_counter()
    try:
        rc = fn(*args)
        err = None
    except Exception as e:  # noqa: BLE001
        rc, err = None, type(e).__name__ + ": " + str(e)
    dt = round((time.perf_counter() - t) * 1000.0, 4)
    calls.append({"call": name, "rc": rc, "ms": dt, "error": err})
    return rc


def vulkan_park(log, calls):
    set_phase("vulkan_init")
    log.st("vulkan_init")
    vkCreateInstance = _proto("vkCreateInstance",
        [ctypes.POINTER(VkInstanceCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkDestroyInstance = _proto("vkDestroyInstance", [ctypes.c_void_p, ctypes.c_void_p], None)
    vkEnumeratePhysicalDevices = _proto("vkEnumeratePhysicalDevices",
        [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkGetPhysicalDeviceProperties = _proto("vkGetPhysicalDeviceProperties",
        [ctypes.c_void_p, ctypes.c_void_p], None)
    vkGetPhysicalDeviceQueueFamilyProperties = _proto("vkGetPhysicalDeviceQueueFamilyProperties",
        [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(VkQueueFamilyProperties)], None)
    vkCreateDevice = _proto("vkCreateDevice",
        [ctypes.c_void_p, ctypes.POINTER(VkDeviceCreateInfo), ctypes.c_void_p,
         ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkDestroyDevice = _proto("vkDestroyDevice", [ctypes.c_void_p, ctypes.c_void_p], None)
    vkGetDeviceQueue = _proto("vkGetDeviceQueue",
        [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)], None)
    vkCreateBuffer = _proto("vkCreateBuffer",
        [ctypes.c_void_p, ctypes.POINTER(VkBufferCreateInfo), ctypes.c_void_p,
         ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkDestroyBuffer = _proto("vkDestroyBuffer", [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], None)
    vkGetBufferMemoryRequirements = _proto("vkGetBufferMemoryRequirements",
        [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(VkMemoryRequirements)], None)
    vkGetPhysicalDeviceMemoryProperties = _proto("vkGetPhysicalDeviceMemoryProperties",
        [ctypes.c_void_p, ctypes.POINTER(VkPhysicalDeviceMemoryProperties)], None)
    vkAllocateMemory = _proto("vkAllocateMemory",
        [ctypes.c_void_p, ctypes.POINTER(VkMemoryAllocateInfo), ctypes.c_void_p,
         ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkFreeMemory = _proto("vkFreeMemory", [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], None)
    vkBindBufferMemory = _proto("vkBindBufferMemory",
        [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64], ctypes.c_int)
    vkCreateCommandPool = _proto("vkCreateCommandPool",
        [ctypes.c_void_p, ctypes.POINTER(VkCommandPoolCreateInfo), ctypes.c_void_p,
         ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkDestroyCommandPool = _proto("vkDestroyCommandPool", [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], None)
    vkAllocateCommandBuffers = _proto("vkAllocateCommandBuffers",
        [ctypes.c_void_p, ctypes.POINTER(VkCommandBufferAllocateInfo),
         ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkFreeCommandBuffers = _proto("vkFreeCommandBuffers",
        [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)], None)
    vkBeginCommandBuffer = _proto("vkBeginCommandBuffer",
        [ctypes.c_void_p, ctypes.POINTER(VkCommandBufferBeginInfo)], ctypes.c_int)
    vkEndCommandBuffer = _proto("vkEndCommandBuffer", [ctypes.c_void_p], ctypes.c_int)
    vkCreateFence = _proto("vkCreateFence",
        [ctypes.c_void_p, ctypes.POINTER(VkFenceCreateInfo), ctypes.c_void_p,
         ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkDestroyFence = _proto("vkDestroyFence", [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], None)
    vkResetFences = _proto("vkResetFences", [ctypes.c_void_p, ctypes.c_uint32,
                                             ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int)
    vkQueueSubmit = _proto("vkQueueSubmit", [ctypes.c_void_p, ctypes.c_uint32,
                                             ctypes.POINTER(VkSubmitInfo), ctypes.c_void_p], ctypes.c_int)
    vkWaitForFences = _proto("vkWaitForFences", [ctypes.c_void_p, ctypes.c_uint32,
                                                 ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint32,
                                                 ctypes.c_uint64], ctypes.c_int)
    vkDeviceWaitIdle = _proto("vkDeviceWaitIdle", [ctypes.c_void_p], ctypes.c_int)

    app = VkApplicationInfo(0, None, b"k1-park-child", 1, b"kvshim", 1, VK_API_VERSION_1_0)
    ici = VkInstanceCreateInfo(0, None, 0, ctypes.cast(ctypes.pointer(app), ctypes.c_void_p),
                               0, None, 0, None)
    inst = ctypes.c_void_p()
    rc = _call(calls, "vkCreateInstance", vkCreateInstance, ctypes.byref(ici), None, ctypes.byref(inst))
    log.st("instance_created", rc=rc, instance=bool(inst.value))
    if rc != 0 or not inst.value:
        return {"ok": False, "error": "vkCreateInstance rc=%r" % rc}

    n = ctypes.c_uint32(0)
    rc = _call(calls, "vkEnumeratePhysicalDevices.count", vkEnumeratePhysicalDevices, inst, ctypes.byref(n), None)
    if rc != 0 or n.value < 1:
        return {"ok": False, "error": "no physical device rc=%r n=%d" % (rc, n.value)}
    arr = (ctypes.c_void_p * n.value)()
    rc = _call(calls, "vkEnumeratePhysicalDevices.list", vkEnumeratePhysicalDevices, inst, ctypes.byref(n), arr)
    if rc != 0:
        return {"ok": False, "error": "enumerate list rc=%r" % rc}
    phys = arr[0]
    props = ctypes.create_string_buffer(4096)
    rc = _call(calls, "vkGetPhysicalDeviceProperties", vkGetPhysicalDeviceProperties, phys,
               ctypes.cast(props, ctypes.c_void_p))
    raw = props.raw
    api = struct.unpack_from("<I", raw, 0)[0]
    driver = struct.unpack_from("<I", raw, 4)[0]
    vendor = struct.unpack_from("<I", raw, 8)[0]
    deviceid = struct.unpack_from("<I", raw, 12)[0]
    devtype = struct.unpack_from("<I", raw, 16)[0]
    name = raw[20:276].split(b"\x00", 1)[0].decode("utf-8", "replace")
    log.st("physical_device", rc=rc, name=name, api_version=api, driver_version=driver,
           vendor_id=vendor, device_id=deviceid, device_type=devtype, device_count=n.value)

    qn = ctypes.c_uint32(0)
    vkGetPhysicalDeviceQueueFamilyProperties(phys, ctypes.byref(qn), None)
    qarr = (VkQueueFamilyProperties * max(1, qn.value))()
    vkGetPhysicalDeviceQueueFamilyProperties(phys, ctypes.byref(qn), qarr)
    qf = None
    for i in range(qn.value):
        if (int(qarr[i].queueFlags) & 0x1) and int(qarr[i].queueCount) > 0:
            qf = i
            break
    if qf is None:
        return {"ok": False, "error": "no graphics queue family"}
    log.st("queue_family", index=qf, flags=int(qarr[qf].queueFlags), queue_count=int(qarr[qf].queueCount))

    prio = ctypes.c_float(1.0)
    qci = VkDeviceQueueCreateInfo(2, None, 0, qf, 1, ctypes.pointer(prio))
    dci = VkDeviceCreateInfo(3, None, 0, 1, ctypes.cast(ctypes.pointer(qci), ctypes.c_void_p),
                             0, None, 0, None, None)
    dev = ctypes.c_void_p()
    rc = _call(calls, "vkCreateDevice", vkCreateDevice, phys, ctypes.byref(dci), None, ctypes.byref(dev))
    log.st("device_created", rc=rc, device=bool(dev.value))
    if rc != 0 or not dev.value:
        return {"ok": False, "error": "vkCreateDevice rc=%r" % rc}
    queue = ctypes.c_void_p()
    vkGetDeviceQueue(dev, qf, 0, ctypes.byref(queue))

    bci = VkBufferCreateInfo(12, None, 0, 4096, 0x20, 0, 0, None)
    buf = ctypes.c_void_p()
    rc = _call(calls, "vkCreateBuffer", vkCreateBuffer, dev, ctypes.byref(bci), None, ctypes.byref(buf))
    log.st("buffer_created", rc=rc)
    if rc != 0 or not buf.value:
        return {"ok": False, "error": "vkCreateBuffer rc=%r" % rc}
    req = VkMemoryRequirements()
    vkGetBufferMemoryRequirements(dev, buf, ctypes.byref(req))
    memprops = VkPhysicalDeviceMemoryProperties()
    vkGetPhysicalDeviceMemoryProperties(phys, ctypes.byref(memprops))
    mi = None
    for i in range(memprops.memoryTypeCount):
        flags = int(memprops.memoryTypes[i].propertyFlags)
        if (flags & 0x2) and (flags & 0x4) and ((int(req.memoryTypeBits) >> i) & 1):
            mi = i
            break
    if mi is None:
        return {"ok": False, "error": "no host-visible coherent memory type"}
    mai = VkMemoryAllocateInfo(10, None, int(req.size), mi)
    mem = ctypes.c_void_p()
    rc = _call(calls, "vkAllocateMemory", vkAllocateMemory, dev, ctypes.byref(mai), None, ctypes.byref(mem))
    log.st("memory_allocated", rc=rc, size=int(req.size), memory_type=mi)
    if rc != 0 or not mem.value:
        return {"ok": False, "error": "vkAllocateMemory rc=%r" % rc}
    rc = _call(calls, "vkBindBufferMemory", vkBindBufferMemory, dev, buf, mem, 0)
    log.st("buffer_bound", rc=rc)
    if rc != 0:
        return {"ok": False, "error": "vkBindBufferMemory rc=%r" % rc}

    pci = VkCommandPoolCreateInfo(39, None, 0, qf)
    pool = ctypes.c_void_p()
    rc = _call(calls, "vkCreateCommandPool", vkCreateCommandPool, dev, ctypes.byref(pci), None, ctypes.byref(pool))
    log.st("command_pool_created", rc=rc)
    if rc != 0 or not pool.value:
        return {"ok": False, "error": "vkCreateCommandPool rc=%r" % rc}
    cai = VkCommandBufferAllocateInfo(40, None, pool, 0, 1)
    cmdarr = (ctypes.c_void_p * 1)()
    rc = _call(calls, "vkAllocateCommandBuffers", vkAllocateCommandBuffers, dev, ctypes.byref(cai), cmdarr)
    log.st("command_buffer_allocated", rc=rc, command_buffer=bool(cmdarr[0]))
    if rc != 0 or not cmdarr[0]:
        return {"ok": False, "error": "vkAllocateCommandBuffers rc=%r" % rc}
    cmd = ctypes.c_void_p(cmdarr[0])
    begin = VkCommandBufferBeginInfo(42, None, 0, None)
    rc = _call(calls, "vkBeginCommandBuffer", vkBeginCommandBuffer, cmd, ctypes.byref(begin))
    log.st("command_buffer_begin", rc=rc)
    if rc != 0:
        return {"ok": False, "error": "vkBeginCommandBuffer rc=%r" % rc}
    rc = _call(calls, "vkEndCommandBuffer", vkEndCommandBuffer, cmd)
    log.st("command_buffer_end", rc=rc)
    if rc != 0:
        return {"ok": False, "error": "vkEndCommandBuffer rc=%r" % rc
                }

    fci = VkFenceCreateInfo(24, None, 0)
    fence = ctypes.c_void_p()
    rc = _call(calls, "vkCreateFence", vkCreateFence, dev, ctypes.byref(fci), None, ctypes.byref(fence))
    log.st("fence_created", rc=rc)
    if rc != 0 or not fence.value:
        return {"ok": False, "error": "vkCreateFence rc=%r" % rc}
    rc = _call(calls, "vkResetFences", vkResetFences, dev, 1, ctypes.byref(fence))
    log.st("fence_reset", rc=rc)
    si = VkSubmitInfo(4, None, 0, None, None, 1, cmdarr, 0, None)
    rc = _call(calls, "vkQueueSubmit", vkQueueSubmit, queue, 1, ctypes.byref(si), fence)
    log.st("submitted", rc=rc, submitted=True)
    if rc != 0:
        return {"ok": False, "error": "vkQueueSubmit rc=%r" % rc}
    rc = _call(calls, "vkWaitForFences", vkWaitForFences, dev, 1, ctypes.byref(fence), 1, 1_000_000_000)
    log.st("fence_wait", rc=rc)
    if rc != 0:
        return {"ok": False, "error": "vkWaitForFences rc=%r" % rc}

    log.st("device_ready", queue_family=qf, submitted=True,
           buffer_bytes=4096, memory_type=mi)
    set_phase("device_ready")
    log.st("park")
    set_phase("park_waitIdle")
    rc = _call(calls, "vkDeviceWaitIdle", vkDeviceWaitIdle, dev)
    log.st("wait_idle", rc=rc)
    set_phase("park_destroyDevice")
    # Destroy in reverse dependency order. Vulkan destroy entry points return void;
    # `completed` is the honest evidence, not a fabricated VkResult.
    vkDestroyFence(dev, fence, None)
    vkFreeCommandBuffers(dev, pool, 1, cmdarr)
    vkDestroyCommandPool(dev, pool, None)
    vkDestroyBuffer(dev, buf, None)
    vkFreeMemory(dev, mem, None)
    _call(calls, "vkDestroyDevice", vkDestroyDevice, dev, None)
    set_phase("park_destroyInstance")
    log.st("destroy_device", rc=None, api="void", completed=True)
    _call(calls, "vkDestroyInstance", vkDestroyInstance, inst, None)
    log.st("destroy_instance", rc=None, api="void", completed=True)
    log.st("parked", device_destroyed=True, instance_destroyed=True,
           held_device=False, vulkan_calls_after_park=0)
    return {"ok": True, "device_name": name, "driver_version": driver, "vendor_id": vendor,
            "device_id": deviceid, "device_type": devtype, "queue_family": qf,
            "queue_flags": int(qarr[qf].queueFlags), "queue_count": int(qarr[qf].queueCount),
            "buffer_bytes": 4096, "memory_type": mi, "memory_size": int(req.size),
            "submitted": True, "device_destroyed": True, "instance_destroyed": True,
            "calls": calls}


def prewarm_target_tmp(log, source, target, chunk_bytes=65536):
    """V1: write a complete 5 MB target tmp, fsync, delete it BEFORE Vulkan."""
    data = open(source, "rb").read()
    tmp = str(target) + ".prewarm"
    set_phase("prewarm", bytes=len(data), chunk_bytes=chunk_bytes)
    target.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with open(tmp, "wb") as f:
        sent = 0
        k = 0
        while sent < len(data):
            chunk = data[sent:sent + chunk_bytes]
            k += 1
            tw0 = time.perf_counter()
            f.write(chunk)
            tw1 = time.perf_counter()
            record_sys("prewarm_write", tw0, tw1, chunk=k, bytes=len(chunk))
            sent += len(chunk)
        tf0 = time.perf_counter()
        f.flush()
        tf1 = time.perf_counter()
        record_sys("prewarm_flush", tf0, tf1)
        ty0 = time.perf_counter()
        os.fsync(f.fileno())
        ty1 = time.perf_counter()
        record_sys("prewarm_fsync", ty0, ty1)
    try:
        os.unlink(tmp)
        removed = True
    except FileNotFoundError:
        removed = False
    log.st("prewarmed", path=tmp, bytes=len(data), chunks=k, elapsed_s=round(time.perf_counter() - t0, 3),
           removed=removed)
    return {"path": tmp, "bytes": len(data), "chunks": k,
            "elapsed_s": round(time.perf_counter() - t0, 3), "removed": removed}


def settle_probe(log, target, max_probes=10, slow_ms=250.0, sleep_s=0.5):
    """Wait for delayed driver reclaim after vkDestroyDevice before the save window.

    4 KiB probe write, timed.  A probe >250 ms means the driver is still settling:
    sleep 500 ms and retry, at most 10 probes (<=5 s sleep total).
    """
    probe = Path(str(target) + ".settle-probe")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = b"K1SETTLE" * 512  # exactly 4096 bytes
    probes = []
    t_all0 = time.perf_counter()
    for i in range(1, max_probes + 1):
        set_phase("settle", probe=i)
        tw0 = time.perf_counter()
        with open(probe, "wb") as f:
            t0 = time.perf_counter()
            f.write(data)
            t1 = time.perf_counter()
            f.flush()
            t2 = time.perf_counter()
            os.fsync(f.fileno())
            t3 = time.perf_counter()
        total_ms = round((t3 - t0) * 1000.0, 3)
        rec = {"probe": i, "bytes": len(data),
               "write_ms": round((t1 - t0) * 1000.0, 3),
               "flush_ms": round((t2 - t1) * 1000.0, 3),
               "fsync_ms": round((t3 - t2) * 1000.0, 3),
               "total_ms": total_ms, "slow": bool(total_ms > slow_ms),
               "sleep_ms_after": 0}
        probes.append(rec)
        log.st("settle_probe", **rec)
        if total_ms <= slow_ms:
            break
        if i < max_probes:
            rec["sleep_ms_after"] = int(sleep_s * 1000)
            set_phase("settle_sleep", probe=i, sleep_ms=rec["sleep_ms_after"])
            time.sleep(sleep_s)
    try:
        os.unlink(probe)
        removed = True
    except FileNotFoundError:
        removed = False
    out = {"probe_bytes": len(data), "slow_ms": slow_ms,
           "total_s": round(time.perf_counter() - t_all0, 3),
           "n_probes": len(probes), "removed": removed, "probes": probes}
    set_phase("settle_done", probes=len(probes), total_s=out["total_s"])
    log.st("settle_done", probes=len(probes), total_s=out["total_s"],
           final_total_ms=probes[-1]["total_ms"] if probes else None, removed=removed)
    return out


def save_cycles(log, source, target, cycles=3, payload_bytes=0, chunk_bytes=65536, fsync_every=0):
    data = open(source, "rb").read()
    if payload_bytes and payload_bytes < len(data):
        data = data[:payload_bytes]
    src = {"path": str(source), "sha16": hashlib.sha256(data).hexdigest()[:16],
           "bytes": len(data), "n_tokens": parse_header(source)["n_tokens"]}
    target.parent.mkdir(parents=True, exist_ok=True)
    # Start from before (pre-reg target is pre-populated, not missing).
    set_phase("save_pre_tmp", cycle=1)
    shutil.copyfile(source, target)
    with open(target, "rb+") as f:
        os.fsync(f.fileno())
    tgt0 = parse_header(target)
    log.st("target_initialized", target=str(target), sha16=tgt0["sha16"], n_tokens=tgt0["n_tokens"],
           bytes=tgt0["bytes"])
    saves = []
    fsync_events = []
    sys0 = len(SYS)
    for i in range(1, cycles + 1):
        cycle_t0 = time.perf_counter()
        log.st("save_loop", cycle=i, of=cycles)
        log.st("saving_cycle", cycle=i, phase="pre_tmp")
        set_phase("save_pre_tmp", cycle=i)
        time.sleep(0.050)
        tmp = str(target) + ".tmp-%d-%d" % (os.getpid(), i)
        log.st("tmp_writing", cycle=i, frac=0.0, chunk_bytes=chunk_bytes)
        chunk_timings = []
        last_end = None
        with open(tmp, "wb") as f:
            sent = 0
            k = 0
            total_chunks = (len(data) + chunk_bytes - 1) // chunk_bytes
            while sent < len(data):
                chunk = data[sent:sent + chunk_bytes]
                k += 1
                set_phase("save_write(chunk_%d)" % k, cycle=i, chunk=k)
                tb0 = time.perf_counter()
                record_sys("write_begin", tb0, tb0, cycle=i, chunk=k, bytes=len(chunk))
                tw0 = time.perf_counter()
                gap_ms = 0.0 if last_end is None else (tw0 - last_end) * 1000.0
                f.write(chunk)
                tw1 = time.perf_counter()
                last_end = tw1
                chunk_timings.append({"cycle": i, "chunk": k, "bytes": len(chunk),
                                      "gap_ms": round(gap_ms, 3),
                                      "write_ms": round((tw1 - tw0) * 1000.0, 3),
                                      "total_ms": round(gap_ms + (tw1 - tw0) * 1000.0, 3)})
                record_sys("write_end", tw0, tw1, cycle=i, chunk=k, bytes=len(chunk))
                sent += len(chunk)
                if fsync_every and k % fsync_every == 0 and sent < len(data):
                    set_phase("save_fsync", cycle=i, chunk=k)
                    itf0 = time.perf_counter()
                    f.flush()
                    itf1 = time.perf_counter()
                    itfs0 = time.perf_counter()
                    os.fsync(f.fileno())
                    itfs1 = time.perf_counter()
                    ev = {"cycle": i, "at_chunk": k, "final": False,
                          "flush_ms": round((itf1 - itf0) * 1000.0, 3),
                          "fsync_ms": round((itfs1 - itfs0) * 1000.0, 3),
                          "total_ms": round((itfs1 - itf0) * 1000.0, 3)}
                    fsync_events.append(ev)
                    record_sys("partial_flush", itf0, itf1, cycle=i, chunk=k)
                    record_sys("partial_fsync", itfs0, itfs1, cycle=i, chunk=k)
                if k == 1 or k % max(1, total_chunks // 10) == 0 or k == total_chunks:
                    log.st("tmp_writing", cycle=i, frac=round(sent / len(data), 4), chunk=k,
                           chunks=total_chunks)
                time.sleep(0.006)
            set_phase("save_flush", cycle=i)
            tfb = time.perf_counter()
            record_sys("flush_begin", tfb, tfb, cycle=i)
            tf0 = time.perf_counter()
            f.flush()
            tf1 = time.perf_counter()
            record_sys("flush_end", tf0, tf1, cycle=i)
            final_ev = {"cycle": i, "at_chunk": total_chunks, "final": True,
                        "flush_ms": round((tf1 - tf0) * 1000.0, 3),
                        "fsync_ms": None, "total_ms": None}
            set_phase("save_fsync", cycle=i)
            tyb = time.perf_counter()
            record_sys("fsync_begin", tyb, tyb, cycle=i)
            ty0 = time.perf_counter()
            os.fsync(f.fileno())
            ty1 = time.perf_counter()
            record_sys("fsync_end", ty0, ty1, cycle=i)
        final_ev["fsync_ms"] = round((ty1 - ty0) * 1000.0, 3)
        final_ev["total_ms"] = round((ty1 - tf0) * 1000.0, 3)
        fsync_events.append(final_ev)
        flush_ms = round((tf1 - tf0) * 1000.0, 3)
        fsync_ms = round((ty1 - ty0) * 1000.0, 3)
        log.st("tmp_ready", cycle=i, tmp=tmp, bytes=os.path.getsize(tmp))
        log.st("fsynced", cycle=i, tmp=tmp)
        set_phase("sleep", cycle=i, sleep_s=0.030)
        time.sleep(0.030)
        set_phase("save_replace", cycle=i)
        trb = time.perf_counter()
        record_sys("durable_replace_begin", trb, trb, cycle=i)
        tr0 = time.perf_counter()
        mode = _durable_replace(tmp, str(target))
        tr1 = time.perf_counter()
        replace_ms = round((tr1 - tr0) * 1000.0, 3)
        record_sys("durable_replace_end", tr0, tr1, cycle=i, mode=mode)
        log.st("replaced", cycle=i, mode=mode)
        set_phase("save_post", cycle=i)
        ident = parse_header(target)
        third = ident["sha16"] != src["sha16"]
        saves.append({"cycle": i, "target_sha16": ident["sha16"], "target_bytes": ident["bytes"],
                      "fsync_every": int(fsync_every), "fsync_count": len([e for e in fsync_events if e["cycle"] == i]),
                      "target_n_tokens": ident["n_tokens"], "third": bool(third),
                      "replace_mode": mode, "tmp_removed": not os.path.exists(tmp),
                      "flush_ms": flush_ms, "fsync_ms": fsync_ms,
                      "replace_ms": replace_ms, "cycle_time_s": round(time.perf_counter() - cycle_t0, 3),
                      "chunk_timings": chunk_timings})
        log.st("hold", cycle=i, hold_s=0.4)
        set_phase("sleep", cycle=i, sleep_s=0.400)
        time.sleep(0.400)
        log.st("hold_end", cycle=i)
        log.st("saving_cycle", cycle=i, phase="done", third=bool(third))
    return {"source": src, "target_initial": tgt0, "saves": saves,
            "fsync_every": int(fsync_every), "fsync_events": fsync_events,
            "all_third_zero": all(not s["third"] for s in saves),
            "syscall_trace": list(SYS[sys0:]),
            "phase_history": list(PHASE_HISTORY)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--source", default=str(OUT / "M5-KILL-before.kvmem"))
    ap.add_argument("--target", default="")
    ap.add_argument("--state-log", default="")
    ap.add_argument("--result", default="")
    ap.add_argument("--vk", choices=["on", "off"], default="on")
    ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--payload-bytes", type=int, default=0)
    ap.add_argument("--chunk-bytes", type=int, default=65536)
    ap.add_argument("--fsync-every", type=int, default=0)
    ap.add_argument("--prewarm", action="store_true")
    ap.add_argument("--park-sleep", type=float, default=0.0)
    ap.add_argument("--no-settle", action="store_true")
    ap.add_argument("--trace", default="")
    ap.add_argument("--no-kill", action="store_true")
    ap.add_argument("--armed", action="store_true")
    a = ap.parse_args()
    if a.armed:
        print("K1_CHILD_REFUSED: --armed is not accepted by the instrumented child", flush=True)
        return 2
    run = int(a.run)
    state_log = Path(a.state_log) if a.state_log else OUT / ("kill_state_k1_%03d.log" % run)
    target = Path(a.target) if a.target else K1 / ("run-%03d" % run) / "target.kvmem"
    result_path = Path(a.result) if a.result else OUT / ("_k1_park_result_%03d.json" % run)
    SYS.clear()
    PHASE_HISTORY.clear()
    set_phase("start", vk=a.vk, cycles=a.cycles)
    log = Logger(state_log)
    hb = Heartbeat(log)
    hb.start()
    out = {"schema": "m5_k1_park_child_v1", "run": run, "model_loaded": False,
           "armed": False, "signals_sent": 0, "state_log": str(state_log),
           "vk_mode": a.vk, "cycles": int(a.cycles),
           "payload_bytes": int(a.payload_bytes), "chunk_bytes": int(a.chunk_bytes),
           "fsync_every": int(a.fsync_every),
           "prewarm": bool(a.prewarm), "park_sleep_s": float(a.park_sleep),
           "settle_skipped": bool(a.no_settle), "trace_path": str(a.trace) if a.trace else None,
           "heartbeat_interval_s": 0.2,
           "source": str(a.source), "target": str(target), "started_at": wall(),
           "states": [], "vk": None, "save": None, "status": "running", "error": None}
    try:
        src = Path(a.source)
        if not src.exists():
            raise SystemExit("source missing: %s" % src)
        out["source_info"] = parse_header(src)
        install_movefile_trace()
        if a.trace:
            start_trace(a.trace)
        if a.prewarm:
            out["prewarm"] = prewarm_target_tmp(log, src, target, int(a.chunk_bytes))
        if a.vk == "off":
            log.st("vk_off", reason="comparison arm: same process shape, no Vulkan object")
            out["vk"] = {"ok": True, "skipped": True, "mode": "off",
                         "device_destroyed": True, "instance_destroyed": True}
            set_phase("holding", device_destroyed=True, instance_destroyed=True, vulkan_skipped=True)
            log.st("holding", device_destroyed=True, instance_destroyed=True, pure_file=True, vk="off")
        else:
            vk = vulkan_park(log, [])
            out["vk"] = vk
            if not vk.get("ok"):
                out["status"] = "未接上（vkCreateDevice/device 路径失败）"
                out["error"] = vk.get("error")
            else:
                set_phase("holding", device_destroyed=True, instance_destroyed=True, vulkan_skipped=False)
                log.st("holding", device_destroyed=True, pure_file=True, vk="on")
        if out["status"] == "running":
            park_end_t = time.perf_counter()
            if a.park_sleep > 0:
                set_phase("post_park_wait", seconds=float(a.park_sleep))
                log.st("post_park_wait_begin", seconds=float(a.park_sleep),
                       since_park_s=round(park_end_t - out.get("_park_done_t", park_end_t), 3))
                time.sleep(float(a.park_sleep))
                log.st("post_park_wait_end", seconds=float(a.park_sleep),
                       since_park_s=round(time.perf_counter() - park_end_t, 3))
                out["post_park_wait_s"] = round(time.perf_counter() - park_end_t, 3)
            if a.no_settle:
                out["settle"] = {"skipped": True, "reason": "--no-settle"}
            else:
                out["settle"] = settle_probe(log, target)
            out["park_to_save_s"] = round(time.perf_counter() - park_end_t, 3)
            out["save"] = save_cycles(log, src, target, int(a.cycles),
                                       int(a.payload_bytes), int(a.chunk_bytes), int(a.fsync_every))
            out["status"] = "completed" if out["save"]["all_third_zero"] else "未通过（third>0）"
    except BaseException as e:  # noqa: BLE001
        out["status"] = "未接上（子进程异常）"
        out["error"] = type(e).__name__ + ": " + str(e)
    finally:
        set_phase("graceful_exit", status=out["status"])
        hb.shutdown()
        log.st("graceful_exit", status=out["status"], model_loaded=False,
               armed=False, signals_sent=0)
        stop_trace()
        out["heartbeat_count"] = sum(1 for _ in [])
        out["phase_history"] = list(PHASE_HISTORY)
        out["syscall_trace"] = list(SYS)
        out["finished_at"] = wall()
        out["elapsed_s"] = round(time.monotonic() - T0, 6)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(result_path) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, result_path)
        log.close()
    return 0 if out["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
