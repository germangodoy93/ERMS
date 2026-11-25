"""Stores files through `app.core.storage` and keeps their metadata in `attachments`.

Photos are re-encoded before storing: this removes EXIF metadata (phones embed the GPS
location), fixes the orientation, limits the size and proves the file is a real image.
"""

import hashlib
import io
import logging
import uuid
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError, ServiceUnavailableError
from app.core.storage import Storage, StorageError
from app.modules.attachments.models import Attachment

logger = logging.getLogger(__name__)

ACCEPTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
MAX_PIXELS = 50_000_000  # rejects decompression bombs well before memory becomes an issue
MAX_SIDE = 2048
JPEG_QUALITY = 85


def normalize_photo(data: bytes) -> bytes:
    """Returns a clean JPEG or raises BusinessRuleError if the file is not a valid image."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in ACCEPTED_FORMATS:
                    raise BusinessRuleError("Solo se aceptan fotos JPG, PNG o WEBP.")
                if probe.width * probe.height > MAX_PIXELS:
                    raise BusinessRuleError("La foto tiene una resolución demasiado alta.")
                probe.verify()
            with Image.open(io.BytesIO(data)) as image:
                oriented = ImageOps.exif_transpose(image)
                rgb = oriented.convert("RGB")
                rgb.thumbnail((MAX_SIDE, MAX_SIDE))
                output = io.BytesIO()
                rgb.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                return output.getvalue()
    except BusinessRuleError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning) as exc:
        raise BusinessRuleError("El archivo no es una imagen válida.") from exc


class AttachmentService:
    def __init__(self, session: Session, storage: Storage) -> None:
        self._session = session
        self._storage = storage

    @property
    def demo(self) -> bool:
        return self._storage.demo

    def list_for(
        self, organization_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID
    ) -> list[Attachment]:
        return list(
            self._session.scalars(
                select(Attachment)
                .where(
                    Attachment.organization_id == organization_id,
                    Attachment.entity_type == entity_type,
                    Attachment.entity_id == entity_id,
                )
                .order_by(Attachment.created_at, Attachment.id)
            )
        )

    def count_for(self, organization_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID) -> int:
        return (
            self._session.scalar(
                select(func.count()).where(
                    Attachment.organization_id == organization_id,
                    Attachment.entity_type == entity_type,
                    Attachment.entity_id == entity_id,
                )
            )
            or 0
        )

    def get(self, organization_id: uuid.UUID, attachment_id: uuid.UUID) -> Attachment:
        attachment = self._session.scalar(
            select(Attachment).where(
                Attachment.id == attachment_id, Attachment.organization_id == organization_id
            )
        )
        if attachment is None:
            raise NotFoundError("El archivo no existe.")
        return attachment

    def store_photo(
        self,
        *,
        organization_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        data: bytes,
        file_name: str,
        uploaded_by_id: uuid.UUID,
    ) -> Attachment:
        clean = normalize_photo(data)
        attachment_id = uuid.uuid4()
        key = f"{organization_id}/{entity_type}/{entity_id}/{attachment_id}.jpg"
        attachment = Attachment(
            id=attachment_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            kind="PHOTO",
            storage_key=key,
            file_name=_safe_name(file_name),
            content_type="image/jpeg",
            size_bytes=len(clean),
            sha256=hashlib.sha256(clean).hexdigest(),
            uploaded_by_id=uploaded_by_id,
        )
        self._session.add(attachment)
        self._session.flush()
        # Written after the row is valid; if the transaction later fails, an orphan file may
        # remain, which is harmless (never served without its row). If the upload fails the
        # error rolls the row back.
        try:
            self._storage.put(key, clean)
        except StorageError as exc:
            logger.warning("Photo upload failed", extra={"error": str(exc)})
            raise ServiceUnavailableError(
                "No fue posible guardar la foto. Intente de nuevo en un momento."
            ) from exc
        return attachment

    def content(self, attachment: Attachment) -> bytes:
        try:
            return self._storage.get(attachment.storage_key)
        except StorageError as exc:
            if self._storage.demo:
                raise NotFoundError(
                    "El archivo ya no está disponible (almacenamiento de demostración)."
                ) from exc
            raise NotFoundError("El archivo no está disponible.") from exc

    def delete(self, attachment: Attachment) -> None:
        self._session.delete(attachment)
        self._session.flush()
        # The photo belongs to the customer: if it cannot be removed from storage the row
        # is kept (the error rolls back) so the deletion can be retried.
        try:
            self._storage.delete(attachment.storage_key)
        except StorageError as exc:
            logger.warning("Photo deletion failed", extra={"error": str(exc)})
            raise ServiceUnavailableError(
                "No fue posible eliminar la foto. Intente de nuevo en un momento."
            ) from exc


def _safe_name(name: str) -> str:
    base = name.replace("\\", "/").rsplit("/", 1)[-1].strip() or "foto"
    return "".join(c for c in base if c.isprintable())[:200] or "foto"
