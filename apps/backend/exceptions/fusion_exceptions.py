from enum import Enum
from typing import Optional, Dict, Any


class ErrorCategory(str, Enum):
    """
    Standardized error categories for the Fusion ecosystem.

    Used by downstream systems (UI, logging, analytics) to classify errors
    in a deterministic and consistent way.
    """

    # Resource / Data Errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"

    # Configuration / Setup Errors
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Query / Parsing Errors
    PARSING_ERROR = "PARSING_ERROR"
    QUERY_EXECUTION_ERROR = "QUERY_EXECUTION_ERROR"

    # Connection / Network Errors
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # Authorization Errors
    PERMISSION_ERROR = "PERMISSION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"

    # Operation Errors
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"

    # System Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorSubCategory(str, Enum):
    """
    Fine-grained error sub-categories within each ErrorCategory.

    Provides additional context for downstream systems to pinpoint
    the exact nature of the error without parsing messages.
    """

    # RESOURCE_NOT_FOUND sub-categories
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"

    # VALIDATION_ERROR sub-categories
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FILTER_VALUE = "INVALID_FILTER_VALUE"
    INVALID_FILTER_OPERATOR = "INVALID_FILTER_OPERATOR"
    UNSUPPORTED_FILE_FORMAT = "UNSUPPORTED_FILE_FORMAT"

    # CONFIGURATION_ERROR sub-categories
    MISSING_DATABASE = "MISSING_DATABASE"
    UNSUPPORTED_DATABASE_TYPE = "UNSUPPORTED_DATABASE_TYPE"
    INDEX_PATTERN_MISMATCH = "INDEX_PATTERN_MISMATCH"

    # CONNECTION_ERROR sub-categories
    SQL_EXECUTION_FAILED = "SQL_EXECUTION_FAILED"
    ES_REQUEST_FAILED = "ES_REQUEST_FAILED"

    # TIMEOUT_ERROR sub-categories
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"

    # DATA_NOT_FOUND sub-categories
    EMPTY_RESULT_SET = "EMPTY_RESULT_SET"

    # PARSING_ERROR sub-categories
    INVALID_QUERY_FORMAT = "INVALID_QUERY_FORMAT"

    # UNSUPPORTED_OPERATION sub-categories
    UNSUPPORTED_CHART_TYPE = "UNSUPPORTED_CHART_TYPE"

    # INTERNAL_ERROR sub-categories
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


# ---------------------------------------------------------------------------
# Base Exception
# ---------------------------------------------------------------------------

