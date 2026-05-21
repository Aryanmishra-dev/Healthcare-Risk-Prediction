import re

with open("backend/app/api/v1/routes/upload.py", "r") as f:
    content = f.read()

# Add imports
imports = """from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.auth.dependencies import get_current_user
from backend.app.models.core import User, PDFUpload, UploadStatusEnum"""

content = content.replace("from pydantic import BaseModel", "from pydantic import BaseModel\n" + imports)

# Add dependencies to route
route_pattern = """async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="Medical report (PDF, JPG, JPEG, or PNG, ≤ 5 MB)"),
):"""

route_repl = """async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="Medical report (PDF, JPG, JPEG, or PNG, ≤ 5 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):"""

content = content.replace(route_pattern, route_repl)

# Add DB saving logic
save_logic = """
    # 5. Save to database
    upload_record = PDFUpload(
        user_id=current_user.id,
        filename=file.filename,
        file_path="virtual_path",
        file_size_kb=len(file_bytes) // 1024,
        upload_number=current_user.total_uploads + 1,
        extracted_data=entities,
        status=UploadStatusEnum.done
    )
    db.add(upload_record)
    current_user.total_uploads += 1
    await db.commit()
    await db.refresh(upload_record)
    
    # Attach upload_id to request state so predictions can link it
    request.state.upload_id = upload_record.id

    return {
"""
content = content.replace("    return {\n", save_logic)

with open("backend/app/api/v1/routes/upload.py", "w") as f:
    f.write(content)
print("Upload patch applied")
