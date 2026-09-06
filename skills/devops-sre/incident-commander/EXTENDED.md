# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

#### Runbook Template Structure

```markdown
# {Service/Component} Incident Response Runbook

## Quick Reference
- **Severity Indicators:** {list of conditions for each severity level}
- **Key Contacts:** {on-call rotations and escalation paths}
- **Critical Commands:** {list of emergency commands with descriptions}

## Detection
### Monitoring Alerts
- {Alert name}: {description and thresholds}
- {Alert name}: {description and thresholds}

### Manual Detection Signs
- {Symptom}: {what to look for and where}
- {Symptom}: {what to look for and where}

## Initial Response (0-15 minutes)
1. **Assess Severity**
   - [ ] Check {primary metric}
   - [ ] Verify {secondary indicator}
   - [ ] Classify as SEV{level} based on {criteria}

2. **Establish Command**
   - [ ] Page Incident Commander if SEV1/2
   - [ ] Create incident tracking ticket
   - [ ] Join war room: {link/bridge info}

3. **Initial Investigation**
   - [ ] Check recent deployments: {deployment log location}
   - [ ] Review error logs: {log location and queries}
   - [ ] Verify dependencies: {dependency check commands}

## Mitigation Strategies
### Strategy 1: {Name}
**Use when:** {conditions}
**Steps:**
1. {detailed step with commands}
2. {detailed step with expected outcomes}
3. {validation step}

**Rollback Plan:**
1. {rollback step}
2. {verification step}

### Strategy 2: {Name}
{similar structure}

## Recovery and Validation
1. **Service Restoration**
   - [ ] {restoration step}
   - [ ] Wait for {metric} to return to normal
   - [ ] Validate end-to-end functionality

2. **Communication**
   - [ ] Update status page
   - [ ] Notify stakeholders
   - [ ] Schedule PIR

## Common Pitfalls
- **{Pitfall}:** {description and how to avoid}
- **{Pitfall}:** {description and how to avoid}

## Reference Information
- **Architecture Diagram:** {link}
- **Monitoring Dashboard:** {link}
- **Related Runbooks:** {links to dependent service runbooks}
```

<a id="section-2"></a>

#### Initial Incident Notification (SEV1/2)

```
Subject: [SEV{severity}] {Service Name} - {Brief Description}

Incident Details:
- Start Time: {timestamp}
- Severity: SEV{level}
- Impact: {user impact description}
- Current Status: {investigating/mitigating/resolved}

Technical Details:
- Affected Services: {service list}
- Symptoms: {what users are experiencing}
- Initial Assessment: {suspected root cause if known}

Response Team:
- Incident Commander: {name}
- Technical Lead: {name}
- SMEs Engaged: {list}

Next Update: {timestamp}
Status Page: {link}
War Room: {bridge/chat link}

---
{Incident Commander Name}
{Contact Information}
```

<a id="section-3"></a>

#### Executive Summary (SEV1)

```
Subject: URGENT - Customer-Impacting Outage - {Service Name}

Executive Summary:
{2-3 sentence description of customer impact and business implications}

Key Metrics:
- Time to Detection: {X minutes}
- Time to Engagement: {X minutes}
- Estimated Customer Impact: {number/percentage}
- Current Status: {status}
- ETA to Resolution: {time or "investigating"}

Leadership Actions Required:
- [ ] Customer communication approval
- [ ] PR/Communications coordination
- [ ] Resource allocation decisions
- [ ] External vendor engagement

Incident Commander: {name} ({contact})
Next Update: {time}

---
This is an automated alert from our incident response system.
```

<a id="section-4"></a>

#### Action Item Template

```
**Title:** {Concise description of the action}
**Priority:** {Critical/High/Medium/Low}
**Category:** {Fix/Process/Technical/Organizational}
**Owner:** {Assigned person}
**Due Date:** {Specific date}
**Success Criteria:** {How will we know this is complete}
**Dependencies:** {What needs to happen first}
**Related PIRs:** {Links to other incidents this addresses}

**Description:**
{Detailed description of what needs to be done and why}

**Implementation Plan:**
1. {Step 1}
2. {Step 2}
3. {Validation step}

**Progress Updates:**
- {Date}: {Progress update}
- {Date}: {Progress update}
```

<a id="section-5"></a>

#### Customer Communication Template

```
We are currently experiencing {brief description of issue} affecting {scope of impact}.

Our engineering team was alerted at {time} and is actively working to resolve the issue. We will provide updates every {frequency} until resolved.

What we know:
- {factual statement of impact}
- {factual statement of scope}
- {brief status of response}

What we're doing:
- {primary response action}
- {secondary response action}

Workaround (if available):
{workaround steps or "No workaround currently available"}

We apologize for the inconvenience and will share more information as it becomes available.

Next update: {time}
Status page: {link}
```

<a id="section-6"></a>

#### Primary Responsibilities

1. **Command and Control**
   - Own the incident response process
   - Make critical decisions about resource allocation
   - Coordinate between technical teams and stakeholders
   - Maintain situational awareness across all response streams

2. **Communication Hub**
   - Provide regular updates to stakeholders
   - Manage external communications (status pages, customer notifications)
   - Facilitate effective communication between response teams
   - Shield responders from external distractions

3. **Process Management**
   - Ensure proper incident tracking and documentation
   - Drive toward resolution while maintaining quality
   - Coordinate handoffs between team members
   - Plan and execute rollback strategies if needed

4. **Post-Incident Leadership**
   - Ensure thorough post-incident reviews are conducted
   - Drive implementation of preventive measures
   - Share learnings with broader organization

<a id="section-7"></a>

### Post-Incident

1. **Blameless Culture**
   - Focus on system failures, not individual mistakes
   - Encourage honest reporting of what went wrong
   - Celebrate learning and improvement opportunities

2. **Action Item Discipline**
   - Assign specific owners and due dates
   - Track progress publicly
   - Prioritize based on risk and effort

3. **Knowledge Sharing**
   - Share PIRs broadly within the organization
   - Update runbooks based on lessons learned
   - Conduct training sessions for common failure modes

4. **Continuous Improvement**
   - Look for patterns across multiple incidents
   - Invest in tooling and automation
   - Regularly review and update processes
