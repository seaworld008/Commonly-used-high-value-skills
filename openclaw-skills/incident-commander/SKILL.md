---
name: incident-commander
description: 'Coordinate active incidents through severity assessment, roles, mitigation, communications, recovery verification, and postmortem handoff.'
zh_description: "用于事故响应中的分诊、角色分配、沟通协调、缓解跟踪和复盘。"
version: "1.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["commander", "devops", "incident", "sre"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "intermediate"
---

# Incident Commander Skill

**Category:** Engineering Team  
**Tier:** POWERFUL  
**Author:** Claude Skills Team  
**Version:** 1.0.0  
**Last Updated:** February 2026

## Overview

The Incident Commander skill provides a comprehensive incident response framework for managing technology incidents from detection through resolution and post-incident review. This skill implements battle-tested practices from SRE and DevOps teams at scale, providing structured tools for severity classification, timeline reconstruction, and thorough post-incident analysis.

## Key Features

- **Automated Severity Classification** - Intelligent incident triage based on impact and urgency metrics
- **Timeline Reconstruction** - Transform scattered logs and events into coherent incident narratives
- **Post-Incident Review Generation** - Structured PIRs with multiple RCA frameworks
- **Communication Templates** - Pre-built templates for stakeholder updates and escalations
- **Runbook Integration** - Generate actionable runbooks from incident patterns

## Skills Included

### Core Tools

1. **Incident Classifier** (`incident_classifier.py`)
   - Analyzes incident descriptions and outputs severity levels
   - Recommends response teams and initial actions
   - Generates communication templates based on severity

2. **Timeline Reconstructor** (`timeline_reconstructor.py`)
   - Processes timestamped events from multiple sources
   - Reconstructs chronological incident timeline
   - Identifies gaps and provides duration analysis

3. **PIR Generator** (`pir_generator.py`)
   - Creates comprehensive Post-Incident Review documents
   - Applies multiple RCA frameworks (5 Whys, Fishbone, Timeline)
   - Generates actionable follow-up items

## Incident Response Framework

### Severity Classification System

#### SEV1 - Critical Outage
**Definition:** Complete service failure affecting all users or critical business functions

**Characteristics:**
- Customer-facing services completely unavailable
- Data loss or corruption affecting users
- Security breaches with customer data exposure
- Revenue-generating systems down
- SLA violations with financial penalties

**Response Requirements:**
- Immediate escalation to on-call engineer
- Incident Commander assigned within 5 minutes
- Executive notification within 15 minutes
- Public status page update within 15 minutes
- War room established
- All hands on deck if needed

**Communication Frequency:** Every 15 minutes until resolution

#### SEV2 - Major Impact
**Definition:** Significant degradation affecting subset of users or non-critical functions

**Characteristics:**
- Partial service degradation (>25% of users affected)
- Performance issues causing user frustration
- Non-critical features unavailable
- Internal tools impacting productivity
- Data inconsistencies not affecting user experience

**Response Requirements:**
- On-call engineer response within 15 minutes
- Incident Commander assigned within 30 minutes
- Status page update within 30 minutes
- Stakeholder notification within 1 hour
- Regular team updates

**Communication Frequency:** Every 30 minutes during active response

#### SEV3 - Minor Impact
**Definition:** Limited impact with workarounds available

**Characteristics:**
- Single feature or component affected
- <25% of users impacted
- Workarounds available
- Performance degradation not significantly impacting UX
- Non-urgent monitoring alerts

**Response Requirements:**
- Response within 2 hours during business hours
- Next business day response acceptable outside hours
- Internal team notification
- Optional status page update

**Communication Frequency:** At key milestones only

#### SEV4 - Low Impact
**Definition:** Minimal impact, cosmetic issues, or planned maintenance

**Characteristics:**
- Cosmetic bugs
- Documentation issues
- Logging or monitoring gaps
- Performance issues with no user impact
- Development/test environment issues

