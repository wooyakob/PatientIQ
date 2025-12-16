# CKO

Format:
1. 40 min pres (demo)
2. Tech mini booth
3. Demo 

Model Service available models?

couchbase-fe tenant
cluster:
- multi node
AWS US East
- 10.0.18.0/24 CIDR
restrict public access: off
v 8.0
5 nodes
SG1 data
3 nodes
CPU 8vCPUs, 16GB
Disk 50GB
IOPS 3000
Disk GP3

SG2
2 nodes
Index, Query, Search, Eventing
8 vCPUs, 16GB
Disk 50GB
IOPS 3000
Disk GP3

Basic support plan, we'll fix it if something goes wrong...

nodes are deployed across multiple AZs to keep data highly available and protect against downtime: off, single using az1

On $2.77 per hour.

playground disabled
deletion protection enabled

add allowed IP




use cases on website:
Hyper personalized content generation
Chatbot Q&A
Enhanced enterprise search
Recommendation systems
Hybrid search
Data analysis
come up with our own, ideation phase


Plan switched from basic to dev pro because basic is unsupported (even though undocumented, not in cluster compatibility error message in UI)
Workflow test, failure limits on shared embedding model (reported, work in progress)
Vectorizing structured from S3, shared bucket but can't separate data, specifiy a file path, folder - again reported, work in progress



