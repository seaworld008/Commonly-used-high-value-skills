# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

### Prisma Schema

```prisma
// schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ── Multi-tenancy ─────────────────────────────────────────────────────────────

model Organization {
  id        String   @id @default(cuid())
  name      String
  slug      String   @unique
  plan      Plan     @default(FREE)
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")
  deletedAt DateTime? @map("deleted_at")

  users      OrganizationMember[]
  projects   Project[]
  auditLogs  AuditLog[]

  @@map("organizations")
}

model OrganizationMember {
  id             String   @id @default(cuid())
  organizationId String   @map("organization_id")
  userId         String   @map("user_id")
  role           OrgRole  @default(MEMBER)
  joinedAt       DateTime @default(now()) @map("joined_at")

  organization Organization @relation(fields: [organizationId], references: [id], onDelete: Cascade)
  user         User         @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@unique([organizationId, userId])
  @@index([userId])
  @@map("organization_members")
}

model User {
  id           String    @id @default(cuid())
  email        String    @unique
  name         String?
  avatarUrl    String?   @map("avatar_url")
  passwordHash String?   @map("password_hash")
  emailVerifiedAt DateTime? @map("email_verified_at")
  lastLoginAt  DateTime? @map("last_login_at")
  createdAt    DateTime  @default(now()) @map("created_at")
  updatedAt    DateTime  @updatedAt @map("updated_at")
  deletedAt    DateTime? @map("deleted_at")

  memberships  OrganizationMember[]
  ownedProjects Project[]           @relation("ProjectOwner")
  assignedTasks TaskAssignment[]
  comments     Comment[]
  auditLogs    AuditLog[]

  @@map("users")
}

// ── Core entities ─────────────────────────────────────────────────────────────

model Project {
  id             String   @id @default(cuid())
  organizationId String   @map("organization_id")
  ownerId        String   @map("owner_id")
  name           String
  description    String?
  status         ProjectStatus @default(ACTIVE)
  settings       Json     @default("{}")
  createdAt      DateTime @default(now()) @map("created_at")
  updatedAt      DateTime @updatedAt @map("updated_at")
  deletedAt      DateTime? @map("deleted_at")

  organization Organization @relation(fields: [organizationId], references: [id])
  owner        User         @relation("ProjectOwner", fields: [ownerId], references: [id])
  tasks        Task[]
  labels       Label[]

  @@index([organizationId])
  @@index([organizationId, status])
  @@index([deletedAt])
  @@map("projects")
}

model Task {
  id          String     @id @default(cuid())
  projectId   String     @map("project_id")
  title       String
  description String?
  status      TaskStatus @default(TODO)
  priority    Priority   @default(MEDIUM)
  dueDate     DateTime?  @map("due_date")
  position    Float      @default(0)          // For drag-and-drop ordering
  version     Int        @default(1)           // Optimistic locking
  createdById String     @map("created_by_id")
  updatedById String     @map("updated_by_id")
  createdAt   DateTime   @default(now()) @map("created_at")
  updatedAt   DateTime   @updatedAt @map("updated_at")
  deletedAt   DateTime?  @map("deleted_at")

  project     Project          @relation(fields: [projectId], references: [id])
  assignments TaskAssignment[]
  labels      TaskLabel[]
  comments    Comment[]
  attachments Attachment[]

  @@index([projectId])
  @@index([projectId, status])
  @@index([projectId, deletedAt])
  @@index([dueDate], where: { deletedAt: null })  // Partial index
  @@map("tasks")
}

// ── Polymorphic attachments ───────────────────────────────────────────────────

model Attachment {
  id           String   @id @default(cuid())
  // Polymorphic association
  entityType   String   @map("entity_type")   // "task" | "comment"
  entityId     String   @map("entity_id")
  filename     String
  mimeType     String   @map("mime_type")
  sizeBytes    Int      @map("size_bytes")
  storageKey   String   @map("storage_key")   // S3 key
  uploadedById String   @map("uploaded_by_id")
  createdAt    DateTime @default(now()) @map("created_at")

  // Only one concrete relation (task) — polymorphic handled at app level
  task      Task? @relation(fields: [entityId], references: [id], map: "attachment_task_fk")

  @@index([entityType, entityId])
  @@map("attachments")
}

// ── Audit trail ───────────────────────────────────────────────────────────────

model AuditLog {
  id             String   @id @default(cuid())
  organizationId String   @map("organization_id")
  userId         String?  @map("user_id")
  action         String                           // "task.created", "task.status_changed"
  entityType     String   @map("entity_type")
  entityId       String   @map("entity_id")
  before         Json?                            // Previous state
  after          Json?                            // New state
  ipAddress      String?  @map("ip_address")
  userAgent      String?  @map("user_agent")
  createdAt      DateTime @default(now()) @map("created_at")

  organization Organization @relation(fields: [organizationId], references: [id])
  user         User?        @relation(fields: [userId], references: [id])

  @@index([organizationId, createdAt(sort: Desc)])
  @@index([entityType, entityId])
  @@index([userId])
  @@map("audit_logs")
}

enum Plan        { FREE STARTER GROWTH ENTERPRISE }
enum OrgRole     { OWNER ADMIN MEMBER VIEWER }
enum ProjectStatus { ACTIVE ARCHIVED }
enum TaskStatus  { TODO IN_PROGRESS IN_REVIEW DONE CANCELLED }
enum Priority    { LOW MEDIUM HIGH CRITICAL }
```

---
