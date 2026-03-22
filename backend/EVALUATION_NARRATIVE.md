# Model Evaluation Narrative

## Research Question

For an aviation safety search engine, would domain-specific models (trained on aviation data) outperform general-purpose embedding models? This evaluation aimed to answer that question systematically.

## Model Selection Strategy

We evaluated **16 embedding models** across multiple categories to ensure comprehensive coverage:

### 1. Aviation-Specific Model
- **SafeAeroBERT** (NASA-AIML/MIKA_SafeAeroBERT): Pre-trained on ASRS and NTSB aviation incident reports
- **Hypothesis**: Domain-specific training should yield superior understanding of aviation terminology and contexts

### 2. General-Purpose Transformer Models
- **BERT-base-cased, RoBERTa-base, RoBERTa-large**: Foundational models with proven track records
- **Rationale**: Establish baselines and test if case sensitivity helps with aviation acronyms (ATC, TCAS, IFR)

### 3. Sentence Embedding Models
- **E5-base, E5-large**: Microsoft's multilingual embedding models
- **MPNet-base-v2**: Popular sentence-transformers model, known for strong performance
- **Rationale**: Optimized specifically for semantic similarity tasks

### 4. State-of-the-Art Retrieval Models (2024-2026)
- **BGE-large/base** (BAAI): Top performers on MTEB leaderboard
- **GTE-large/base** (Google): Trained specifically for retrieval tasks
- **UAE-Large-V1**: Universal Angle Embeddings with novel architecture
- **Rationale**: Test if latest research advances translate to aviation domain

### 5. Efficient/Fast Models
- **MiniLM-L12-v2, MiniLM-L6-v2**: Smaller models (384-dim) for faster inference
- **Rationale**: Evaluate performance vs. efficiency trade-offs

### 6. Instruction-Based Models
- **Instructor-XL, Instructor-large**: Models that can be guided with task-specific instructions
- **Rationale**: Test if instruction-tuning helps with specialized domains

## Evaluation Methodology

### Dataset
- **Query Source**: Ronald's synthetic queries (rnapberkeley/asrs dataset)
- **Validation Queries**: 200 aviation-specific queries from 7,158 total
- **Document Corpus**: 162 ASRS aviation incident reports
- **Ground Truth**: Each query has 1 known relevant document (seed_doc_id)

### Evaluation Setup
This represents a **single-relevant-document retrieval task**: given a query, can the model rank the correct ASRS report highly among 162 candidates?

### Metrics
1. **Recall@10**: Percentage of queries where the relevant document appears in top 10 results
   - Critical for user experience (first page of results)

2. **Recall@100**: Percentage of queries where the relevant document appears in top 100 results
   - **Primary metric**: Balances precision and recall for safety-critical search

3. **Recall@1000**: Percentage of queries where the relevant document is found anywhere
   - All models achieved 81% (limited to 162 documents)
   - Shows 19% of queries lack the relevant document in the corpus

4. **MRR (Mean Reciprocal Rank)**: Average of 1/rank for first relevant result
   - Measures how highly the relevant document is ranked
   - Higher values = better ranking quality

## Key Findings

### Finding 1: General-Purpose Models Outperformed Aviation-Specific Model

**Winner: BERT-base-cased (54% Recall@100)**
- Despite no aviation-specific training, achieved best overall performance
- **Case sensitivity advantage**: Preserves aviation acronyms (ATC, TCAS, IFR) correctly

**SafeAeroBERT Performance: #12 out of 16 (47% Recall@100)**
- Underperformed despite being pre-trained on ASRS/NTSB data
- Possible reasons:
  - Smaller training corpus vs. general models' massive pre-training
  - Uncased tokenization loses acronym information
  - Synthetic queries may differ from real incident report queries
  - General models' broader knowledge may help with implicit context

### Finding 2: Simple, Established Models Beat State-of-the-Art

**Top 3: BERT-base-cased (54%), MPNet-base-v2 (53%), RoBERTa-base (51%)**
- All are older, well-established models
- Newer SOTA models (BGE, GTE, UAE) ranked lower (#5-11)

**Implications**:
- Domain fit matters more than model novelty
- Well-tuned baselines are competitive
- Synthetic query evaluation may not capture full model capabilities

### Finding 3: Recall@10 vs. Recall@100 Trade-offs

**E5-base**: Best Recall@10 (9%) but moderate Recall@100 (48.5%)
- Ranks relevant documents very high when found
- May miss some relevant documents entirely

**BERT-base-cased**: Moderate Recall@10 (5.5%) but best Recall@100 (54%)
- Finds more relevant documents overall
- Ranks them slightly lower on average

**For safety-critical search**: Recall@100 is more important (can't afford to miss incidents)

### Finding 4: MRR Shows Ranking Quality Differences

**Best MRR: UAE-Large-V1 (0.0599)**
- When it finds relevant documents, ranks them highest
- But lower Recall@100 (49%) means it misses some documents

**BERT-base-cased MRR: 0.0318**
- Lower MRR but finds more documents overall
- Trade-off: breadth of coverage vs. precision of ranking

## Implications for Production

### Recommendation: BERT-base-cased

**Strengths**:
1. Best Recall@100 (54%): Finds relevant documents most consistently
2. Case preservation: Handles aviation acronyms correctly
3. Well-established: Proven reliability and extensive documentation
4. Moderate size: 768-dim embeddings, ~440MB model

**Limitations**:
1. Lower MRR (0.0318): Relevant documents may not appear at top
2. Moderate Recall@10 (5.5%): Users may need to scan more results
3. No aviation-specific knowledge: Relies purely on pattern matching

### Alternative: MPNet-base-v2

**Strengths**:
1. Close second: 53% Recall@100 (only 1% behind winner)
2. Better MRR (0.0499): Ranks relevant documents higher
3. Better Recall@10 (7%): More relevant results on first page
4. Native sentence-transformers model: Easier integration

**Trade-off**: Uncased model (loses acronym case information) but has better ranking quality

## Evaluation Limitations

1. **Small Document Corpus**: Only 162 documents limits Recall@1000 differentiation
2. **Synthetic Queries**: May not represent real user information needs
3. **Single Relevant Document**: Real searches may have multiple relevant reports
4. **No Hybrid Evaluation**: Didn't test combining semantic + BM25 search
5. **No Fine-tuning**: Models tested out-of-the-box without aviation-specific tuning

## Future Work

1. **Fine-tune general models on aviation data**: Best of both worlds?
2. **Test on real user queries**: Validate against actual search behavior
3. **Hybrid search evaluation**: Combine semantic + BM25 for better coverage
4. **Larger corpus testing**: Evaluate on full 38,655 ASRS reports
5. **Query expansion**: Test if domain-specific query rewriting helps

## Conclusion

This comprehensive evaluation demonstrates that **domain-specific pre-training is not sufficient** for superior performance. General-purpose models with appropriate architectural features (case sensitivity, strong pre-training) can outperform domain-specific models on specialized tasks.

For the aviation safety search engine, **BERT-base-cased** provides the best balance of recall, reliability, and practical deployment considerations, though **MPNet-base-v2** offers a strong alternative with better ranking quality.

The surprising underperformance of SafeAeroBERT suggests that effective aviation search may depend more on robust semantic understanding and careful feature engineering (case preservation, hybrid search) than on aviation-specific language modeling alone.

---

*Evaluation conducted: February 11, 2026*
*Team: MIDS Capstone - Aviation Safety Search Engine*
*Evaluator: Niyanthri Naresh (Model Building & ML Pipeline)*
