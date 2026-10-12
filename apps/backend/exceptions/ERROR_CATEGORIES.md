# Error Categories & Sub-Categories Reference

Complete list of `ErrorCategory` and `ErrorSubCategory` used in the Fusion exception system.

---

## RESOURCE_NOT_FOUND

The required resource is not found in the database.

| ErrorSubCategory          | Description                                     | Exception Class             | Used In                                        |
| ------------------------- | ----------------------------------------------- | --------------------------- | ---------------------------------------------- |
| `ACCOUNT_NOT_FOUND`       | Account not found                               | `ValidationException`       | `util/helper.py`                               |

---

## DATA_NOT_FOUND

Query executed successfully but returned no data.

| ErrorSubCategory   | Description                            | Exception Class         | Used In           |
| ------------------ | -------------------------------------- | ----------------------- | ----------------- |
| `EMPTY_RESULT_SET` | Query returns 0 rows / empty DataFrame | `DataNotFoundException` | `magic_parser.py` |

---

## VALIDATION_ERROR

Input validation failed.

| ErrorSubCategory          | Description                                                             | Exception Class       | Used In                                       |
| ------------------------- | ----------------------------------------------------------------------- | --------------------- | --------------------------------------------- |
| `MISSING_REQUIRED_FIELD`  | Required field is empty (field, table, sourceId, queryId)               | `ValidationException` | `util/helper.py`, `service/config_handler.py` |
| `INVALID_FILTER_VALUE`    | Filter value does not match the operator (is, isOneOf, gte, lte, range) | `ValidationException` | `util/helper.py`                              |
| `INVALID_FILTER_OPERATOR` | Invalid filter operator (e.g., unique values for multi-field)           | `ValidationException` | `util/helper.py`                              |
| `UNSUPPORTED_FILE_FORMAT` | Download file format is not supported                                   | `ValidationException` | `service/config_handler.py`                   |
| `TOPIC_NOT_FOUND`         | Topic not found during topic management filtering                       | `ValidationException` | `util/helper.py`                              |

---

## CONFIGURATION_ERROR

Required system configuration is missing or invalid.

| ErrorSubCategory            | Description                                      | Exception Class          | Used In                     |
| --------------------------- | ------------------------------------------------ | ------------------------ | --------------------------- |
| `MISSING_DATABASE`          | `database` configuration is empty on connection  | `ConfigurationException` | `service/config_handler.py` |
| `UNSUPPORTED_DATABASE_TYPE` | Database type is unrecognized                    | `ConfigurationException` | `service/config_handler.py` |
| `INDEX_PATTERN_MISMATCH`    | Number of indexes and index_pattern do not match | `ConfigurationException` | `magic_parser.py`           |

---

## CONNECTION_ERROR

Failed to connect or execute query to the database / external service.

| ErrorSubCategory       | Description                                         | Exception Class       | Used In           |
| ---------------------- | --------------------------------------------------- | --------------------- | ----------------- |
| `SQL_EXECUTION_FAILED` | SQL/PostgreSQL execution failed                     | `ConnectionException` | `magic_parser.py` |
| `ES_REQUEST_FAILED`    | Request to Elasticsearch failed (HTTP status ≥ 300) | `ConnectionException` | `magic_parser.py` |

---

## TIMEOUT_ERROR

Operation exceeded the specified time limit.

| ErrorSubCategory   | Description                                  | Exception Class    | Used In           |
| ------------------ | -------------------------------------------- | ------------------ | ----------------- |
| `DATABASE_TIMEOUT` | Database timeout (psycopg2 OperationalError) | `TimeoutException` | `magic_parser.py` |
| `REQUEST_TIMEOUT`  | HTTP request timeout to ES parser            | `TimeoutException` | `magic_parser.py` |

---

## PARSING_ERROR

Failed to parse structured data format (JSON, query, etc).

| ErrorSubCategory       | Description                                   | Exception Class    | Used In                                        |
| ---------------------- | --------------------------------------------- | ------------------ | ---------------------------------------------- |
| `INVALID_QUERY_FORMAT` | Failed to parse query (JSON/AST literal_eval) | `ParsingException` | `magic_parser.py`, `service/config_handler.py` |

---

## UNSUPPORTED_OPERATION

The requested operation is not supported in the current context.

