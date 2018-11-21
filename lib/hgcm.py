'''
Simple HGCM implementation using VBGL_IOCTL_HGCM_{CONNECT,DISCONNECT,CALL}
VBoxGuest IOCTLs.
'''
from __future__ import print_function
import ctypes
import os
import functools

try:
    import fcntl
except:
    pass

from array import array
from struct import pack, unpack

IOCTL_HGCM_CONNECT = 4
IOCTL_HGCM_DISCONNECT = 5
IOCTL_HGCM_CALL = 7

VMMDevHGCMParmType_32bit              = 1
VMMDevHGCMParmType_64bit              = 2
VMMDevHGCMParmType_LinAddr            = 4
VMMDevHGCMParmType_PageList           = 10

def VBGL_IOCTL_CODE_SIZE_linux(func, size):
    return 0xc0005600 + (size<<16) + func

def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2)

def VBGL_IOCTL_CODE_SIZE_win(func, size):
    return CTL_CODE(
        0x22,          # FILE_DEVICE_UNKNOWN
        2048 + func,
        0,             # METHOD_BUFFERED
        2)             # FILE_WRITE_ACCESS

def vbox_ioctl_header(insize, outsize):
    '''
    typedef struct VBGLREQHDR
    {
        /** IN: The request input size, and output size if cbOut is zero.
         * @sa VMMDevRequestHeader::size  */
        uint32_t        cbIn;
        /** IN: Structure version (VBGLREQHDR_VERSION)
         * @sa VMMDevRequestHeader::version */
        uint32_t        uVersion;
        /** IN: The VMMDev request type, set to VBGLREQHDR_TYPE_DEFAULT unless this is a
         * kind of VMMDev request.
         * @sa VMMDevRequestType, VMMDevRequestHeader::requestType */
        uint32_t        uType;
        /** OUT: The VBox status code of the operation, out direction only. */
        int32_t         rc;
        /** IN: The output size.  This is optional - set to zero to use cbIn as the
         * output size. */
        uint32_t        cbOut;
        /** Reserved, MBZ. */
        uint32_t        uReserved;
    } VBGLREQHDR;
    '''
    return pack('<IIIiII',
            24+insize,  # cbIn
            0x10001,    # uVersion = VBGLREQHDR_VERSION
            0,          # uType = VBGLREQHDR_TYPE_DEFAULT
            -225,       # rc = VERR_INTERNAL_ERROR
            24+outsize, # cbOut
            0)          # uReserved

def vbox_ioctl_windows(handle, func, inbuf, outsize):
    tx = ctypes.c_ulong()

    insize = len(inbuf)
    buf_in = ctypes.create_string_buffer(vbox_ioctl_header(insize, outsize) + inbuf)
    buf_out = ctypes.create_string_buffer(24+outsize)

    res = ctypes.windll.kernel32.DeviceIoControl(
        handle, VBGL_IOCTL_CODE_SIZE_win(func, 24+insize),
        buf_in, 24+insize,
        buf_out, 24+outsize,
        ctypes.byref(tx), None)
    if not res:
        raise WinError()
    return buf_out.raw

def vbox_ioctl_linux(fd, func, inbuf, outsize):
    insize = len(inbuf)
    buf = array('b', vbox_ioctl_header(insize, outsize) + inbuf.ljust(outsize, '\0'))
    res = fcntl.ioctl(fd, VBGL_IOCTL_CODE_SIZE_linux(func, len(buf)), buf, 1)
    if res:
        raise IOError('VBoxError (IOCTL): %d' % rc)
    return buf


do_vbox_ioctl = None
def get_vbox_ioctl_func():
    global do_vbox_ioctl
    if do_vbox_ioctl is not None:
        return do_vbox_ioctl

    if os.path.exists('/dev/vboxuser'):
        fd = os.open('/dev/vboxuser', os.O_RDWR)
        do_vbox_ioctl = functools.partial(vbox_ioctl_linux, fd)
    else:
        handle = ctypes.windll.kernel32.CreateFileA(
            r'\\.\VBoxGuest',
            0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
            None, None,
            3, # OPEN_EXISTING
            None, None)
        do_vbox_ioctl = functools.partial(vbox_ioctl_windows, handle)
    return do_vbox_ioctl

def vbox_ioctl(func, req, outsize):
    resp = get_vbox_ioctl_func()(func, req, outsize=outsize)
    _,_,_,rc,_,_ = unpack('<IIIiII', resp[:24])
    if rc:
        raise IOError('VBoxError (HGCM): %d' % rc)
    return resp[24:24+outsize]

