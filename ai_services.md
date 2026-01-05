Doc for what is available from Adam Clevy: https://docs.google.com/document/d/1rONaLuQQc4ik3zZ4VQsSFkNfgqHGP7UVwAaqlLI2TMw/edit?tab=t.0
Solutions Engineers have restricted access, cloud architecture team is in control.

# Using S3 as a source of data. 
Have noted limitations e.g. 
"I'd also add that for vectorizing structured data from S3, if we're not able to specify a folder/bucket and all SEs are using this one bucket then it'll vectorize all JSON (if specified) uploaded here. Not sure how we'd separate the data we're using without being able to specify a folder/file path."
Can vectorize but it will vectorize all data. 
Do not use for now.

# AI Functions
Mask sensitive data - patient, doctor notes (name of patient).
Sentiment analysis - general sentiment of patient from their notes.
Summarize research for medical research summary.
Classify content, Extract entities - pulling out condition "cancer", december - date.
Correct grammar, spelling for doctor, patient notes - avoid doctor's handwriting scrawl, untidy notes.

Can use OpenAI model or Bedrock model, nova.
Neither work currently as not able to detect an operational cluster.
Have to raise this issue too, perhaps it is meant to be this way as testing has stopped.

# Workflows

S3
structured (JSON)
unstructured 
to vectorize, neither work due to S3 bucket restrictions.

data from capella
research papers stored in Capella
testing workflow
using predeployed embedding model
nvidia/llama-3.2-nv-embedqa-1b-v2
129 documents


# Models
Not able to deploy models.
We have an embedding model available.
No LLM is available, may be able to use Bedrock.
But will require API, not in same VPC.

# Agent Catalog
Agentc initialized in this project.
Tools are stored and versioned in Tools Hub.
Prompts are stored and versioned in Prompt Hub.
No traces in Agent Tracer as agent not in use yet. Still have to test traces.

# Private Endpoints
Between capella and AWS model for example.

Private endpoint secures traffic between a virtual private cloud (VPC) and AWS services
Not able to update this, insufficient permissions.
