from pathlib import Path

import magic
from zipfile import ZipFile, is_zipfile
from lxml import etree


SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "image",
    "image/jpeg": "image",
}


def detect_file_type(path: Path) -> tuple[str, str]:
    """
    Identify a file using its actual contents rather than
    trusting its filename extension.

    Returns:
        tuple[str, str]:
            logical file type and detected MIME type.
    """

    mime_type = magic.from_file(str(path), mime=True)

    # Some Windows libmagic builds report OOXML as ZIP/octet-stream. Inspect
    # package content types and the actual main part, never the extension.
    if is_zipfile(path):
        try:
            with ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise ValueError("Ambiguous document package")
                parser = etree.XMLParser(resolve_entities=False, no_network=True)
                root = etree.fromstring(archive.read("[Content_Types].xml"), parser)
                types = {n.get("PartName"): n.get("ContentType") for n in root
                         if etree.QName(n).localname == "Override"}
                candidates = []
                for part, content, kind, namespace in [
                    ("/word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
                     "docx", "http://schemas.openxmlformats.org/wordprocessingml/2006/main"),
                    ("/ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
                     "pptx", "http://schemas.openxmlformats.org/presentationml/2006/main")]:
                    if types.get(part) == content:
                        main = etree.fromstring(archive.read(part.lstrip("/")), parser)
                        if etree.QName(main).namespace != namespace:
                            raise ValueError("Invalid document main part")
                        candidates.append(kind)
                if len(candidates) == 1:
                    kind = candidates[0]
                    return kind, next(m for m, k in SUPPORTED_MIME_TYPES.items() if k == kind)
                raise ValueError("Unsupported document package")
        except (KeyError, etree.XMLSyntaxError):
            raise ValueError("Invalid document package") from None

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            f"Unsupported file type: {mime_type}"
        )

    file_type = SUPPORTED_MIME_TYPES[mime_type]

    return file_type, mime_type