def hgcm_connect(svc):
    '''
    Connect to the HGCM service by the given name. Returns client ID.
    '''

    '''
    # define VBGL_IOCTL_HGCM_CONNECT                    VBGL_IOCTL_CODE_SIZE(4, VBGL_IOCTL_HGCM_CONNECT_SIZE)
    # define VBGL_IOCTL_HGCM_CONNECT_SIZE               sizeof(VBGLIOCHGCMCONNECT)
    # define VBGL_IOCTL_HGCM_CONNECT_SIZE_IN            sizeof(VBGLIOCHGCMCONNECT)
    # define VBGL_IOCTL_HGCM_CONNECT_SIZE_OUT           RT_UOFFSET_AFTER(VBGLIOCHGCMCONNECT, u.Out)
    typedef struct VBGLIOCHGCMCONNECT
    {
        /** The header. */
        VBGLREQHDR                  Hdr;
        union
        {
            struct
            {
                HGCMServiceLocation Loc;
            } In;
            struct
            {
                uint32_t            idClient;
            } Out;
        } u;
    } VBGLIOCHGCMCONNECT, RT_FAR *PVBGLIOCHGCMCONNECT;
    AssertCompileSize(VBGLIOCHGCMCONNECT, 24 + 132);

    typedef enum
    {
        VMMDevHGCMLoc_Invalid    = 0,
        VMMDevHGCMLoc_LocalHost  = 1,
        VMMDevHGCMLoc_LocalHost_Existing = 2,
        VMMDevHGCMLoc_SizeHack   = 0x7fffffff
    } HGCMServiceLocationType;
    AssertCompileSize(HGCMServiceLocationType, 4);

    typedef struct
    {
        char achName[128]; /**< This is really szName. */
    } HGCMServiceLocationHost;
    AssertCompileSize(HGCMServiceLocationHost, 128);

    typedef struct HGCMSERVICELOCATION
    {
        /** Type of the location. */
        HGCMServiceLocationType type;

        union
        {
            HGCMServiceLocationHost host;
        } u;
    } HGCMServiceLocation;
    AssertCompileSize(HGCMServiceLocation, 128+4);
    '''

    data = pack('<I128s',
            2,  # type = LocalHost_Existing
            svc # achName
            )

    client_id, = unpack('<I', vbox_ioctl(IOCTL_HGCM_CONNECT, data, 4))
    return client_id

def hgcm_disconnect(client_id):
    '''
    Disconnect the given HGCM client.
    '''

    '''
    # define VBGL_IOCTL_HGCM_DISCONNECT                 VBGL_IOCTL_CODE_SIZE(5, VBGL_IOCTL_HGCM_DISCONNECT_SIZE)
    # define VBGL_IOCTL_HGCM_DISCONNECT_SIZE            sizeof(VBGLIOCHGCMDISCONNECT)
    # define VBGL_IOCTL_HGCM_DISCONNECT_SIZE_IN         sizeof(VBGLIOCHGCMDISCONNECT)
    # define VBGL_IOCTL_HGCM_DISCONNECT_SIZE_OUT        sizeof(VBGLREQHDR)
    /** @note This is also used by a VbglR0 API.  */
    typedef struct VBGLIOCHGCMDISCONNECT
    {
        /** The header. */
        VBGLREQHDR          Hdr;
        union
        {
            struct
            {
                uint32_t    idClient;
            } In;
        } u;
    } VBGLIOCHGCMDISCONNECT, RT_FAR *PVBGLIOCHGCMDISCONNECT;
    AssertCompileSize(VBGLIOCHGCMDISCONNECT, 24 + 4);
    '''
    data = pack('<I', client_id)
    vbox_ioctl(IOCTL_HGCM_DISCONNECT, data, 0)


