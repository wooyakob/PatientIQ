To start, we are focusing on Patients with Pulmonary/Respiratory conditions.

This includes:
- Asthma
- COPD (Chronic Obstructive Pulmonary Disease)
- Emphysema
- Pneumonia
- Influenza
- Pulmonary Fibrosis
- Sarcoidosis
- Pulmonary Hypertension

Data Sources:

Medical Research Papers:
- Will use a free public BigQuery dataset to export JSON of relevant Pulmonary research papers.
- PubMed Central. See research-papers/pulmonary-research.sql. Can export 10MBs, 197 rows from BQ free. Around 200 relevant research papers.

Bucket: Research
Scope: Pubmed
Collection: Pulmonary

Schema:
author
title
article_text
article_citation
pmc_link 

Workflow: pulmonary_research_papers
Hyperscale Index: hyperscale_pubmed_papers_article_text_vectorized
Can vectorize rich semantic content contained in: article_text.
vectorized_article






Patients:
To keep data manageable, we'll create comprehensive data profiles for 5 patients.
All 5 patients will have Pulmonary disorders to demonstrate the value of combining wearable, research and patient data in a single 360.

Activity Environment Data, Personal Health Data: https://www.kaggle.com/datasets/manideepreddy966/wearables-dataset


Healthcare Dataset used for Patient Data: https://www.kaggle.com/datasets/prasad22/healthcare-dataset 

Tool for free CSV To JSON conversion: https://jam.dev/utilities/csv-to-json





Wearables:
- Personal Health and Activity Environment Data: https://www.kaggle.com/datasets/manideepreddy966/wearables-dataset
Personal Health used to create Patients, conditions adapted to Pulmonary.
Activity Environment used to simulate Watch data from a Wearable.

Wearable data is more numeric and does not need to be Vectorized. Used in conjunction with research papers that offer richer semantic content. Perhaps a composite index, filter with numeric metrics, then perform vector search of the research.













bucket
scripps
scope
people
collection
doctor
patient


scope
wearables
patient_1

scope
notes
patient 
doctor

docnotes
allnotes_vectorized


data sources:
example,
SELECT article_text, author, title, article_citation FROM `bigquery-public-data.pmc_open_access_commercial.articles` LIMIT 1000
Only able to save 145 of 1,000 rows.

pubmed central
"PubMed Central (PMC) is a free full-text archive of biomedical and life sciences journal literature at the U.S. National Institutes of Health's National Library of Medicine (NIH NLM). This dataset contains open access articles available under Creative Commons. The collection includes article metadata, full text content, author information, publication dates, journal details, and licensing information."

from Somya,
study with real wearable data of about 22 asthma patients: https://datashare.ed.ac.uk/handle/10283/4761
study on wearable data usefulness: https://pmc.ncbi.nlm.nih.gov/articles/PMC12387376/






doctor notes:
doctor_id
patient_id
doctor_name
patient_name
visit_date
notes_text [this will be vectorized]


patient notes (this will use AI functions to remove personal info and perform sentiment analysis using a Couchbase Capella function):
patient_id
patient_name
visit_date
assigned_doctor (their doctor on insurance)
visit_doctor (doctor they saw during visit)

people

doctor:
doctor_name
doctor_id
doctor_specialty
doctor_hospital
doctor_licence_number

patient:
patient_name
patient_id
patient_age
patient_gender
patient_height
patient_weight
patient_bmi
patient_blood_type
patient_allergies
patient_medication
patient_illnesses

research
pubmed



wearable data
per day
last 30 days






watch

phone


there will be one doctor for now (our user)
all five patients belong to this doctor



Data models confirmed with Somya.
New data may be created or vectorized on the frontend e.g. a search query, vectorized in same dims as embedded data in Capella.


pubmed_papers_small.json
Count: 10 papers
Size: 18,271 bytes (~18 KB)