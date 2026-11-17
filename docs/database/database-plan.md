# QUIZVERSE Relational Database Blueprint (Phase 3 Preparation)

## 1. Engine & Hosting
- **Engine**: PostgreSQL 15+ hosted on Supabase Cloud Free Tier.
- **Access Strategy**:
  - Web client connects via public anon key subject to Row Level Security (RLS).
  - Backend API connects via service-role key for administrative tasks and grading audits.

---

## 2. Entity-Relationship Schema Outline

```mermaid
erDiagram
    PROFILES ||--o{ QUIZZES : creates
    QUIZZES ||--|{ QUESTIONS : contains
    QUESTIONS ||--|{ QUESTION_OPTIONS : has
    QUIZZES ||--o{ EXAM_SESSIONS : takes
    PROFILES ||--o{ EXAM_SESSIONS : participates
    EXAM_SESSIONS ||--o{ EXAM_RESPONSES : records
    EXAM_SESSIONS ||--o{ AUDIT_LOGS : generates

    PROFILES {
        uuid id PK
        string email
        string full_name
        string role
        timestamptz created_at
    }

    QUIZZES {
        uuid id PK
        string title
        string slug
        int duration_minutes
        int passing_score
        string status
        boolean is_3d_enabled
        uuid created_by FK
    }

    QUESTIONS {
        uuid id PK
        uuid quiz_id FK
        string title
        string type
        int points
        jsonb metadata_3d
        int order_index
    }

    QUESTION_OPTIONS {
        uuid id PK
        uuid question_id FK
        string text
        boolean is_correct
    }

    EXAM_SESSIONS {
        uuid id PK
        uuid quiz_id FK
        uuid candidate_id FK
        string access_token
        string status
        int total_score
        timestamptz started_at
        timestamptz completed_at
    }

    EXAM_RESPONSES {
        uuid id PK
        uuid session_id FK
        uuid question_id FK
        jsonb selected_option_ids
        boolean is_correct
        int score_awarded
    }

    AUDIT_LOGS {
        uuid id PK
        uuid session_id FK
        string event_type
        jsonb telemetry_data
        timestamptz created_at
    }
```

---

## 3. Row Level Security (RLS) Strategy

All tables in Phase 3 will have Row Level Security explicitly enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).

| Table | SELECT Policy | INSERT/UPDATE Policy |
| :--- | :--- | :--- |
| `profiles` | Users can view own profile; Admins view all | Users can update own profile name/avatar |
| `quizzes` | Published quizzes visible to all; Drafts visible to creator/admin | Creators & Admins only |
| `questions` | Hidden during active exam; Admins view all | Creators & Admins only |
| `question_options` | Correct answer flag stripped for student queries | Creators & Admins only |
| `exam_sessions` | Candidates can only view their own session | Inserted upon valid token submission |
| `audit_logs` | Invisible to candidate; Admins view all | Insertable by active candidate session |

---

## 4. Realtime & Storage Preparation
- **Realtime Channels**:
  - `quiz-session:<id>`: Broadcasts candidate heartbeats, proctor announcements, and time sync updates.
- **Storage Buckets**:
  - `exam-assets`: Public read access for 3D GLTF models, texture maps, and question illustration media.
