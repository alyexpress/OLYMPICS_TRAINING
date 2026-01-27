import hashlib


def hashed(data):
    return hashlib.md5((data + "92vALen3n").encode()).hexdigest()