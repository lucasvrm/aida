from __future__ import annotations

from app.core.config import settings
from app.core.errors import UpstreamError
from app.core.retry import retry
from app.supabase.client import supabase_client

class Storage:
    def __init__(self):
        self.sb = supabase_client()

    def download(self, bucket: str, path: str) -> bytes:
        def _do():
            return self.sb.storage.from_(bucket).download(path)
        try:
            data = retry(_do, attempts=3)
        except Exception as e:
            raise UpstreamError("Falha ao baixar do Supabase Storage.", details=str(e))
        if not isinstance(data, (bytes, bytearray)):
            raise UpstreamError("Download retornou formato inválido.")
        b = bytes(data)
        if len(b) > settings.MAX_DOCUMENT_BYTES:
            raise UpstreamError(
                "Arquivo excede o limite de tamanho.",
                details={"bytes": len(b), "max": settings.MAX_DOCUMENT_BYTES},
            )
        return b

    def upload(self, bucket: str, path: str, content: bytes, content_type: str) -> None:
        def _do():
            return self.sb.storage.from_(bucket).upload(
                file=content,
                path=path,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        try:
            retry(_do, attempts=3)
        except Exception as e:
            raise UpstreamError("Falha ao subir para Supabase Storage.", details=str(e))

    def signed_url(self, bucket: str, path: str, ttl_seconds: int) -> str:
        try:
            res = self.sb.storage.from_(bucket).create_signed_url(path, ttl_seconds)
        except Exception as e:
            raise UpstreamError("Falha ao gerar signedUrl.", details=str(e))
        url = res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
        if not url:
            raise UpstreamError("Resposta sem signedUrl.", details=res)
        return url
