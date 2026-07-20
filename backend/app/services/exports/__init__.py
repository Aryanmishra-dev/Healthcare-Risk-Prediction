from app.core.config import settings

from .providers import LocalExportProvider

# Default instance
export_provider = LocalExportProvider(base_dir=settings.exports_dir)