**Response Requirements:**
- Response within 1-2 business days
- Standard ticket/issue tracking
- No special escalation required

**Communication Frequency:** Standard development cycle updates

### Incident Commander Role

#### Primary Responsibilities

Read [the detailed procedure and examples](EXTENDED.md#section-6) when working on this part of the task.

#### Decision-Making Framework

**Emergency Decisions (SEV1/2):**
- Incident Commander has full authority
- Bias toward action over analysis
- Document decisions for later review
- Consult subject matter experts but don't get blocked

**Resource Allocation:**
- Can pull in any necessary team members
- Authority to escalate to senior leadership
- Can approve emergency spend for external resources
- Make call on communication channels and timing

**Technical Decisions:**
- Lean on technical leads for implementation details
- Make final calls on trade-offs between speed and risk
- Approve rollback vs. fix-forward strategies
- Coordinate testing and validation approaches

### Communication Templates

#### Initial Incident Notification (SEV1/2)

Read [the detailed procedure and examples](EXTENDED.md#section-2) when working on this part of the task.

#### Executive Summary (SEV1)

Read [the detailed procedure and examples](EXTENDED.md#section-3) when working on this part of the task.

#### Customer Communication Template

Read [the detailed procedure and examples](EXTENDED.md#section-5) when working on this part of the task.

### Stakeholder Management

#### Stakeholder Classification

**Internal Stakeholders:**
- **Engineering Leadership** - Technical decisions and resource allocation
- **Product Management** - Customer impact assessment and feature implications
- **Customer Support** - User communication and support ticket management
- **Sales/Account Management** - Customer relationship management for enterprise clients
- **Executive Team** - Business impact decisions and external communication approval
- **Legal/Compliance** - Regulatory reporting and liability assessment

**External Stakeholders:**
- **Customers** - Service availability and impact communication
- **Partners** - API availability and integration impacts
- **Vendors** - Third-party service dependencies and support escalation
- **Regulators** - Compliance reporting for regulated industries
- **Public/Media** - Transparency for public-facing outages

#### Communication Cadence by Stakeholder

| Stakeholder | SEV1 | SEV2 | SEV3 | SEV4 |
|-------------|------|------|------|------|
| Engineering Leadership | Real-time | 30min | 4hrs | Daily |
| Executive Team | 15min | 1hr | EOD | Weekly |
| Customer Support | Real-time | 30min | 2hrs | As needed |
| Customers | 15min | 1hr | Optional | None |
| Partners | 30min | 2hrs | Optional | None |

### Runbook Generation Framework

#### Dynamic Runbook Components

1. **Detection Playbooks**
   - Monitoring alert definitions
   - Triage decision trees
   - Escalation trigger points
   - Initial response actions

2. **Response Playbooks**
   - Step-by-step mitigation procedures
   - Rollback instructions
   - Validation checkpoints
   - Communication checkpoints

3. **Recovery Playbooks**
   - Service restoration procedures
   - Data consistency checks
   - Performance validation
   - User notification processes

#### Runbook Template Structure

Read [the detailed procedure and examples](EXTENDED.md#section-1) when working on this part of the task.

### Post-Incident Review (PIR) Framework

#### PIR Timeline and Ownership

**Timeline:**
- **24 hours:** Initial PIR draft completed by Incident Commander
- **3 business days:** Final PIR published with all stakeholder input
- **1 week:** Action items assigned with owners and due dates
- **4 weeks:** Follow-up review on action item progress

**Roles:**
- **PIR Owner:** Incident Commander (can delegate writing but owns completion)
- **Technical Contributors:** All engineers involved in response
- **Review Committee:** Engineering leadership, affected product teams
- **Action Item Owners:** Assigned based on expertise and capacity

#### Root Cause Analysis Frameworks

#### 1. Five Whys Method

The Five Whys technique involves asking "why" repeatedly to drill down to root causes:

**Example Application:**
- **Problem:** Database became unresponsive during peak traffic
- **Why 1:** Why did the database become unresponsive? → Connection pool was exhausted
- **Why 2:** Why was the connection pool exhausted? → Application was creating more connections than usual
- **Why 3:** Why was the application creating more connections? → New feature wasn't properly connection pooling
- **Why 4:** Why wasn't the feature properly connection pooling? → Code review missed this pattern
- **Why 5:** Why did code review miss this? → No automated checks for connection pooling patterns

**Best Practices:**
- Ask "why" at least 3 times, often need 5+ iterations
- Focus on process failures, not individual blame
- Each "why" should point to a actionable system improvement
- Consider multiple root cause paths, not just one linear chain

#### 2. Fishbone (Ishikawa) Diagram

Systematic analysis across multiple categories of potential causes:

**Categories:**
- **People:** Training, experience, communication, handoffs
- **Process:** Procedures, change management, review processes
- **Technology:** Architecture, tooling, monitoring, automation
- **Environment:** Infrastructure, dependencies, external factors

**Application Method:**
1. State the problem clearly at the "head" of the fishbone
2. For each category, brainstorm potential contributing factors
3. For each factor, ask what caused that factor (sub-causes)
4. Identify the factors most likely to be root causes
5. Validate root causes with evidence from the incident

#### 3. Timeline Analysis

Reconstruct the incident chronologically to identify decision points and missed opportunities:

**Timeline Elements:**
- **Detection:** When was the issue first observable? When was it first detected?
- **Notification:** How quickly were the right people informed?
- **Response:** What actions were taken and how effective were they?
- **Communication:** When were stakeholders updated?
- **Resolution:** What finally resolved the issue?

**Analysis Questions:**
- Where were there delays and what caused them?
- What decisions would we make differently with perfect information?
- Where did communication break down?
- What automation could have detected/resolved faster?

### Escalation Paths

#### Technical Escalation

**Level 1:** On-call engineer
- **Responsibility:** Initial response and common issue resolution
- **Escalation Trigger:** Issue not resolved within SLA timeframe
- **Timeframe:** 15 minutes (SEV1), 30 minutes (SEV2)

**Level 2:** Senior engineer/Team lead
- **Responsibility:** Complex technical issues requiring deeper expertise
- **Escalation Trigger:** Level 1 requests help or timeout occurs
- **Timeframe:** 30 minutes (SEV1), 1 hour (SEV2)

**Level 3:** Engineering Manager/Staff Engineer
- **Responsibility:** Cross-team coordination and architectural decisions
- **Escalation Trigger:** Issue spans multiple systems or teams
- **Timeframe:** 45 minutes (SEV1), 2 hours (SEV2)

**Level 4:** Director of Engineering/CTO
- **Responsibility:** Resource allocation and business impact decisions
- **Escalation Trigger:** Extended outage or significant business impact
- **Timeframe:** 1 hour (SEV1), 4 hours (SEV2)

#### Business Escalation

**Customer Impact Assessment:**
- **High:** Revenue loss, SLA breaches, customer churn risk
- **Medium:** User experience degradation, support ticket volume
- **Low:** Internal tools, development impact only

**Escalation Matrix:**

| Severity | Duration | Business Escalation |
|----------|----------|-------------------|
| SEV1 | Immediate | VP Engineering |
| SEV1 | 30 minutes | CTO + Customer Success VP |
| SEV1 | 1 hour | CEO + Full Executive Team |
| SEV2 | 2 hours | VP Engineering |
| SEV2 | 4 hours | CTO |
| SEV3 | 1 business day | Engineering Manager |

### Status Page Management

#### Update Principles

1. **Transparency:** Provide factual information without speculation
2. **Timeliness:** Update within committed timeframes
3. **Clarity:** Use customer-friendly language, avoid technical jargon
4. **Completeness:** Include impact scope, status, and next update time

#### Status Categories

- **Operational:** All systems functioning normally
- **Degraded Performance:** Some users may experience slowness
- **Partial Outage:** Subset of features unavailable
- **Major Outage:** Service unavailable for most/all users
- **Under Maintenance:** Planned maintenance window

#### Update Template

```
{Timestamp} - {Status Category}

{Brief description of current state}

Impact: {who is affected and how}
Cause: {root cause if known, "under investigation" if not}
Resolution: {what's being done to fix it}

Next update: {specific time}

We apologize for any inconvenience this may cause.
```

### Action Item Framework

#### Action Item Categories

1. **Immediate Fixes**
   - Critical bugs discovered during incident
   - Security vulnerabilities exposed
   - Data integrity issues

2. **Process Improvements**
   - Communication gaps
   - Escalation procedure updates
   - Runbook additions/updates

3. **Technical Debt**
   - Architecture improvements
   - Monitoring enhancements
   - Automation opportunities

4. **Organizational Changes**
   - Team structure adjustments
   - Training requirements
   - Tool/platform investments

#### Action Item Template

Read [the detailed procedure and examples](EXTENDED.md#section-4) when working on this part of the task.

## Usage Examples

### Example 1: Database Connection Pool Exhaustion

```bash
# Classify the incident
echo '{"description": "Users reporting 500 errors, database connections timing out", "affected_users": "80%", "business_impact": "high"}' | python scripts/incident_classifier.py

# Reconstruct timeline from logs
python scripts/timeline_reconstructor.py --input assets/db_incident_events.json --output timeline.md

# Generate PIR after resolution
python scripts/pir_generator.py --incident assets/db_incident_data.json --timeline timeline.md --output pir.md
```

### Example 2: API Rate Limiting Incident

```bash
# Quick classification from stdin
echo "API rate limits causing customer API calls to fail" | python scripts/incident_classifier.py --format text

# Build timeline from multiple sources
python scripts/timeline_reconstructor.py --input assets/api_incident_logs.json --detect-phases --gap-analysis

# Generate comprehensive PIR
python scripts/pir_generator.py --incident assets/api_incident_summary.json --rca-method fishbone --action-items
```

## Best Practices

### During Incident Response

1. **Maintain Calm Leadership**
   - Stay composed under pressure
   - Make decisive calls with incomplete information
   - Communicate confidence while acknowledging uncertainty

2. **Document Everything**
   - All actions taken and their outcomes
   - Decision rationale, especially for controversial calls
   - Timeline of events as they happen

3. **Effective Communication**
   - Use clear, jargon-free language
   - Provide regular updates even when there's no new information
   - Manage stakeholder expectations proactively

4. **Technical Excellence**
   - Prefer rollbacks to risky fixes under pressure
   - Validate fixes before declaring resolution
   - Plan for secondary failures and cascading effects

### Post-Incident

Read [the detailed procedure and examples](EXTENDED.md#section-7) when working on this part of the task.

## Integration with Existing Tools

### Monitoring and Alerting
- PagerDuty/Opsgenie integration for escalation
- Datadog/Grafana for metrics and dashboards
- ELK/Splunk for log analysis and correlation

### Communication Platforms
- Slack/Teams for war room coordination
- Zoom/Meet for video bridges
- Status page providers (Statuspage.io, etc.)

### Documentation Systems
- Confluence/Notion for PIR storage
- GitHub/GitLab for runbook version control
- JIRA/Linear for action item tracking

### Change Management
- CI/CD pipeline integration
- Deployment tracking systems
- Feature flag platforms for quick rollbacks

## Conclusion

The Incident Commander skill provides a comprehensive framework for managing incidents from detection through post-incident review. By implementing structured processes, clear communication templates, and thorough analysis tools, teams can improve their incident response capabilities and build more resilient systems.

The key to successful incident management is preparation, practice, and continuous learning. Use this framework as a starting point, but adapt it to your organization's specific needs, culture, and technical environment.

Remember: The goal isn't to prevent all incidents (which is impossible), but to detect them quickly, respond effectively, communicate clearly, and learn continuously.
