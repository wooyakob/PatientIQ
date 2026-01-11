# Run in BiqQuery against free PubMed Dataset to return relevant medical research papers focused on Pulmonary conditions.
SELECT author, title, article_text, article_citation, pmc_link 
FROM `bigquery-public-data.pmc_open_access_commercial.articles` 
WHERE 
  REGEXP_CONTAINS(LOWER(IFNULL(title, '')),
    r'asthma|copd|chronic obstructive pulmonary|emphysema|pneumonia|influenza|pulmonary fibrosis|sarcoidosis|pulmonary hypertension|respiratory|pulmonary')
LIMIT 1000;