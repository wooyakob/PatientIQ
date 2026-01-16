Had to rerun workflow to ensure Hyperscale indexed documents.

DROP INDEX `hyperscale_pubmed_vectorized_article_text_vectorized` ON `Research`.`Pubmed`.`Pulmonary`;

https://docs.couchbase.com/cloud/vector-index/hyperscale-vector-index.html

CREATE VECTOR INDEX `<index_name>`
       ON `<collection>`(`<key_name>` VECTOR)
       WITH {"dimension": <dimensions>,
             "similarity": <similarity_metric>,
             "description": <centroids_and_quantization>
        };

CREATE VECTOR INDEX `hyperscale_pubmed_vectorized_article_text_vectorized` ON `Research`.`Pubmed`.`Pulmonary`(`article_text_vectorized` VECTOR) WITH {   "nodes":[ "svc-qisea-node-006.kfe63sbh2c511uyt.cloud.couchbase.com:18091","svc-qisea-node-007.kfe63sbh2c511uyt.cloud.couchbase.com:18091" ], "num_replica":1, "dimension":2048, "similarity":"L2", "description":"IVF,SQ8" }

Similarity algorithm that can be changed is L2. Uses L2 Squared by default.

https://docs.couchbase.com/cloud/vector-index/vectors-and-indexes-overview.html#euclidean-squared

Euclidean Squared Distance Formula
𝐿22(𝑥,𝑦)=∑𝑛𝑖=1(𝑥𝑖−𝑦𝑖)2

See CREATE VECTOR INDEX docs for specifying a similarity algorithm: https://docs.couchbase.com/cloud/n1ql/n1ql-language-reference/createvectorindex.html


