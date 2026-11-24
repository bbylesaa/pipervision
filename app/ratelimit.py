"""Rate limiter sederhana in-memory (per IP, per menit).

Untuk skala besar / multi-instance gunakan Redis atau gateway (mis. Cloudflare).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, request: Request) -> None:
        if self.per_minute <= 0:
            return
        fwd = request.headers.get("x-forwarded-for")
        ip = (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown"))
        now = time.monotonic()
        q = self.hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            raise HTTPException(429, "Terlalu banyak permintaan. Coba lagi sebentar lagi.")
        q.append(now)
