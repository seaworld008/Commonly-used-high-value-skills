# Stage Design Patterns

## Marp Syntax

```markdown
---
marp: true
theme: default
paginate: true
header: "Title"
footer: "Author | Date"
---

# Slide Title

Content here

---

# Next Slide

- Bullet 1
- Bullet 2

<!-- Speaker notes go here -->
```

### Marp Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `<!-- _class: lead -->` | Title/lead slide style | Opening slides |
| `<!-- _class: invert -->` | Dark background | Emphasis slides |
| `<!-- _backgroundColor: #hex -->` | Custom background | Branded slides |
| `<!-- _color: #hex -->` | Text color | Contrast adjustment |
| `<!-- _paginate: false -->` | Hide page number | Title/closing slides |

## reveal.js Syntax

```html
<section>
  <h1>Slide Title</h1>
  <p>Content</p>
  <aside class="notes">Speaker notes</aside>
</section>

<section>
  <section>Vertical slide 1</section>
  <section>Vertical slide 2</section>
</section>
```

## Slidev Syntax

```markdown
---
theme: seriph
title: Presentation Title
---

# Slide 1

Content

---
transition: slide-left
---

# Slide 2

<v-click>Appears on click</v-click>

<!--
Speaker notes here
-->
```

## Narrative Arc Patterns

### Problem-Solution Arc

```
Slide 1: Hook (surprising stat or question)
Slide 2-3: Problem definition (pain points)
Slide 4: Impact/cost of the problem
Slide 5: Solution introduction
Slide 6-8: Solution demo/walkthrough
Slide 9: Results/proof
Slide 10: CTA
```

### AIDA Arc

```
Attention: Provocative opening (1 slide)
Interest: Why this matters (2-3 slides)
Desire: How it works, benefits (3-5 slides)
Action: What to do next (1-2 slides)
```

### Tutorial Arc

```
Goal: What you'll learn (1 slide)
Prerequisites: What you need (1 slide)
Steps: Step-by-step walkthrough (5-15 slides)
Summary: Key takeaways (1 slide)
Resources: Links and next steps (1 slide)
```

## Theme Design Patterns

### Minimal Dark

```yaml
theme:
  background: "#1a1a2e"
  text: "#eaeaea"
  accent: "#e94560"
  code_bg: "#16213e"
  font: "Inter, sans-serif"
  code_font: "JetBrains Mono, monospace"
```

### Corporate Light

```yaml
theme:
  background: "#ffffff"
  text: "#333333"
  accent: "#0066cc"
  code_bg: "#f5f5f5"
  font: "Noto Sans JP, sans-serif"
  code_font: "Source Code Pro, monospace"
```

## Code Slide Patterns

### Highlighted Code Block

```markdown
# Implementation

​```typescript {3-5|7-9}
function processOrder(order: Order) {
  // Step 1: Validate
  const validated = validate(order);
  if (!validated) throw new ValidationError();

  // Step 2: Process
  const result = await process(validated);
  return result;
}
​```
```

### Split Layout (Code + Explanation)

```markdown
# Architecture

::left::
​```typescript
const app = new Hono()
app.use(authMiddleware)
app.route('/api', apiRouter)
​```

::right::
1. Initialize framework
2. Apply auth middleware
3. Mount API routes
```

## Slide Count Guidelines

| Duration | Total slides | Content slides | Transition slides |
|----------|-------------|----------------|-------------------|
| 5 min LT | 8-12 | 6-8 | 2-4 |
| 15 min | 15-25 | 12-18 | 3-7 |
| 30 min | 30-45 | 25-35 | 5-10 |
| 45 min keynote | 45-70 | 35-50 | 10-20 |
