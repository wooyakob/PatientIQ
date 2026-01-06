# Agentic Healthcare Application

## Mission
Doctors do not have time to make every single decision, especially the small, non-critical decisions. Agents can handle many of these micro decisions for them, intelligently, to ensure that doctors have the information they need to be at their best and make life-saving decisions without burning out.

## System Overview
This application uses four specialized AI agents powered by LangGraph and agentc (Agent Catalog) to provide intelligent, automated support for healthcare professionals. Each agent has specific responsibilities and outputs structured data to the Couchbase Capella database.

---

## Agent 1: Wearable Data Monitoring and Alerting Agent

### Purpose
Continuously monitor patient wearable device data (heart rate, step count) and proactively alert physicians when concerning patterns emerge that may require medical attention.

### Responsibilities
1. **Data Analysis**
   - Analyze 7-day trends in heart rate and step count data
   - Calculate statistical metrics (average, min, max, standard deviation)
   - Compare current readings against patient baseline and age-appropriate norms
   - Identify sudden changes, anomalies, or concerning trends

2. **Clinical Context**
   - Consider patient's medical condition (e.g., cancer, diabetes, hypertension, anxiety)
   - Factor in patient age and gender
   - Account for expected variations based on diagnosis
   - Understand medication effects on vital signs

3. **Alert Generation**
   - Generate alerts ONLY when medical attention is warranted
   - Assign severity levels:
     - **Critical**: Requires immediate attention (e.g., heart rate >130 sustained, <50 sustained)
     - **High**: Should be reviewed within 24 hours
     - **Medium**: Review at next appointment
     - **Low**: For information/trending only
   - Include specific metrics that triggered the alert
   - Provide clear, actionable message for the physician

4. **Pattern Recognition**
   - Detect declining activity trends (e.g., steps decreasing over days)
   - Identify irregular heart rate patterns
   - Flag sudden changes from baseline

### Input
- `patient_id`: Patient identifier
- `patient_data`: Object containing:
  - Demographics (name, age, gender)
  - Medical condition
  - `wearable_data`:
    - `heart_rate`: Array of readings (bpm)
    - `step_count`: Array of readings (steps)

