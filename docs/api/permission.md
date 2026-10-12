# API Permission Specifications

**Version:** 1.0.0

REST API for Vibe Codebase — cover permissions.

---

## Permission :lock:

> All permission endpoints require `JWTBearer`.

### `POST /permission/add`

Add a new permission.

**Request Body** — `PermissionDTO`

| Field | Type | Required |
|---|---|---|
| `name` | string | no |
| `description` | string | no |
| `alias` | string | no |
| `type` | string | no |
| `privileges` | list \| object | no |
| `parentId` | string | no |
| `image` | string | no |
| `createdBy` | string | no |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "alias": "string",
    "type": "string",
    "privileges": [],
    "parentId": "string",
    "image": "string",
    "createdBy": "string",
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Permission added successfully |
| `400` | Failed to add permission |

---

### `PUT /permission/update`

Update a permission (full update).

**Request Body** — `UpdatePermissionDTO` (extends `PermissionDTO` + `id`)

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| *(all PermissionDTO fields are optional)* | | |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "privileges": [],
    "updatedAt": "datetime"
  }
}
```

---

### `PUT /permission/update-partial`

Update a permission (partial update — merges privileges with existing ones).

**Request Body** — `UpdatePermissionDTO`

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| *(only fields to be changed)* | | |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "privileges": [],
    "updatedAt": "datetime"
  }
}
```

> The `privileges` field is merged (combined) with existing privileges, not replaced.

---

### `DELETE /permission/delete`

Delete a permission.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `id` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": "{id} has been deleted."
}
```

---

### `POST /permission/get-all`

List permissions with pagination & filter.

**Request Body** — `FindDTO`

**Response `200`**

```json
{
  "metaData": {
    "status": true,
    "executionTime": 5,
    "responseCode": 200,
    "message": "Success",
    "pagination": { "size": 10, "totalElements": 30, "totalPages": 3, "scrollId": "" }
  },
  "data": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "alias": "string",
      "type": "string",
      "privileges": [],
      "createdAt": "datetime"
    }
  ]
}
```

---

### `GET /permission/get-one`

Get permission details by ID.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `id` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "alias": "string",
    "type": "string",
    "privileges": [],
    "parentId": "string",
    "image": "string",
    "createdBy": "string",
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
}
```

---

## Schema

### Permission

| Field | Type | Description |
|---|---|---|
| `id` | string | Primary key |
| `name` | string | Permission/role name |
| `description` | string | Description |
| `alias` | string | Alias |
| `type` | string | Type |
| `privileges` | list \| object | Privilege list |
| `parentId` | string | Parent permission |
| `image` | string | Image URL |
| `createdBy` | string | Created by |
| `createdAt` | datetime | Created at |
| `updatedAt` | datetime | Updated at |

---

> :lock: = Endpoint requires Bearer Token (JWT)