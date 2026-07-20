from backend.app.core.config import settings

from .providers import LocalExportProvider

# Global export provider instance
export_provider = LocalExportProvider(base_dir=settings.exports_dir)
