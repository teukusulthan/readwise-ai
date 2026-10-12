# -*- coding: utf-8 -*-
import json

import jmespath
import mimetypes
from config.base import settings
from loguru import logger
from datetime import datetime
from service import Services
from service import change_field_id
from util.helper import mongo_query_builder, get_md5, date_converter
from dto.upload import UploadFileDTO
from kafka import KafkaProducer
import magic
import re
from util.s3_filesystem import BaseBoto3, NewBaseBoto3
import io, tempfile, shutil, os
from PIL import Image

# Hard cap comes from settings.MAX_UPLOAD_SIZE_MB (BE_MAX_UPLOAD_SIZE_MB).

# Whitelist: only these extensions are allowed
ALLOWED_EXTENSIONS = {
    # documents
    "html",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "csv",
    "rtf",
    "odt",
    "ods",
    "odp",
    "epub",
    "md",
    # images
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "webp",
    "svg",
    "tiff",
    "ico",
    "heic",
    "heif",
    # video/audio
    "mp4",
    "mov",
    "avi",
    "mkv",
    "webm",
    "flv",
    "wmv",
    "m4v",
    "mp3",
    "wav",
    "ogg",
    "m4a",
    "aac",
    "flac",
    # archives
    "zip",
    "tar",
    "gz",
    "bz2",
    "xz",
    "7z",
    # data
    "json",
    "xml",
    "yaml",
    "yml",
}

# Whitelist: only these MIME types are allowed (verified by magic bytes, not filename)
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "text/html",
    "application/json",
    "application/xml",
    "text/xml",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp",
    "image/svg+xml",
    "image/svg",
    "image/tiff",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "audio/x-m4a",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "application/zip",
    "application/x-tar",
    "application/gzip",
}

# Characters allowed in folder paths and filenames
_SAFE_FILENAME_RE = re.compile(r"[^\w\s\-.]")  # only word chars, spaces, hyphens, dots
_SAFE_FOLDER_RE = re.compile(r"[^\w\s\-/]")  # same but allow forward-slash for depth


