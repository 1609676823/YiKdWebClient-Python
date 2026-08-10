"""附件分块与上传工具。"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional, Union

from .common import _json_dumps
from .models import UploadModel, UploadModelData

if False:  # pragma: no cover - 仅供静态类型检查，避免运行时循环导入。
    from .client import YiK3CloudClient


class FileChunk:
    def __init__(self) -> None:
        self.Chunkindex = 0
        self.Filename = ""
        self.IsLast = False
        self._chunkbyte = b""
        self.ChunkBase64 = ""

    @property
    def Chunkbyte(self) -> bytes:
        return self._chunkbyte

    @Chunkbyte.setter
    def Chunkbyte(self, value: bytes) -> None:
        self._chunkbyte = bytes(value)
        self.ChunkBase64 = base64.b64encode(self._chunkbyte).decode("ascii")

    chunk_index = property(
        lambda self: self.Chunkindex, lambda self, v: setattr(self, "Chunkindex", v)
    )
    filename = property(lambda self: self.Filename, lambda self, v: setattr(self, "Filename", v))
    is_last = property(lambda self: self.IsLast, lambda self, v: setattr(self, "IsLast", v))
    chunk_bytes = property(
        lambda self: self.Chunkbyte, lambda self, v: setattr(self, "Chunkbyte", v)
    )
    chunk_base64 = property(lambda self: self.ChunkBase64)


ChunkAction = Callable[[FileChunk], None]
ProgressAction = Callable[[FileChunk, "YiK3CloudClient"], None]


class AttachmentHelper:
    @staticmethod
    def _validate_chunk_arguments(chunkAction: ChunkAction, chunkSize: int) -> None:
        if chunkAction is None:
            raise TypeError("chunkAction 不能为空")
        if chunkSize <= 0 or chunkSize > 2_147_483_647:
            raise ValueError("分块大小必须大于 0 且不能超过 Int32.MaxValue。")

    @staticmethod
    def ReadFileInChunksByAction(
        filePath: Union[str, Path],
        chunkAction: ChunkAction,
        chunkSize: int = 1024 * 1024,
    ) -> None:
        AttachmentHelper._validate_chunk_arguments(chunkAction, chunkSize)
        path = Path(filePath)
        total_length = path.stat().st_size
        position = 0
        chunk_index = 0
        with path.open("rb") as stream:
            while True:
                data = stream.read(chunkSize)
                if not data:
                    break
                position += len(data)
                chunk = FileChunk()
                chunk.Filename = path.name
                chunk.Chunkindex = chunk_index
                chunk.IsLast = position >= total_length
                chunk.Chunkbyte = data
                chunkAction(chunk)
                chunk_index += 1

    @staticmethod
    def ReadBase64ChunksByAction(
        base64Data: str,
        fileName: str,
        chunkAction: ChunkAction,
        chunkSize: int = 1024 * 1024,
    ) -> None:
        AttachmentHelper._validate_chunk_arguments(chunkAction, chunkSize)
        data = base64.b64decode(base64Data)
        total_length = len(data)
        for chunk_index, offset in enumerate(range(0, total_length, chunkSize)):
            chunk = FileChunk()
            chunk.Filename = fileName
            chunk.Chunkindex = chunk_index
            chunk.IsLast = offset + chunkSize >= total_length
            chunk.Chunkbyte = data[offset : offset + chunkSize]
            chunkAction(chunk)

    @staticmethod
    def _upload_chunks(
        read_chunks: Callable[[ChunkAction], None],
        yiK3CloudClient: "YiK3CloudClient",
        UploadModelTemplate: UploadModel,
        progressaction: Optional[ProgressAction],
    ) -> str:
        response = ""

        def upload(chunk: FileChunk) -> None:
            nonlocal response
            data = UploadModelTemplate.data
            data.FileName = chunk.Filename
            data.SendByte = chunk.ChunkBase64
            data.IsLast = chunk.IsLast
            upload_json = _json_dumps(
                asdict(UploadModelTemplate),
                yiK3CloudClient.UnsafeRelaxedJsonEscaping,
                write_indented=True,
            )
            response = yiK3CloudClient.AttachmentUpLoad(upload_json)
            if progressaction is not None:
                progressaction(chunk, yiK3CloudClient)

            try:
                root = json.loads(response)
                result = root["Result"]
                success = result["ResponseStatus"]["IsSuccess"]
            except Exception as exc:
                raise ValueError(response) from exc
            if str(success).casefold() != "true":
                raise ValueError(response)
            data.FileId = str(result.get("FileId", ""))

        read_chunks(upload)
        return response

    @staticmethod
    def AttachmentUploadByFilePath(
        filePath: Union[str, Path],
        yiK3CloudClient: "YiK3CloudClient",
        UploadModelTemplate: UploadModel,
        chunkSize: int = 1024 * 1024,
        progressaction: Optional[ProgressAction] = None,
    ) -> str:
        try:
            return AttachmentHelper._upload_chunks(
                lambda action: AttachmentHelper.ReadFileInChunksByAction(
                    filePath, action, chunkSize
                ),
                yiK3CloudClient,
                UploadModelTemplate,
                progressaction,
            )
        except Exception as exc:
            return str(exc)

    @staticmethod
    def AttachmentUploadByBase64(
        base64Data: str,
        fileName: str,
        yiK3CloudClient: "YiK3CloudClient",
        UploadModelTemplate: UploadModel,
        chunkSize: int = 1024 * 1024,
        progressaction: Optional[ProgressAction] = None,
    ) -> str:
        try:
            return AttachmentHelper._upload_chunks(
                lambda action: AttachmentHelper.ReadBase64ChunksByAction(
                    base64Data, fileName, action, chunkSize
                ),
                yiK3CloudClient,
                UploadModelTemplate,
                progressaction,
            )
        except Exception as exc:
            return str(exc)

    @staticmethod
    def CheckUploadModelData(UploadModelTemplate: UploadModel) -> None:
        data = UploadModelTemplate.data
        required = [
            (data.FileName, "文件名不能为空。"),
            (data.FormId, "表单ID不能为空。"),
            (data.InterId, "单据内码不能为空。"),
            (data.FileId, "文件ID不能为空。"),
            (data.SendByte, "文件字节流不能为空。"),
        ]
        for value, message in required:
            if value is None or not str(value).strip():
                raise ValueError(message)

        has_entry_key = bool(data.Entrykey and data.Entrykey.strip())
        has_entry_id = bool(
            data.EntryinterId and data.EntryinterId.strip() and data.EntryinterId != "-1"
        )
        if has_entry_key != has_entry_id:
            raise ValueError("Entrykey 和 EntryinterId 要么全有，要么全没有。")

    read_file_in_chunks = ReadFileInChunksByAction
    read_base64_chunks = ReadBase64ChunksByAction
    upload_file_path = AttachmentUploadByFilePath
    upload_base64 = AttachmentUploadByBase64
    validate_upload_model = CheckUploadModelData


__all__ = ["AttachmentHelper", "FileChunk", "UploadModel", "UploadModelData"]
