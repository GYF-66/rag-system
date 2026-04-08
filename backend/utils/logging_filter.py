# -*- coding: utf-8 -*-
"""
日志敏感信息过滤器
防止密码、Token 等敏感信息泄露到日志中
"""
import logging
import re


class SensitiveDataFilter(logging.Filter):
    """过滤日志中的敏感信息"""

    PATTERNS = [
        (re.compile(r'password["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.IGNORECASE), 'password: ***'),
        (re.compile(r'token["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.IGNORECASE), 'token: ***'),
        (re.compile(r'secret["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.IGNORECASE), 'secret: ***'),
        (re.compile(r'api_key["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.IGNORECASE), 'api_key: ***'),
    ]

    def filter(self, record):
        if hasattr(record, 'msg') and record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        return True
