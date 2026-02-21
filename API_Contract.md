# Scans

 Scan object
```
{
  id: string
  repo_path: string
  commit_sha: string
  status: string (queued | running | completed | failed)
  rot_score: float
  mismatch_count: integer
  created_at: datetime (ISO 8601)
  updated_at: datetime (ISO 8601)
}
```

## GET /scans
Returns all scans in the system.

* **URL Params**

   None

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response**:

  Code: 200

  Content:
```
{
  scans: [
    {<scan_object>},
    {<scan_object>},
    {<scan_object>}
  ]
}
```

## GET /scans/:id
Returns the specified scan.

* **URL Params**

  Required: ```id=[string]```

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response:**

  Code: 200

  Content: ``` { <scan_object> } ```

* **Error Response:**

  Code: 404

  Content: ```{ error: "Scan does not exist" }```


## POST /scans
Creates a new scan and returns the scan object.

* **URL Params**

  None

* **Headers**

  Content-Type: application/json

* **Data Params**
```
{
  repo_path: string,
  config_path: string,
  commit_sha: string (optional)
}
```

* **Success Response:**

  Code: 200

  Content: ```{ <scan_object> }```

* **Error Response:**

  Code: 400

  Content: ```{ error: "Invalid configuration or repository path" }```


## DELETE /scans/:id
Deletes the specified scan record.

* **URL Params**

  Required: ```id=[string]```

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response**:

   Code: 204

* **Error Response:**

  Code: 404

   Content: ```{ error: "Scan does not exist" }```

# Reports

Report object
```
{
  scan_id: string
  repo_path: string
  timestamp: datetime (ISO 8601)

  summary: {
    rot_score: float,
    mismatch_count: integer,
    status: string (clean | mismatch)
  },

  code_index: {
    files: integer,
    symbols: integer
  },

  doc_index: {
    docs: integer,
    references: integer
  },

  mismatches: [
    {<mismatch_object>},
    {<mismatch_object>}
  ]
}
```
## GET /scans/:id/report
Returns the full scan report.

* **URL Params**

  Required: id=[string]

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response:**
 
  Code: 200
  
  Content: ```{ <report_object> }```

* **Error Response:**

  Code: 404

  Content: ```{ error: "Scan does not exist" }```

  OR

  Code: 409
 
  Content: ```{ error: "Scan not completed yet" }```

# Mismatches

Mismatch object
```
{
  type: string (MISSING_TARGET | CHANGED_TARGET | MOVED_TARGET)
  severity: string (low | medium | high)

  doc: {
    path: string,
    line: integer,
    reference: string
  },

  code: {
    path: string,
    symbol: string,
    current_hash: string,
    baseline_hash: string
  },

  message: string,
  suggested_action: string
}
```

## GET /scans/:id/mismatches
Returns all mismatches for a scan.

* **URL Params**
  
  Required: id=[string]

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response:**

  Code: 200

  Content:
```
{
  mismatches: [
    {<mismatch_object>},
    {<mismatch_object>},
    {<mismatch_object>}
  ]
}
```

* **Error Response:**
 
  Code: 404

  Content: ```{ error: "Scan does not exist" }```

# Configuration

Configuration object
```
{
  version: integer,
  language: string,
  docs: {
    root: string,
    include: [string],
    exclude: [string]
  },
  code: {
    root: string,
    include: [string],
    exclude: [string]
  },
  references: {
    mode: string,
    tag: string
  },
  hash_store: {
    path: string
  },
  output: {
    report_path: string,
    pretty: boolean
  }
}
```

## GET /config
Returns the active configuration.

* **URL Params**

  None

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response:**

  Code: 200

  Content: ```{ <configuration_object> }```

## PUT /config
Updates configuration.

* **URL Params**

  None

* **Headers**

  Content-Type: application/json

* **Data Params**

   ```{ <configuration_object> }```

* **Success Response:**

  Code: 200

  Content: ```{ <configuration_object> }```

* **Error Response:**

  Code: 400

  Content: ```{ error: "Invalid configuration format" }```

# Hashes

```
Hash object
{
  file: string,
  symbol: string,
  hash: string (sha256),
  start_line: integer,
  end_line: integer
}
```

## GET /hashes
Returns stored baseline hashes.

* **URL Params**
  
  None

* **Data Params**

  None

* **Headers**

  Content-Type: application/json

* **Success Response:**

  Code: 200

  Content:
```
{
  hashes: [
    {<hash_object>},
    {<hash_object>}
  ]
}
```

## POST /hashes/update
Updates the baseline hash store.

* URL Params

  None

* Headers

  Content-Type: application/json

* Data Params
```
{
  scan_id: string
}
```

* Success Response:
  
  Code: 200

  Content: ```{ message: "Baseline updated successfully" }```

* Error Response:

   Code: 404

  Content: ```{ error: "Scan does not exist" }```
