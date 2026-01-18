# PatientIQ Agents
Agents make micro decisions on admin tasks and take actions to complete them. Results are displayed in the PatientIQ dashboard for a doctor to use.

## pulmonary_research_agent
This Agent fetches a Patient's condition e.g. Asthma, and searches Pulmonary research related to that condition. It then summarizes the research and provides initial recommendation to the Doctor, who can then ask follow up questions of the entire Pulmonary research base.

## docnotes_search_agent
This Agent searches through notes taken by a doctor during and after visits with patients. A doctor can ask questions to jog their memory and remind themselves about previous visits with patients to ensure important information is not lost and can be reused to make informed decisions based on a patient's visit history and items discussed.

## message_routing_agent
This Agent can view public messages and announcements and nudge a doctor to read when it's important and related to them. The Agent can also respond to private messages when a doctor is unavailable, providing a contact or method to reach them in an emergency.

## wearable_alerting_agent
This Agent will review a Patient's 30 day wearable data and alert the Doctor if there are any concerning trends or patterns. 

## previsit_summarizer_agent
This Agent will review a Patient's previsit Questionnaire answers and allow a Doctor to generate a quick summary before an upcoming Appointment with their Patient.

### Agentc
agentc init
agentc status
agentc index tools prompts (optional logs, if there are issues with tracing)
agentc publish --bucket agent-catalog
agentc clean (can clean logs locally, and in Capella)

#### Vector Search Tools
- **Couchbase AI Services**: Embedding model with 2048-dimensional vectors
- **Hyperscale Vector Indexes**:
  - `hyperscale_pubmed_vectorized_article_vectorized` (Research)
  - `hyperscale_doctor_notes_vectorized_all_notes_vectorized` (Notes)

#### Agent Tracer

Agent Tracer is used for troubleshooting Agents:
- Agent acts unpredictably. Check the exact prompts sent to your agent and the generated thinking from your LLM during a user session.	
- Wrong tool called. Check the tools the agent called and troubleshoot, whether it’s similar names or overlapping and confusing descriptions.	
- Inter-agent coordination failure. Inspect the context handed off between agents - find withheld information or reasoning-action mismatches.	
- Tool schema mismatch. Compare the tool inputs provided to your agent’s LLM with your expected schema.	
- Agent stuck in a loop. Check whether the same tool or a set of tools are called in a loop, and check the agent’s reasoning log.

A single span could be:
* A tool execution
* A Large Language Model (LLM) call
* A document retrieval

When defining spans in your app, you start with a root span, that contains the entire application. The name of your root span also sets the name of your application in Agent Tracer

Define child spans from your root span to change what information gets logged at each step of your app

### Links:
- [https://docs.couchbase.com/ai/build/integrate-agent-with-catalog.html](https://docs.couchbase.com/ai/build/integrate-agent-with-catalog.html)
- [https://docs.couchbase.com/ai/build/tools-prompts-hub.html](https://docs.couchbase.com/ai/build/tools-prompts-hub.html)
- [https://couchbaselabs.github.io/agent-catalog/](https://couchbaselabs.github.io/agent-catalog/)
- [https://github.com/couchbaselabs/agent-catalog](https://github.com/couchbaselabs/agent-catalog)
- [https://github.com/couchbaselabs/agent-catalog/tree/master/examples/with_langgraph](https://github.com/couchbaselabs/agent-catalog/tree/master/examples/with_langgraph)
- [https://github.com/couchbaselabs/agent-catalog/tree/master/examples/with_fastapi](https://github.com/couchbaselabs/agent-catalog/tree/master/examples/with_fastapi)
- [https://docs.couchbase.com/ai/build/agent-tracer/add-spans-callbacks.html](https://docs.couchbase.com/ai/build/agent-tracer/add-spans-callbacks.html)
- [https://docs.couchbase.com/ai/build/agent-tracer/add-spans-callbacks.html#tool-results](https://docs.couchbase.com/ai/build/agent-tracer/add-spans-callbacks.html#tool-results)
- [https://docs.couchbase.com/ai/api-guide/api-use.html](https://docs.couchbase.com/ai/api-guide/api-use.html)
- [https://docs.couchbase.com/ai/model-service-api-reference/rest-api.html](https://docs.couchbase.com/ai/model-service-api-reference/rest-api.html)