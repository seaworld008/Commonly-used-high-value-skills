# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

#### Second Normal Form (2NF)
- **1NF Compliance**: Must satisfy First Normal Form
- **Full Functional Dependency**: Non-key attributes depend on the entire primary key
- **Partial Dependency Elimination**: Remove attributes that depend on part of a composite key

**Example Violation:**
```sql
-- BAD: Student course table with partial dependencies
CREATE TABLE student_courses (
    student_id INT,
    course_id INT,
    student_name VARCHAR(100),  -- Depends only on student_id
    course_name VARCHAR(100),   -- Depends only on course_id
    grade CHAR(1),
    PRIMARY KEY (student_id, course_id)
);

-- GOOD: Separate tables eliminate partial dependencies
CREATE TABLE students (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE courses (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE enrollments (
    student_id INT REFERENCES students(id),
    course_id INT REFERENCES courses(id),
    grade CHAR(1),
    PRIMARY KEY (student_id, course_id)
);
```

<a id="section-2"></a>

#### Third Normal Form (3NF)
- **2NF Compliance**: Must satisfy Second Normal Form
- **Transitive Dependency Elimination**: Non-key attributes should not depend on other non-key attributes
- **Direct Dependency**: Non-key attributes depend directly on the primary key

**Example Violation:**
```sql
-- BAD: Employee table with transitive dependency
CREATE TABLE employees (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    department_id INT,
    department_name VARCHAR(100),  -- Depends on department_id, not employee id
    department_budget DECIMAL(10,2) -- Transitive dependency
);

-- GOOD: Separate department information
CREATE TABLE departments (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    budget DECIMAL(10,2)
);

CREATE TABLE employees (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    department_id INT REFERENCES departments(id)
);
```