def hgcm_call(client_id, func, params):
    '''
    Call an HGCM function.

    Supported parameter types:
    * int; VMMDevHGCMParmType_32bit
    * string/bytes: VMMDevHGCMParmType_LinAddr

    It will return all parameters after the call, in case they were modified
    by the function.
    '''

    '''
    typedef struct VBGLIOCHGCMCALL
    {
        /** Common header. */
        VBGLREQHDR  Hdr;
        /** Input: The id of the caller. */
        uint32_t    u32ClientID;
        /** Input: Function number. */
        uint32_t    u32Function;
        /** Input: How long to wait (milliseconds) for completion before cancelling the
        * call.  This is ignored if not a VBGL_IOCTL_HGCM_CALL_TIMED or
        * VBGL_IOCTL_HGCM_CALL_TIMED_32 request. */
        uint32_t    cMsTimeout;
        /** Input: Whether a timed call is interruptible (ring-0 only).  This is ignored
        * if not a VBGL_IOCTL_HGCM_CALL_TIMED or VBGL_IOCTL_HGCM_CALL_TIMED_32
        * request, or if made from user land. */
        bool        fInterruptible;
        /** Explicit padding, MBZ. */
        uint8_t     bReserved;
        /** Input: How many parameters following this structure.
        *
        * The parameters are either HGCMFunctionParameter64 or HGCMFunctionParameter32,
        * depending on whether we're receiving a 64-bit or 32-bit request.
        *
        * The current maximum is 61 parameters (given a 1KB max request size,
        * and a 64-bit parameter size of 16 bytes).
        *
        * @note This information is duplicated by Hdr.cbIn, but it's currently too much
        *       work to eliminate this. */
        uint16_t    cParms;
        /* Parameters follow in form HGCMFunctionParameter aParms[cParms] */
    } VBGLIOCHGCMCALL, RT_FAR *PVBGLIOCHGCMCALL;
    AssertCompileSize(VBGLIOCHGCMCALL, 24 + 16);

    typedef enum
    {
        VMMDevHGCMParmType_Invalid            = 0,
        VMMDevHGCMParmType_32bit              = 1,
        VMMDevHGCMParmType_64bit              = 2,
        VMMDevHGCMParmType_PhysAddr           = 3,  /**< @deprecated Doesn't work, use PageList. */
        VMMDevHGCMParmType_LinAddr            = 4,  /**< In and Out */
        VMMDevHGCMParmType_LinAddr_In         = 5,  /**< In  (read;  host<-guest) */
        VMMDevHGCMParmType_LinAddr_Out        = 6,  /**< Out (write; host->guest) */
        VMMDevHGCMParmType_LinAddr_Locked     = 7,  /**< Locked In and Out */
        VMMDevHGCMParmType_LinAddr_Locked_In  = 8,  /**< Locked In  (read;  host<-guest) */
        VMMDevHGCMParmType_LinAddr_Locked_Out = 9,  /**< Locked Out (write; host->guest) */
        VMMDevHGCMParmType_PageList           = 10, /**< Physical addresses of locked pages for a buffer. */
        VMMDevHGCMParmType_SizeHack           = 0x7fffffff
    } HGCMFunctionParameterType;

    typedef struct
    {
        HGCMFunctionParameterType type;
        union
        {
            uint32_t   value32;
            uint64_t   value64;
            struct
            {
                uint32_t size;

                union
                {
                    RTGCPHYS64 physAddr;
                    RTGCPTR64  linearAddr;
                } u;
            } Pointer;
            struct
            {
                uint32_t size;   /**< Size of the buffer described by the page list. */
                uint32_t offset; /**< Relative to the request header, valid if size != 0. */
            } PageList;
        } u;
        //...
    } HGCMFunctionParameter64;
    '''

    fmt = '<IIIBBH'
    data = pack(fmt,
            client_id,
            func,
            100000, # timeout, ignored
            0, 0,
            len(params))
    assert len(data) == 16

    args = []
    for p in params:
        if isinstance(p, (int, long)):
            args.append(p)
            data += pack('<IIQ', VMMDevHGCMParmType_32bit, p, 0)
        else:
            s = ctypes.create_string_buffer(p)
            data += pack('<IIQ', VMMDevHGCMParmType_LinAddr, len(p), ctypes.addressof(s))
            args.append((s, len(p)))

    # print(' '.join('%02x'%ord(x) for x in data))
    sz = len(data)
    data = vbox_ioctl(IOCTL_HGCM_CALL, data, sz)

    res = []
    for i, a in enumerate(args):
        if isinstance(a, (int, long)):
            _,ret,_ = unpack('<IIQ', data[16+i*16:16+(i+1)*16])
            res.append(ret)
        else:
            s, sz = a
            res.append(s[:sz])
    return res


if __name__ == '__main__':
    GET_PROP = 1
    SET_PROP = 2
    DEL_PROP = 3

    client = hgcm_connect('VBoxGuestPropSvc')
    print('Client: %d' % client)
    hgcm_call(client, SET_PROP, ["foo\0", "bar\0"])
    _, res, _, sz = hgcm_call(client, GET_PROP, ["foo\0", "A"*0x100, 0, 0])
    value = res[:sz].rstrip('\0')
    assert value == 'bar'