| ErrorSubCategory         | Description                              | Exception Class                 | Used In                                        |
| ------------------------ | ---------------------------------------- | ------------------------------- | ---------------------------------------------- |
| `UNSUPPORTED_CHART_TYPE` | Chart type or operation is not supported | `UnsupportedOperationException` | `magic_parser.py`, `service/config_handler.py` |

---

## INTERNAL_ERROR

Unexpected internal error.

| ErrorSubCategory   | Description                    | Exception Class     | Used In           |
| ------------------ | ------------------------------ | ------------------- | ----------------- |
| `UNEXPECTED_ERROR` | Catch-all for unhandled errors | `InternalException` | `magic_parser.py` |

---

# Sample JSON Metadata per Error Category

Below are sample JSON `metaData` blocks that appear in the API response for each error category.

## RESOURCE_NOT_FOUND

```json
{
  "metaData": {
    "executionTime": "45ms",
    "message": "Error when get connection. Connetion `abc123` not found",
    "errorCategory": "RESOURCE_NOT_FOUND",
    "errorSubCategory": "CONNECTION_NOT_FOUND",
    "resourceType": "Connection",
    "resourceId": "abc123",
    "resourceName": null,
    "connectionId": "abc123"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "32ms",
    "message": "Error when get query. Query `my_query` not found",
    "errorCategory": "RESOURCE_NOT_FOUND",
    "errorSubCategory": "QUERY_NOT_FOUND",
    "resourceType": "Query",
    "resourceId": null,
    "resourceName": "my_query",
    "queryName": "my_query"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "28ms",
    "message": "Index Mapping not found. Details: ...",
    "errorCategory": "RESOURCE_NOT_FOUND",
    "errorSubCategory": "INDEX_MAPPING_NOT_FOUND",
    "resourceType": "Index Mapping",
    "resourceId": null,
    "resourceName": null,
    "originalError": "..."
  }
}
```

## DATA_NOT_FOUND

```json
{
  "metaData": {
    "executionTime": "230ms",
    "message": "Sorry, the data you requested was not found in the database. Please check the configuration again, okay?",
    "errorCategory": "DATA_NOT_FOUND",
    "errorSubCategory": "EMPTY_RESULT_SET",
    "databaseType": "qdrant"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "310ms",
    "message": "Sorry, the data you requested was not found in the database. Please check the configuration again, okay?",
    "errorCategory": "DATA_NOT_FOUND",
    "errorSubCategory": "EMPTY_RESULT_SET",
    "queryInfo": [
      "_query_execution:{\"query\": {...}, \"index\": \"my_index\", \"log_config\": {...}}"
    ]
  },
  "additionalInfo": {
    "index/database": "my_index",
    "query": { "...": "..." }
  }
}
```

## VALIDATION_ERROR

```json
{
  "metaData": {
    "executionTime": "12ms",
    "message": "SQL filter at index 2: 'field' cannot be empty. Each filter must specify the column to filter on.",
    "errorCategory": "VALIDATION_ERROR",
    "errorSubCategory": "MISSING_REQUIRED_FIELD",
    "fieldName": "field",
    "filterIndex": 2,
    "operator": "is"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "15ms",
    "message": "Filter operator 'is between' requires both 'value.gte' and 'value.lte'. Missing: gte, lte.",
    "errorCategory": "VALIDATION_ERROR",
    "errorSubCategory": "INVALID_FILTER_VALUE",
    "fieldName": "created_at",
    "operator": "is between",
    "field": "created_at",
    "missingFields": ["gte", "lte"],
    "expectedFormat": { "value": { "gte": "<start>", "lte": "<end>" } }
  }
}
```

```json
{
  "metaData": {
    "executionTime": "18ms",
    "message": "Filter operator 'unique values' on Elasticsearch only supports a single field.",
    "errorCategory": "VALIDATION_ERROR",
    "errorSubCategory": "INVALID_FILTER_OPERATOR",
    "fieldName": "[\"field1\", \"field2\"]",
    "operator": "unique values",
    "fieldsProvided": ["field1", "field2"]
  }
}
```

