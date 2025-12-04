import os
import warnings


def main():
    # Reduce noisy logs/warnings from HF/Transformers
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    for _cat in (UserWarning, FutureWarning, DeprecationWarning):
        try:
            warnings.filterwarnings("ignore", category=_cat)
        except Exception:
            pass

    try:
        from bert_score import score as bscore
    except Exception as e:
        print("bertscore is not installed. Install with: pip install bert-score")
        return

    # Query and candidates
    query = "Input 'Review this section' in the comment content field"
    cand_1 = "Input the author name in the comment author field"
    cand_2 = "Input the comment you want to add in the comment content field"

    # Score candidates against the query (candidate vs reference)
    # Plain BERTScore
    P0, R0, F10 = bscore([cand_1, cand_2], [query, query], lang='en', rescale_with_baseline=True)
    # BERTScore with IDF weighting (computed over provided pairs automatically)
    P1, R1, F11 = bscore([cand_1, cand_2], [query, query], lang='en', rescale_with_baseline=True, idf=True)

    # Optional: Sentence-BERT cosine similarity (semantic)
    has_sbert = True
    try:
        from sentence_transformers import SentenceTransformer, util
    except Exception:
        has_sbert = False
    sbert_scores = [None, None]
    if has_sbert:
        try:
            model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            emb = model.encode([query, cand_1, cand_2], normalize_embeddings=True)
            # cosine similarity
            import numpy as np
            qv, c1v, c2v = emb[0], emb[1], emb[2]
            s1 = float(np.dot(qv, c1v))
            s2 = float(np.dot(qv, c2v))
            sbert_scores = [s1, s2]
        except Exception:
            has_sbert = False

    def to_float(tensor_val):
        try:
            return float(tensor_val)
        except Exception:
            return float(tensor_val.item())

    results = [
        {
            'tag': 'cand_1 vs query',
            'text': cand_1,
            'bert_f1': float(F10[0]),
            'bert_idf_f1': float(F11[0]),
            'sbert_cos': sbert_scores[0],
        },
        {
            'tag': 'cand_2 vs query',
            'text': cand_2,
            'bert_f1': float(F10[1]),
            'bert_idf_f1': float(F11[1]),
            'sbert_cos': sbert_scores[1],
        },
    ]

    print("Query:")
    print(f"  {query}\n")
    print("Results:")
    for r in results:
        print(f"- {r['tag']}")
        print(f"  text: {r['text']}")
        print(f"  BERTScore F1 (plain):       {r['bert_f1']:.4f}")
        print(f"  BERTScore F1 (IDF):         {r['bert_idf_f1']:.4f}")
        if r['sbert_cos'] is not None:
            print(f"  Sentence-BERT cosine:       {r['sbert_cos']:.4f}\n")
        else:
            print(f"  Sentence-BERT cosine:       (install sentence-transformers)\n")


if __name__ == "__main__":
    main()


