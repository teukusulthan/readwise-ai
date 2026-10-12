# API Group Specifications

**Version:** 1.0.0

REST API for Vibe Codebase — cover groups.

---

## Group :lock:

> All group endpoints require `JWTBearer`.

### `POST /group/add`

Add a new group.

**Request Body** — `GroupDTO`

| Field | Type | Required |
|---|---|---|
| `name` | string | no |
| `description` | string | no |
| `parentId` | string | no |
| `image` | string | no |
| `settings` | object | no |
| `filters` | object[] | no |
| `personalization` | object | no |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "parentId": "string",
    "image": "string",
    "settings": {},
    "filters": [],
    "personalization": {},
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Group added successfully |
| `400` | Failed to add group |

---

### `PUT /group/update`

Update a group (full update).

**Request Body** — `UpdateGroupDTO` (extends `GroupDTO` + `id`)

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| *(all GroupDTO fields are optional)* | | |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "updatedAt": "datetime"
  }
}
```

---

### `DELETE /group/delete`

Delete a group.

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

### `POST /group/get-all`

List groups with pagination & filter.

**Request Body** — `FindDTO`

**Response `200`**

```json
{
  "metaData": {
    "status": true,
    "executionTime": 5,
    "responseCode": 200,
    "message": "Success",
    "pagination": { "size": 10, "totalElements": 50, "totalPages": 5, "scrollId": "" }
  },
  "data": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "parentId": "string",
      "image": "string",
      "createdAt": "datetime"
    }
  ]
}
```

---

### `GET /group/get-one`

Get group details by ID.

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
    "parentId": "string",
    "image": "string",
    "settings": {},
    "filters": [],
    "personalization": {},
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
}
```

---

## Schema

### Group

| Field | Type | Description |
|---|---|---|
| `id` | string | Primary key |
| `name` | string | Group name |
| `description` | string | Description |
| `parentId` | string | Parent group |
| `image` | string | Image URL |
| `settings` | object | Group settings |
| `filters` | object[] | Saved filters |
| `personalization` | object | Personalization |
| `createdAt` | datetime | Created at |
| `updatedAt` | datetime | Updated at |

> :lock: = Endpoint requires Bearer Token (JWT)