from .providers import LocalExportProvider
from backend.app.core.config import settings

# Global export provider instance
export_provider = LocalExportProvider(base_dir=settings.exports_dir)
