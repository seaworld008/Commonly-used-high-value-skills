# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

### Customer Interview Analyzer Example

**Input (interview.txt):**
```
Customer: Jane, Enterprise PM at TechCorp
Date: 2024-01-15

Interviewer: What's the hardest part of your current workflow?

Jane: The biggest frustration is the lack of real-time collaboration.
When I'm working on a PRD, I have to constantly ping my team on Slack
to get updates. It's really frustrating to wait for responses,
especially when we're on a tight deadline.

I've tried using Google Docs for collaboration, but it doesn't
integrate with our roadmap tools. I'd pay extra for something that
just worked seamlessly.

Interviewer: How often does this happen?

Jane: Literally every day. I probably waste 30 minutes just on
back-and-forth messages. It's my biggest pain point right now.
```

**Command:**
```bash
python scripts/customer_interview_analyzer.py interview.txt
```

**Output:**
```
============================================================
CUSTOMER INTERVIEW ANALYSIS
============================================================

📋 INTERVIEW METADATA
Segments found: 1
Lines analyzed: 15

😟 PAIN POINTS (3 found)

1. [HIGH] Lack of real-time collaboration
   "I have to constantly ping my team on Slack to get updates"

2. [MEDIUM] Tool integration gaps
   "Google Docs...doesn't integrate with our roadmap tools"

3. [HIGH] Time wasted on communication
   "waste 30 minutes just on back-and-forth messages"

💡 FEATURE REQUESTS (2 found)

1. Real-time collaboration - Priority: High
2. Seamless tool integration - Priority: Medium

🎯 JOBS TO BE DONE

When working on PRDs with tight deadlines
I want real-time visibility into team updates
So I can avoid wasted time on status checks

📊 SENTIMENT ANALYSIS

Overall: Negative (pain-focused interview)
Key emotions: Frustration, Time pressure

💬 KEY QUOTES

• "It's really frustrating to wait for responses"
• "I'd pay extra for something that just worked seamlessly"
• "It's my biggest pain point right now"

🏷️ THEMES

- Collaboration friction
- Tool fragmentation
- Time efficiency
```

---
