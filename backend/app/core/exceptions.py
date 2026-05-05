"""Application-wide exception classes and handlers."""

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application error."""

    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.error_message = message
        self.details = details
        super().__init__(status_code=status_code, detail={"error": {"code": code, "message": message, "details": details}})


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Invalid or expired authentication credentials"):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(code="FORBIDDEN", message=message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(code="NOT_FOUND", message=f"{resource} not found", status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(code="CONFLICT", message=message, status_code=status.HTTP_409_CONFLICT)