```json
{
  "metaData": {
    "executionTime": "20ms",
    "message": "File format pdf is not supported!",
    "errorCategory": "VALIDATION_ERROR",
    "errorSubCategory": "UNSUPPORTED_FILE_FORMAT",
    "fieldName": "file_format",
    "expectedValue": "csv, xlsx",
    "actualValue": "pdf"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "55ms",
    "message": "Topic not found for topic management filter. Please verify the topic ID: 'topic-xyz'",
    "errorCategory": "VALIDATION_ERROR",
    "errorSubCategory": "TOPIC_NOT_FOUND",
    "fieldName": "media_tags.keyword",
    "operator": "is contains topic management",
    "topicId": "topic-xyz"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "48ms",
    "message": "Account(s) not found for account management filter. Please verify the account IDs.",
    "errorCategory": "VALIDATION_ERROR",
    "errorSubCategory": "ACCOUNT_NOT_FOUND",
    "fieldName": "scAccountId.keyword",
    "operator": "is contain account management",
    "accountIds": ["acc-001", "acc-002"]
  }
}
```

## CONFIGURATION_ERROR

```json
{
  "metaData": {
    "executionTime": "22ms",
    "message": "database cannot be empty",
    "errorCategory": "CONFIGURATION_ERROR",
    "errorSubCategory": "MISSING_DATABASE",
    "configKey": "database",
    "connectionId": "conn-123",
    "databaseType": "postgresql"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "18ms",
    "message": "Type is not found: Type oracle",
    "errorCategory": "CONFIGURATION_ERROR",
    "errorSubCategory": "UNSUPPORTED_DATABASE_TYPE",
    "configKey": "database_type",
    "providedType": "oracle"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "25ms",
    "message": "index and index_pattern length mismatch (index=2, index_pattern=3)",
    "errorCategory": "CONFIGURATION_ERROR",
    "errorSubCategory": "INDEX_PATTERN_MISMATCH",
    "configKey": "index_pattern",
    "indexCount": 2,
    "patternCount": 3
  }
}
```

## CONNECTION_ERROR

```json
{
  "metaData": {
    "executionTime": "1520ms",
    "message": "SQL query execution failed (with filter): column \"nonexistent\" does not exist",
    "errorCategory": "CONNECTION_ERROR",
    "errorSubCategory": "SQL_EXECUTION_FAILED",
    "queryInfo": [
      "_query_execution:{\"query\": \"SELECT ...\", \"index\": \"mydb\", \"log_query\": {...}}"
    ]
  },
  "additionalInfo": {
    "index/database": "mydb",
    "query": "SELECT ..."
  }
}
```

```json
{
  "metaData": {
    "executionTime": "820ms",
    "message": "Error when requests to elasticsearch. {\"detail\": \"search_phase_execution_exception\"}",
    "errorCategory": "CONNECTION_ERROR",
    "errorSubCategory": "ES_REQUEST_FAILED",
    "serviceName": "FUSION_ES_PARSER",
    "status_code": 400
  }
}
```

## TIMEOUT_ERROR

```json
{
  "metaData": {
    "executionTime": "30000ms",
    "message": "Sorry, your request timed out. The query took too long to process.",
    "errorCategory": "TIMEOUT_ERROR",
    "errorSubCategory": "DATABASE_TIMEOUT",
    "operation": "postgresql_query",
    "query": "SELECT ...",
    "error": "could not receive data from server: timeout expired"
  }
}
```

```json
{
  "metaData": {
    "executionTime": "15000ms",
    "message": "Sorry, your request timed out. The query took too long to process.",
    "errorCategory": "TIMEOUT_ERROR",
    "errorSubCategory": "REQUEST_TIMEOUT",
    "operation": "elasticsearch_request"
  }
}
```

## PARSING_ERROR

```json
{
  "metaData": {
    "executionTime": "8ms",
    "message": "Invalid query format",
    "errorCategory": "PARSING_ERROR",
    "errorSubCategory": "INVALID_QUERY_FORMAT",
    "parseType": "query_parsing",
    "originalError": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
  }
}
```

## UNSUPPORTED_OPERATION

```json
{
  "metaData": {
    "executionTime": "10ms",
    "message": "Sorry, Currently we do not support chart maps from Qdrant",
    "errorCategory": "UNSUPPORTED_OPERATION",
    "errorSubCategory": "UNSUPPORTED_CHART_TYPE",
    "operation": "chart_maps",
    "context": "qdrant",
    "chartType": "Maps"
  }
}
```

## INTERNAL_ERROR

```json
{
  "metaData": {
    "executionTime": "500ms",
    "message": "Error from `FUSION_ES_PARSER`. Details: Connection refused",
    "errorCategory": "INTERNAL_ERROR",
    "errorSubCategory": "UNEXPECTED_ERROR",
    "originalError": "Connection refused",
    "parser": "FUSION_ES_PARSER"
  }
}
```
