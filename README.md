# PatientIQ - Agentic Patient 360
## Team Name: Latent Potential
## App Name: PatientIQ

## One Liner
PatientIQ centralizes patient data and minimizes a doctor's cognitive load by making intelligent micro decisions, freeing up more space for the life saving ones made by the experts.

## Abstract
Doctors today face countless daily micro decisions, many of which are administrative and pull focus away from life saving care. PatientIQ centralizes key patient information and uses AI agents to handle routine information retrieval, giving clinicians more time to focus on analysis and delivery of patient care.

## Run
- `make dev`
- `make stop`

## Code Formatting
- Install hooks:
  - `make install-hooks`

## Agentc
See: `/agents/AGENTS.md`

 ### Cluster Configuration
 Cluster used for testing (high level):
 - AWS US East
 - Couchbase Server `8.0`
 - 5 nodes total
 - Data service group: 3 nodes
 - Index/Query/Search/Eventing group: 2 nodes
 - MultiAZ required for AI Functions to work
 - Private Networking Enabled for Workflows, Embedding Model to Work

### Database Schema
Configured via environment variables:
- `COUCHBASE_BUCKET` (defaults to `Scripps`)
- `COUCHBASE_RESEARCH_BUCKET` (defaults to `Research`)

#### Research (bucket)
- **Pubmed** (scope)
  - `Pulmonary` (collection)
  - `questions` (collection)
  - `answers` (collection)

#### Scripps (bucket)
- **Notes** (scope)
  - `Doctor` (collection)
  - `Patient` (collection)
- **People** (scope)
  - `Doctors` (collection)
  - `Patients` (collection)
- **Wearables** (scope)
  - `Patient_1` (collection)
  - `Patient_2` (collection)
  - `Patient_3` (collection)
  - `Patient_4` (collection)
  - `Patient_5` (collection)
- **Questionnaires** (scope)
  - `Patient_1` (collection)
  - `Patient_2` (collection)
  - `Patient_3` (collection)
  - `Patient_4` (collection)
  - `Patient_5` (collection)
- **Messages** (scope)
  - `Private` (collection)
  - `Public` (collection)
- **Calendar** (scope)
  - `Appointments` (collection)


 ## Cluster Cost Estimate
 **Window**

 - **Feb 8–12**
 - **Feb 12:** cluster destroyed
 
 **Assumptions used in this estimate**
 
 - **Weekdays (Mon–Fri):** 9am–noon (3 hours/day)
 - **Weekend:** Sat/Sun off
 - **Rate (on):** 2.77
 - **Rate (off):** 0.16
 
 **Weekly estimate**
 
 | Category | Calculation | Weekly hours | Cost |
 | --- | --- | ---: | ---: |
 | On time | 3 hours/day × 5 days | 15 | $41.55 |
 | Off time | (21 hours × 5 days) + (24 hours × 2 days) | 153 | $24.48 |
 | **Total** |  |  | **$66.03** |
 
 **Projected total (3–4 weeks):** $198.09