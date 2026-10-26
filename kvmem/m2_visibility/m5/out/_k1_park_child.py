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
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
M5 = ROOT / "kvmem/m2_visibility/m5"
OUT = M5 / "out"
K1 = OUT / "kill_k1"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
from session_state import _durable_replace  # noqa: E402

T0 = time.monotonic()
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

    def st(self, state_name, **detail):
        rec = {"state": state_name, "t_mono": round(time.monotonic() - T0, 6), "t_wall": wall(), **detail}
        line = "[STATE %s t_mono=%.6f t_wall=%s] %s" % (state_name, rec["t_mono"], rec["t_wall"],
                                                       json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()
        return rec

    def close(self):
        try:
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
    log.st("park")
    rc = _call(calls, "vkDeviceWaitIdle", vkDeviceWaitIdle, dev)
    log.st("wait_idle", rc=rc)
    # Destroy in reverse dependency order. Vulkan destroy entry points return void;
    # `completed` is the honest evidence, not a fabricated VkResult.
    vkDestroyFence(dev, fence, None)
    vkFreeCommandBuffers(dev, pool, 1, cmdarr)
    vkDestroyCommandPool(dev, pool, None)
    vkDestroyBuffer(dev, buf, None)
    vkFreeMemory(dev, mem, None)
    _call(calls, "vkDestroyDevice", vkDestroyDevice, dev, None)
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


def save_cycles(log, source, target, cycles=3):
    data = open(source, "rb").read()
    src = {"path": str(source), "sha16": hashlib.sha256(data).hexdigest()[:16],
           "bytes": len(data), "n_tokens": parse_header(source)["n_tokens"]}
    target.parent.mkdir(parents=True, exist_ok=True)
    # Start from before (pre-reg target is pre-populated, not missing).
    shutil.copyfile(source, target)
    with open(target, "rb+") as f:
        os.fsync(f.fileno())
    tgt0 = parse_header(target)
    log.st("target_initialized", target=str(target), sha16=tgt0["sha16"], n_tokens=tgt0["n_tokens"],
           bytes=tgt0["bytes"])
    saves = []
    for i in range(1, cycles + 1):
        log.st("save_loop", cycle=i, of=cycles)
        log.st("saving_cycle", cycle=i, phase="pre_tmp")
        time.sleep(0.050)
        tmp = str(target) + ".tmp-%d-%d" % (os.getpid(), i)
        log.st("tmp_writing", cycle=i, frac=0.0, chunk_bytes=65536)
        with open(tmp, "wb") as f:
            sent = 0
            k = 0
            total_chunks = (len(data) + 65535) // 65536
            while sent < len(data):
                chunk = data[sent:sent + 65536]
                f.write(chunk)
                sent += len(chunk)
                k += 1
                if k == 1 or k % max(1, total_chunks // 10) == 0 or k == total_chunks:
                    log.st("tmp_writing", cycle=i, frac=round(sent / len(data), 4), chunk=k,
                           chunks=total_chunks)
                time.sleep(0.006)
            f.flush()
            os.fsync(f.fileno())
        log.st("tmp_ready", cycle=i, tmp=tmp, bytes=os.path.getsize(tmp))
        log.st("fsynced", cycle=i, tmp=tmp)
        time.sleep(0.030)
        mode = _durable_replace(tmp, str(target))
        log.st("replaced", cycle=i, mode=mode)
        ident = parse_header(target)
        third = ident["sha16"] != src["sha16"]
        saves.append({"cycle": i, "target_sha16": ident["sha16"], "target_bytes": ident["bytes"],
                      "target_n_tokens": ident["n_tokens"], "third": bool(third),
                      "replace_mode": mode, "tmp_removed": not os.path.exists(tmp)})
        log.st("hold", cycle=i, hold_s=0.4)
        time.sleep(0.400)
        log.st("hold_end", cycle=i)
        log.st("saving_cycle", cycle=i, phase="done", third=bool(third))
    return {"source": src, "target_initial": tgt0, "saves": saves,
            "all_third_zero": all(not s["third"] for s in saves)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--source", default=str(OUT / "M5-KILL-before.kvmem"))
    ap.add_argument("--target", default="")
    ap.add_argument("--state-log", default="")
    ap.add_argument("--result", default="")
    a = ap.parse_args()
    run = int(a.run)
    state_log = Path(a.state_log) if a.state_log else OUT / ("kill_state_k1_%03d.log" % run)
    target = Path(a.target) if a.target else K1 / ("run-%03d" % run) / "target.kvmem"
    result_path = Path(a.result) if a.result else OUT / ("_k1_park_result_%03d.json" % run)
    log = Logger(state_log)
    out = {"schema": "m5_k1_park_child_v1", "run": run, "model_loaded": False,
           "armed": False, "signals_sent": 0, "state_log": str(state_log),
           "source": str(a.source), "target": str(target), "started_at": wall(),
           "states": [], "vk": None, "save": None, "status": "running", "error": None}
    try:
        src = Path(a.source)
        if not src.exists():
            raise SystemExit("source missing: %s" % src)
        out["source_info"] = parse_header(src)
        vk = vulkan_park(log, [])
        out["vk"] = vk
        if not vk.get("ok"):
            out["status"] = "未接上（vkCreateDevice/device 路径失败）"
            out["error"] = vk.get("error")
        else:
            log.st("holding", device_destroyed=True, pure_file=True)
            out["save"] = save_cycles(log, src, target, 3)
            out["status"] = "completed" if out["save"]["all_third_zero"] else "未通过（third>0）"
    except BaseException as e:  # noqa: BLE001
        out["status"] = "未接上（子进程异常）"
        out["error"] = type(e).__name__ + ": " + str(e)
    finally:
        log.st("graceful_exit", status=out["status"], model_loaded=False,
               armed=False, signals_sent=0)
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