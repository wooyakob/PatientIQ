
data sources:
example,
SELECT article_text, author, title, article_citation FROM `bigquery-public-data.pmc_open_access_commercial.articles` LIMIT 1000
Only able to save 145 of 1,000 rows.

pubmed central
"PubMed Central (PMC) is a free full-text archive of biomedical and life sciences journal literature at the U.S. National Institutes of Health's National Library of Medicine (NIH NLM). This dataset contains open access articles available under Creative Commons. The collection includes article metadata, full text content, author information, publication dates, journal details, and licensing information."

from Somya,
study with real wearable data of about 22 asthma patients: https://datashare.ed.ac.uk/handle/10283/4761
study on wearable data usefulness: https://pmc.ncbi.nlm.nih.gov/articles/PMC12387376/
wearable data: https://www.kaggle.com/datasets/manideepreddy966/wearables-dataset 

Keith,
we start with one category, then figure out how to relate the data we have on patients, to that specific category and it's respective illnesses

figure out focus for the dataset
e.g. respirtory conditions
Condition: Asthma... 

Fill category...
Next category: Cardiovascular diseases

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
phone


watch