class FusionBaseException(Exception):
    """
    Base exception class for all Fusion errors.

    Every subclass automatically populates ``metaData.errorCategory`` and
    optionally ``metaData.errorSubCategory`` so that API consumers can
    classify the error without parsing messages.

    Attributes:
        message:              Human-readable error description.
        error_category:       One of :class:`ErrorCategory`.
        error_sub_category:   Optional :class:`ErrorSubCategory` for finer detail.
        meta_data:            Extra context shipped in the API response.
        original_exception:   Optional wrapped exception for chaining.
    """

    def __init__(
        self,
        message: str,
        error_category: ErrorCategory,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_category = error_category
        self.error_sub_category = error_sub_category
        self.meta_data = meta_data or {}
        self.original_exception = original_exception

        # Always present in metaData for downstream systems
        self.meta_data["errorCategory"] = error_category.value
        if error_sub_category:
            self.meta_data["errorSubCategory"] = error_sub_category.value

    # -- Serialisation helpers ------------------------------------------------

    def to_response_dict(self) -> Dict[str, Any]:
        """Convert exception to the standard API response envelope."""
        result = {
            "success": False,
            "message": self.message,
            "metaData": {
                "errorCategory": self.error_category.value,
                **self.meta_data,
            },
        }
        if self.error_sub_category:
            result["metaData"]["errorSubCategory"] = self.error_sub_category.value
        return result

    def __str__(self) -> str:
        sub = f"/{self.error_sub_category.value}" if self.error_sub_category else ""
        return f"[{self.error_category.value}{sub}] {self.message}"


# ---------------------------------------------------------------------------
# Concrete Exception Classes
# ---------------------------------------------------------------------------

class ResourceNotFoundException(FusionBaseException):
    """A required resource (connection, query, topic, data source …) was not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        message: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        identifier = resource_id or resource_name or "unknown"
        default_message = message or f"{resource_type} not found: '{identifier}'"

        meta = meta_data or {}
        meta.update({
            "resourceType": resource_type,
            "resourceId": resource_id,
            "resourceName": resource_name,
        })

        super().__init__(
            message=default_message,
            error_category=ErrorCategory.RESOURCE_NOT_FOUND,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class DataNotFoundException(FusionBaseException):
    """Query executed successfully but returned no data."""

    def __init__(
        self,
        message: str = "Sorry, the data you requested was not found in the database. Please check the configuration again, okay?",
        query_info: Optional[tuple] = None,
        error_sub_category: Optional[ErrorSubCategory] = ErrorSubCategory.EMPTY_RESULT_SET,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if query_info:
            meta["queryInfo"] = query_info

        super().__init__(
            message=message,
            error_category=ErrorCategory.DATA_NOT_FOUND,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class ConfigurationException(FusionBaseException):
    """Required configuration is missing or invalid."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if config_key:
            meta["configKey"] = config_key

        super().__init__(
            message=message,
            error_category=ErrorCategory.CONFIGURATION_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class ValidationException(FusionBaseException):
    """Input validation failed."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if field_name:
            meta["fieldName"] = field_name
        if expected_value:
            meta["expectedValue"] = expected_value
        if actual_value:
            meta["actualValue"] = actual_value

        super().__init__(
            message=message,
            error_category=ErrorCategory.VALIDATION_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class ParsingException(FusionBaseException):
    """Parsing JSON, query syntax, or other structured formats failed."""

    def __init__(
        self,
        message: str = "Invalid query or data format",
        parse_type: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = ErrorSubCategory.INVALID_QUERY_FORMAT,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if parse_type:
            meta["parseType"] = parse_type

        super().__init__(
            message=message,
            error_category=ErrorCategory.PARSING_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class QueryExecutionException(FusionBaseException):
    """Database query execution failed."""

    def __init__(
        self,
        message: str,
        database_type: Optional[str] = None,
        query: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if database_type:
            meta["databaseType"] = database_type
        if query:
            meta["query"] = query[:500]  # truncate for safety

        super().__init__(
            message=message,
            error_category=ErrorCategory.QUERY_EXECUTION_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class ConnectionException(FusionBaseException):
    """Unable to connect to a database or external service."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        host: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if service_name:
            meta["serviceName"] = service_name
        if host:
            meta["host"] = host

        super().__init__(
            message=message,
            error_category=ErrorCategory.CONNECTION_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class TimeoutException(FusionBaseException):
    """Operation timed out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        operation: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if operation:
            meta["operation"] = operation
        if timeout_seconds is not None:
            meta["timeoutSeconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_category=ErrorCategory.TIMEOUT_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class UnsupportedOperationException(FusionBaseException):
    """Operation not supported in the current context."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        context: Optional[str] = None,
        error_sub_category: Optional[ErrorSubCategory] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if operation:
            meta["operation"] = operation
        if context:
            meta["context"] = context

        super().__init__(
            message=message,
            error_category=ErrorCategory.UNSUPPORTED_OPERATION,
            error_sub_category=error_sub_category,
            meta_data=meta,
        )


class InternalException(FusionBaseException):
    """Unexpected internal / system error."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        error_sub_category: Optional[ErrorSubCategory] = ErrorSubCategory.UNEXPECTED_ERROR,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        meta = meta_data or {}
        if original_exception:
            meta["originalError"] = str(original_exception)

        super().__init__(
            message=message,
            error_category=ErrorCategory.INTERNAL_ERROR,
            error_sub_category=error_sub_category,
            meta_data=meta,
            original_exception=original_exception,
        )

