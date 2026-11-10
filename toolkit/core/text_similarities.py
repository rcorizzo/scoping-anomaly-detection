import time
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
# import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
# --> pip install tensorflow
# --> pip install --upgrade tensorflow-hub
# import tensorflow_hub as hub
from sklearn.metrics.pairwise import cosine_similarity

from help_tools import helpers as h
from help_tools.helpers import log_line
import pandas as pd
import faiss
import torch.cuda

#  --> before execution of this line
# python -m spacy download en_core_web_sm
# nlp = spacy.load("en_core_web_sm")
model_bge = SentenceTransformer('BAAI/bge-large-en-v1.5')
model_uae = SentenceTransformer("WhereIsAI/UAE-Large-V1").cuda()


def compute_model_embeddings(model, texts):
    return np.array(model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def create_faiss_index(embeddings):
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index


def embed_articles(filtered_relevant_articles: List[List[str]], query: str) -> List[List[str]]:
    texts = [filtered_relevant_article[2] + " " + filtered_relevant_article[7] for filtered_relevant_article in filtered_relevant_articles]

    article_embeddings_bge = compute_model_embeddings(model_bge, texts)
    article_embeddings_uae = compute_model_embeddings(model_uae, texts)

    index_bge = create_faiss_index(article_embeddings_bge)
    index_uae = create_faiss_index(article_embeddings_uae)

    query_embedding_bge = compute_model_embeddings(model_bge, [query])
    query_embedding_uae = compute_model_embeddings(model_uae, [query])

    k = len(filtered_relevant_articles)
    distances_bge, indices_bge = index_bge.search(query_embedding_bge, k)
    similarity_scores_bge = 1 / (1 + distances_bge[0])

    distances_uae, indices_uae = index_uae.search(query_embedding_uae, k)
    similarity_scores_uae = 1 / (1 + distances_uae[0])

    similarity_dict_bge = {index: sim for index, sim in zip(indices_bge[0], similarity_scores_bge)}
    similarity_dict_uae = {index: sim for index, sim in zip(indices_uae[0], similarity_scores_uae)}

    for i, record in enumerate(filtered_relevant_articles):
        record.append(float(similarity_dict_bge.get(i, 0)))
        record.append(float(similarity_dict_uae.get(i, 0)))

    return filtered_relevant_articles