class Upload:
    def __init__(self):
        self.mongo = Services.mongo()
        self.s3 = Services.boto3()
        self.collection = self.mongo[settings.MONGO_DB][
            settings.MONGO_COLLECTION_UPLOAD
        ]
        self.collection_connection = self.mongo[settings.MONGO_DB][
            settings.MONGO_COLLECTION_CONNECTION
        ]

        self.collection_view = self.mongo[settings.MONGO_DB][
            f"v_{settings.MONGO_COLLECTION_UPLOAD}"
        ]
        self.bucket_name = (settings.S3FS_PATH_AGENT or "").replace("s3://", "")

    def resize_image(self, file_obj, scale_factor: float = 0.5) -> str:
        """
        Resize gambar dan simpan hasilnya ke folder tmp/, lalu kembalikan path-nya.

        :param image_path: Path gambar asli.
        :param scale_factor: Opsional, override faktor skala default.
        :return: Path ke gambar hasil resize.
        """

        file_obj.seek(0)
        img = Image.open(file_obj)
        width, height = img.size
        scale_factor = scale_factor if scale_factor else 0.5
        img.resize(
            (int(width * scale_factor), int(height * scale_factor)),
            Image.Resampling.LANCZOS,
        )

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        return buffer

    def _sanitize_filename(self, name: str) -> str:
        """
        Strip dangerous characters from a filename.
        Raises ValueError if the result is empty or looks like a path-traversal attempt.
        """
        if "\x00" in name:
            raise ValueError("Filename contains null byte.")

        name = os.path.basename(name.replace("\\", "/"))
        name = name.lstrip("./")

        name = _SAFE_FILENAME_RE.sub("", name)

        name = re.sub(r"\.{2,}", ".", name).strip()

        if not name:
            raise ValueError("Filename is empty after sanitization.")

        return name

    def _sanitize_folder(self, folder: str) -> str:
        """
        Sanitize folder path to prevent path-traversal attacks.
        Raises ValueError on suspicious input.
        """
        if not folder:
            raise ValueError("Folder path must not be empty.")

        if "\x00" in folder:
            raise ValueError("Folder path contains null byte.")

        folder = folder.replace("\\", "/")

        if ".." in folder.split("/"):
            raise ValueError("Path traversal detected in folder path.")

        folder = folder.lstrip("/")

        folder = _SAFE_FOLDER_RE.sub("", folder).strip("/")

        if not folder:
            raise ValueError("Folder path is empty after sanitization.")

        return folder

    def _validate_extension(self, filename: str) -> str:
        """Return the lower-cased extension or raise ValueError if not allowed."""
        parts = filename.rsplit(".", 1)
        if len(parts) != 2 or not parts[1]:
            raise ValueError(f"File '{filename}' has no extension.")

        ext = parts[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '.{ext}' is not allowed.")

        raw_exclude = settings.EXCLUDE_UPLOAD_EXTENSIONS or ""
        excluded = {e.strip().lower().lstrip(".") for e in raw_exclude.split(",") if e.strip()}
        if excluded and ext in excluded:
            raise ValueError(f"File extension '.{ext}' is not permitted in this deployment.")

        return ext

    def _validate_mime_by_magic(self, file_obj) -> str:
        """
        Read the first 2 KB of the file to detect the real MIME type via magic bytes.
        This prevents MIME-type spoofing by renaming (e.g. shell.php → image.jpg).
        Rewinds the file pointer afterwards.
        """
        header = file_obj.read(2048)
        file_obj.seek(0)

        detected = magic.from_buffer(header, mime=True)
        if detected not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Detected MIME type '{detected}' is not permitted.")

        return detected

    def _sanitize_tags(self, raw_tags: str) -> list:
        tags = [re.sub(r"[^\w\-]", "", t).strip() for t in raw_tags.split(",")]
        tags = [t for t in tags if t]
        return tags[:50]

    def upload_file(self, file, contents, dto: UploadFileDTO):
        """
        Secure version of upload_file.

        Security improvements
        ─────────────────────
        1. Path-traversal prevention  — folder & filename are sanitized before use.
        2. Extension whitelist        — only explicitly allowed extensions are accepted.
        3. Magic-byte MIME validation — real file type is detected from content, not
                                        just the filename, preventing MIME spoofing.
        4. File-size cap              — rejects files larger than settings.MAX_UPLOAD_SIZE_MB.
        5. Tag / data sanitization    — tags are stripped of special characters.
        6. Multipart upload fix       — large uploads now correctly use the resolved
                                        s3_util / bucket_name (custom connection aware).
        7. Null-byte rejection        — filenames/paths containing null bytes are rejected.
        """
        if file.size is None:
            raise ValueError("Cannot determine file size.")
        file_size_mb = file.size / (1024 * 1024)
        if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValueError(
                f"File size {file_size_mb:.1f} MB exceeds the maximum allowed "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        try:
            safe_folder = self._sanitize_folder(dto.folder)
        except ValueError as exc:
            raise ValueError(f"Invalid folder: {exc}") from exc

        raw_filename = file.filename or "upload"
        try:
            safe_base = self._sanitize_filename(raw_filename)
            ext = self._validate_extension(safe_base)
        except ValueError as exc:
            raise ValueError(f"Invalid filename: {exc}") from exc

        if dto.filename:
            try:
                custom_stem = self._sanitize_filename(dto.filename)
                custom_stem = custom_stem.rsplit(".", 1)[0]
            except ValueError as exc:
                raise ValueError(f"Invalid custom filename: {exc}") from exc
            safe_base = f"{custom_stem}.{ext}"

        try:
            real_mime = self._validate_mime_by_magic(file.file)
        except ValueError as exc:
            raise ValueError(f"File content validation failed: {exc}") from exc

        guessed_mime, _ = mimetypes.guess_type(safe_base)
        if guessed_mime and guessed_mime != real_mime:
            logger.warning(
                "MIME mismatch — filename suggests '{guessed}' but magic bytes say '{real}'. "
                "Using magic-byte result.",
                guessed=guessed_mime,
                real=real_mime,
            )
        mime_type = real_mime

        data = dto.dict()

        if data.get("tags"):
            data["tags"] = self._sanitize_tags(data["tags"])

        for key, value in data.items():
            if isinstance(value, list):
                temp = []
                for val in value:
                    temp.append(val.split(","))
                data[key] = jmespath.search("[][]", temp)

        data["createdAt"] = datetime.now()

        file_path = f"{safe_folder}/{safe_base}"
        _id = get_md5(file_path)

        s3_util = self.s3
        bucket_name = (settings.S3FS_PATH_AGENT or "").replace("s3://", "")

        if dto.connectionId:
            logger.warning("Using custom connectionId: {id}", id=dto.connectionId)
            connection = self.collection_connection.find_one({"_id": dto.connectionId})
            if connection and connection.get("databaseType", "") == "s3":
                access_key = connection.get("username", "")
                secret_key = connection.get("password", "")
                address = f"http://{connection.get('host', '')}:{connection.get('port', 8000)}"
                bucket_name = connection.get("database", "")
                try:
                    s3_util = NewBaseBoto3(access_key, secret_key, address).client
                except Exception:
                    logger.info(
                        "Cannot connect to custom s3 connection: {id}", id=dto.connectionId
                    )

        if "image" in mime_type and dto.rescaleFile:
            contents = self.resize_image(file.file, dto.scaleFactor)

        if file_size_mb > 100:
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                shutil.copyfileobj(contents, temp)
                temp_path = temp.name

            upload_id = s3_util.create_multipart_upload(
                Bucket=bucket_name, Key=file_path
            )["UploadId"]

            chunk_size = 5 * 1024 * 1024
            parts = []
            part_number = 1

            try:
                with open(temp_path, "rb") as f:
                    while True:
                        file_chunk = f.read(chunk_size)
                        if not file_chunk:
                            break

                        resp = s3_util.upload_part(
                            Bucket=bucket_name,
                            Key=file_path,
                            PartNumber=part_number,
                            UploadId=upload_id,
                            Body=file_chunk,
                        )
                        parts.append({"PartNumber": part_number, "ETag": resp["ETag"]})
                        part_number += 1

                s3_util.complete_multipart_upload(
                    Bucket=bucket_name,
                    Key=file_path,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
            except Exception:
                s3_util.abort_multipart_upload(
                    Bucket=bucket_name, Key=file_path, UploadId=upload_id
                )
                raise
            finally:
                os.remove(temp_path)

        else:
            s3_util.upload_fileobj(
                contents,
                Bucket=bucket_name,
                Key=file_path,
                ExtraArgs={"ContentType": mime_type},
            )

        logger.info("File {id} uploaded to S3 successfully.", id=_id)
        data["path"] = f"s3://{bucket_name}/{file_path}"
        data["mimeType"] = mime_type
        data["filesize"] = file.size
        self.collection.update_one({"_id": _id}, {"$set": data}, upsert=True)
        logger.info("Metadata for {id} saved to DB.", id=_id)

        data["id"] = _id
        if dto.extractFile:
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_SERVER,
                value_serializer=lambda v: json.dumps(v, default=date_converter).encode(
                    "ascii"
                ),
                max_request_size=settings.KAFKA_MAX_REQUEST,
            )
            producer.send(settings.KAFKA_TOPIC_FILE_EXTRACTION, value=data)
            logger.info("File {id} queued for extraction.", id=_id)
            producer.flush()
            producer.close()

        return data

    def get_by_id(self, _id):
        data = self.collection.find_one({"_id": _id})
        if data:
            data["id"] = data.pop("_id")
            return data
        return {}

    def get_all(self, dto):
        query = mongo_query_builder(dto, text_type="type,name")
        data = (
            self.collection_view.find(query)
            .skip((dto.page - 1) * dto.size)
            .limit(dto.size)
            .sort(dto.orderBy, -1 if dto.order.lower() == "desc" else 1)
        )

        return change_field_id(list(data)), self.collection.count_documents(query)

    def delete(self, _id):
        data = self.get_by_id(_id)
        if data:
            try:
                self.s3.delete_object(
                    Bucket=(settings.S3FS_PATH_AGENT or "").replace("s3://", ""),
                    Key=data["path"].replace(f"{settings.S3FS_PATH_AGENT}/", ""),
                )
            except FileNotFoundError:
                pass
            self.collection.delete_one({"_id": _id})

        return f"File: {data['path']} {_id} has been deleted."
