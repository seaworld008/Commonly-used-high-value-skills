# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

### Data Structure

Each debt item is tracked with the following attributes:

```json
{
  "id": "DEBT-2024-001",
  "title": "Legacy user authentication module",
  "category": "code",
  "subcategory": "error_handling",
  "location": "src/auth/legacy_auth.py:45-120",
  "description": "Authentication error handling uses generic exceptions",
  "impact": {
    "velocity": 7,
    "quality": 8,
    "productivity": 6,
    "business": 5
  },
  "effort": {
    "size": "M",
    "risk": "medium",
    "skill_required": "mid"
  },
  "interest_rate": 105,
  "cost_of_delay": 378,
  "priority": "high",
  "created_date": "2024-01-15",
  "last_updated": "2024-01-20",
  "assigned_to": null,
  "status": "identified",
  "tags": ["security", "user-experience", "maintainability"]
}
```

<a id="section-2"></a>

### Impact Assessment (1-10 scale)

**Development Velocity Impact**
- 1-2: Negligible impact on development speed
- 3-4: Minor slowdown, workarounds available
- 5-6: Moderate impact, affects some features
- 7-8: Significant slowdown, affects most work
- 9-10: Critical blocker, prevents new development

**Quality Impact**
- 1-2: No impact on defect rates
- 3-4: Minor increase in minor bugs
- 5-6: Moderate increase in defects
- 7-8: Regular production issues
- 9-10: Critical reliability problems

**Team Productivity Impact**
- 1-2: No impact on team morale or efficiency
- 3-4: Occasional frustration
- 5-6: Regular complaints from developers
- 7-8: Team actively avoiding the area
- 9-10: Causing developer turnover

**Business Impact**
- 1-2: No customer-facing impact
- 3-4: Minor UX degradation
- 5-6: Moderate performance impact
- 7-8: Customer complaints or churn
- 9-10: Revenue-impacting issues

<a id="section-3"></a>

### 5. Dependency Debt
Issues related to external libraries, frameworks, and system dependencies.

**Indicators:**
- Outdated packages with known security vulnerabilities
- Dependencies with incompatible licenses
- Unused dependencies bloating the build
- Version conflicts between packages
- Deprecated APIs still in use
- Heavy dependencies for simple tasks
- Missing dependency pinning

**Impact:**
- Security vulnerabilities
- Build instability
- Longer build times
- Legal compliance issues
- Difficulty upgrading core frameworks

**Detection Methods:**
- Vulnerability scanning
- License compliance checking
- Usage analysis
- Version compatibility checking

<a id="section-4"></a>

### 1. Code Debt
Code-level issues that make the codebase harder to understand, modify, and maintain.

**Indicators:**
- Long functions (>50 lines for complex logic, >20 for simple operations)
- Deep nesting (>4 levels of indentation)
- High cyclomatic complexity (>10)
- Duplicate code patterns (>3 similar blocks)
- Missing or inadequate error handling
- Poor variable/function naming
- Magic numbers and hardcoded values
- Commented-out code blocks

**Impact:**
- Increased debugging time
- Higher defect rates
- Slower feature development
- Knowledge silos (only original author understands the code)

**Detection Methods:**
- AST parsing for structural analysis
- Pattern matching for common anti-patterns
- Complexity metrics calculation
- Duplicate code detection algorithms
