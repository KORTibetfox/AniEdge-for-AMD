"""Resolve the target Radeon through DXGI; used by the DirectML path."""
import ctypes
from ctypes import wintypes as w


def rx9070xt_device():
    class GUID(ctypes.Structure):
        _fields_ = [("a", w.DWORD), ("b", w.WORD), ("c", w.WORD), ("d", ctypes.c_ubyte * 8)]
    class LUID(ctypes.Structure):
        _fields_ = [("low", w.DWORD), ("high", w.LONG)]
    class DESC(ctypes.Structure):
        _fields_ = [("Description", w.WCHAR * 128), ("VendorId", w.UINT), ("DeviceId", w.UINT),
                    ("SubSysId", w.UINT), ("Revision", w.UINT), ("DedicatedVideoMemory", ctypes.c_size_t),
                    ("DedicatedSystemMemory", ctypes.c_size_t), ("SharedSystemMemory", ctypes.c_size_t),
                    ("AdapterLuid", LUID), ("Flags", w.UINT)]
    iid = GUID(0x770aae78, 0xf26f, 0x4dba, (ctypes.c_ubyte * 8)(0xa8, 0x29, 0x25, 0x3c, 0x83, 0xd1, 0xb3, 0x87))
    factory = ctypes.c_void_p()
    create = ctypes.windll.dxgi.CreateDXGIFactory1
    create.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    if create(ctypes.byref(iid), ctypes.byref(factory)) != 0:
        raise RuntimeError("DXGI GPU 목록을 읽지 못했습니다.")

    def vtable(pointer):
        return ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

    def release(pointer):
        ctypes.WINFUNCTYPE(w.ULONG, ctypes.c_void_p)(vtable(pointer)[2])(pointer)

    try:
        enum = ctypes.WINFUNCTYPE(w.LONG, ctypes.c_void_p, w.UINT, ctypes.POINTER(ctypes.c_void_p))(vtable(factory)[12])
        for index in range(32):
            adapter = ctypes.c_void_p()
            if enum(factory, index, ctypes.byref(adapter)) != 0:
                break
            try:
                desc = DESC()
                get_desc = ctypes.WINFUNCTYPE(w.LONG, ctypes.c_void_p, ctypes.POINTER(DESC))(vtable(adapter)[10])
                if get_desc(adapter, ctypes.byref(desc)) == 0 and desc.VendorId == 0x1002 and "RX 9070 XT" in desc.Description:
                    return index, desc.Description
            finally:
                release(adapter)
    finally:
        release(factory)
    raise RuntimeError("AMD Radeon RX 9070 XT 장치를 찾지 못했습니다.")