### Output
Alert object (if needed):
```json
{
  "id": "uuid",
  "patient_id": "1",
  "alert_type": "Elevated Heart Rate Trend",
  "severity": "high",
  "message": "Patient shows sustained elevated heart rate (avg 92 bpm) over 7 days, 15% above baseline. Given anxiety disorder diagnosis, may indicate increased stress or medication adjustment needed.",
  "metrics": {
    "heart_rate": [85, 92, 78, 88, 82, 90, 86],
    "step_count": [6200, 7500, 5800, 8100, 6900, 7200, 6500]
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

### Guidelines
- **Be Conservative**: Only alert when truly necessary to avoid alert fatigue
- **Be Specific**: Always cite exact numbers and trends
- **Be Contextual**: Consider the patient's condition in your assessment
- **Be Actionable**: Give physicians clear next steps

---

## Agent 2: Medical Research and Summarization Agent

### Purpose
Automatically generate concise, evidence-based medical research summaries relevant to each patient's condition, providing physicians with the latest clinical insights without requiring manual research.

### Responsibilities
1. **Research Topic Identification**
   - Analyze patient's primary condition
   - Identify the most clinically relevant research area
   - Focus on actionable treatment advances and best practices
   - Generate a concise topic title (max 10 words)

2. **Summary Generation**
   - Create exactly 3 research summaries per patient
   - Each summary should be 2-3 sentences
   - Focus on research from the last 2-3 years
   - Prioritize Level 1 evidence (RCTs, meta-analyses, systematic reviews)
   - Include specific outcomes or statistics when relevant

3. **Clinical Relevance**
   - Cover different aspects of the condition:
     - Treatment advances/new therapies
     - Clinical trial results
     - Best practices for management
   - Make summaries actionable for clinical decision-making
   - Use physician-appropriate language (clinical, not patient-facing)

4. **Content Quality**
   - Be factual and evidence-based
   - Avoid speculation or unproven treatments
   - Cite specific interventions or approaches
   - Mention key outcomes (e.g., "reduced hospitalizations by 30%")

### Input
- `patient_id`: Patient identifier
- `patient_data`: Object containing:
  - Patient name
  - Age
  - Primary medical condition
  - Current treatment status (if available)

### Output
Research summary object:
```json
{
  "patient_id": "1",
  "condition": "Breast Cancer Stage II",
  "research_topic": "HER2-Positive Breast Cancer: Recent Treatment Advances",
  "summaries": [
    "The DESTINY-Breast03 trial demonstrated that trastuzumab deruxtecan significantly improved progression-free survival compared to trastuzumab emtansine in HER2-positive metastatic breast cancer, with a 72% reduction in disease progression risk. This antibody-drug conjugate is now considered a preferred second-line option.",
    "Neoadjuvant therapy combining pertuzumab, trastuzumab, and chemotherapy achieves pathologic complete response in 60% of HER2-positive early breast cancer patients, correlating with improved long-term survival. This approach allows for potential de-escalation of surgery.",
    "Genomic profiling with Oncotype DX in HER2-positive disease helps identify patients who may safely omit chemotherapy when hormone receptor-positive, reducing overtreatment while maintaining excellent outcomes in low-risk cases."
  ],
  "sources": [],
  "generated_at": "2024-01-20T10:30:00Z"
}
```

### Guidelines
- **Be Current**: Focus on 2022-2024 research
- **Be Specific**: Include drug names, trial names, specific percentages
- **Be Diverse**: Cover different aspects (treatment, monitoring, lifestyle)
- **Be Concise**: 2-3 sentences per summary, no more
- **Be Practical**: Information should be usable in clinical practice

---

## Agent 3: Message Board Routing Agent

### Purpose
Intelligently analyze facility-wide announcements and automatically route relevant information to specific staff members based on their roles, specialties, and the content's relevance, ensuring critical information reaches the right people without overwhelming everyone.

### Responsibilities
1. **Message Analysis**
   - Read and understand announcement content
   - Identify key topics, urgency, and scope
   - Determine who needs this information
   - Assess priority level

2. **Relevance Matching**
   - Match announcement content to staff roles and specialties
   - Consider department relevance
   - Identify individuals directly affected
   - Avoid unnecessary routing (reduce noise)

3. **Priority Assessment**
   - **Urgent**: Immediate action required (safety issues, critical updates)
   - **High**: Important, time-sensitive information
   - **Medium**: Relevant information, non-urgent
   - **Low**: FYI, general awareness

4. **Routing Decision**
   - List specific recipients by name/ID
   - Provide reasoning for each routing decision
   - Determine if broadcast is sufficient or if private routing needed
   - Minimize alert fatigue by being selective

### Input
- `announcement`: The message text
- `staff_directory`: Array of staff objects:
  ```json
  [
    {
      "name": "Dr. Sarah Johnson",
      "role": "Oncologist",
      "specialties": ["Breast Cancer", "Lung Cancer"],
      "department": "Oncology"
    }
  ]
  ```

### Output
Routing response object:
```json
{
  "announcement": "New chemotherapy protocol for breast cancer patients effective immediately...",
  "routes": [
    {
      "id": "uuid",
      "original_message": "New chemotherapy protocol for breast cancer patients effective immediately...",
      "routing_needed": true,
      "priority": "high",
      "recipients": [
        {
          "name": "Dr. Sarah Johnson",
          "reason": "Oncologist specializing in breast cancer treatment"
        },
        {
          "name": "Nurse Emma Williams",
          "reason": "Oncology department nurse administering chemotherapy"
        }
      ],
      "timestamp": "2024-01-20T10:30:00Z"
    }
  ],
  "recipients": [
    {
      "name": "Dr. Sarah Johnson",
      "reason": "Oncologist specializing in breast cancer treatment"
    }
  ],
  "priority": "high"
}
```

### Guidelines
- **Be Selective**: Only route when truly relevant to avoid information overload
- **Be Specific**: Clearly explain why each person should receive the message
- **Be Timely**: Assign appropriate priority based on urgency
- **Be Logical**: Consider workflow and responsibilities in routing decisions

---

## Agent 4: Medical Questionnaire Summarization and Intelligent Timely Delivery Agent

### Purpose
Automatically summarize patient-completed questionnaires before appointments, extracting key clinical information and highlighting concerns, enabling physicians to prepare efficiently and conduct more focused appointments.

### Responsibilities
1. **Questionnaire Analysis**
   - Review all patient responses
   - Identify clinically significant information
   - Detect changes from previous responses (if available)

2. **Summary Creation**
   - Write a concise 3-4 sentence clinical summary
   - Use physician-appropriate medical terminology
   - Focus on information affecting clinical decisions
   - Highlight symptom changes, new concerns, medication issues

3. **Key Points Extraction**
   - Identify 3-5 most important points
   - Prioritize actionable items
   - Note urgent concerns first
   - Include relevant patient-reported outcomes

### Input
- `patient_id`: Patient identifier
- `patient_data`: Patient demographics and condition
- `questionnaire_responses`: Object with Q&A pairs:
  ```json
  {
    "How has your pain level been this week (1-10)?": "7, worse than last month",
    "Are you experiencing any new symptoms?": "Yes, increased fatigue and nausea",
    "How many doses of medication did you miss?": "2-3 per week",
    "Any concerns you'd like to discuss?": "Worried about side effects"
  }
  ```
- `appointment_date`: Scheduled appointment

### Output
Questionnaire summary object:
```json
{
  "patient_id": "1",
  "appointment_date": "2024-02-01",
  "summary": "Patient reports increased pain (7/10, up from previous 5/10) with new onset fatigue and nausea. Medication adherence suboptimal at 2-3 missed doses weekly. Patient expresses concern about side effects, suggesting need for medication review or alternative options.",
  "key_points": [
    "Pain escalation: 7/10 (previous 5/10)",
    "New symptoms: Fatigue and nausea",
    "Poor medication adherence: 2-3 missed doses/week",
    "Patient concerned about side effects",
    "Requires medication effectiveness review"
  ],
  "generated_at": "2024-01-25T10:30:00Z"
}
```

### Guidelines
- **Be Thorough**: Don't miss important details
- **Be Concise**: Busy physicians need scannable summaries
- **Be Clinical**: Use appropriate medical language
- **Be Alert**: Flag anything requiring immediate attention
- **Be Structured**: Organize information logically
- **Be Actionable**: Help physician prepare specific discussion points

---

## Technical Implementation Notes

### Database Schema (Couchbase Capella)

All agent outputs are stored as JSON documents in Couchbase:

- **Patients**: bucket `ckodb`, scope `People`, collection `Patient` (document ID: `patient_id`)
- **Doctor notes**: bucket `ckodb`, scope `Notes`, collection `Doctor`
- **Patient notes**: bucket `ckodb`, scope `Notes`, collection `Patient`
- **Wearable alerts**: bucket `ckodb`, scope `Wearables`, collection `Watch`
- **Research summaries**: bucket `ckodb`, scope `Research`, collection `pubmed`

Current temporary storage locations:

- Message routing records are saved to `ckodb`.`Notes`.`Doctor`.
- Questionnaire summaries are saved to `ckodb`.`Notes`.`Doctor` with `document_type="questionnaire_summary"` until a dedicated `Questionnaires` scope/collection is finalized.

### Agent Integration

Agents use:
- **LangGraph**: State management and workflow orchestration
- **agentc (Agent Catalog)**: Prompt and tool versioning
- **OpenAI GPT-4**: Language model for analysis
- **Couchbase SDK**: Database operations

### Prompts and Tools

- Prompts stored in: `prompts/{agent_name}.yaml`
- Tools stored in: `tools/{category}_tools.py`
- Version controlled via Git + agentc hooks

### API Endpoints

Agents triggered via FastAPI:
- `POST /api/agents/wearable-monitor/run`
- `POST /api/agents/research-summarizer/run`
- `POST /api/agents/message-router/run`
- `POST /api/agents/questionnaire-summarizer/run`
- `POST /api/agents/run-all` (runs all applicable agents)

---

## Quality Standards

All agents must:
1. Provide factual, evidence-based information
2. Use appropriate medical terminology
3. Consider clinical context (patient condition, age, medications)
4. Be concise and scannable
5. Include specific metrics and details
6. Avoid unnecessary alerts (reduce fatigue)
7. Output structured JSON for database storage
8. Handle errors gracefully
9. Log decisions for transparency
10. Prioritize patient safety

