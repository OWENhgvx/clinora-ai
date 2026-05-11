def test_tokenize_and_sparse_empty_vocab():
    import rag

    rag._bm25_vocab = {}
    assert rag._tokenize("Chest Pain 101!") == ["chest", "pain", "101"]
    indices, values = rag._text_to_sparse("chest pain")
    assert indices == []
    assert values == []


def test_fit_bm25_builds_vocab(monkeypatch):
    import rag

    monkeypatch.setattr(rag, "_save_bm25_vocab", lambda: None)
    rag.fit_bm25(["chest pain", "pain with dyspnea"])
    assert rag._bm25_vocab
    assert "pain" in rag._bm25_vocab


def test_shutdown_closes_client_and_ignores_close_errors():
    import rag

    class FakeClient:
        def __init__(self, should_fail=False):
            self.closed = False
            self.should_fail = should_fail

        def close(self):
            if self.should_fail:
                raise RuntimeError("close failed")
            self.closed = True

    client = FakeClient()
    rag._client = client
    rag._shutdown()
    assert client.closed is True
    assert rag._client is None

    rag._client = FakeClient(should_fail=True)
    rag._shutdown()
    assert rag._client is None


def test_get_dense_model_and_reranker_are_cached(monkeypatch):
    import rag

    created_dense = []
    created_reranker = []

    class FakeSentenceTransformer:
        def __init__(self, name):
            created_dense.append(name)

    class FakeCrossEncoder:
        def __init__(self, name, max_length):
            created_reranker.append((name, max_length))

    rag._dense_model = None
    rag._reranker = None
    monkeypatch.setattr(rag, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setattr(rag, "CrossEncoder", FakeCrossEncoder)

    assert rag._get_dense_model() is rag._get_dense_model()
    assert rag._get_reranker() is rag._get_reranker()
    assert created_dense == [rag.DENSE_MODEL_NAME]
    assert created_reranker == [(rag.RERANKER_MODEL_NAME, 512)]


def test_load_and_save_bm25_vocab(monkeypatch, tmp_path):
    import rag

    db_dir = tmp_path / "qdrant_db"
    params_path = db_dir / "bm25_params.json"
    monkeypatch.setattr(rag, "DB_DIR", db_dir)
    monkeypatch.setattr(rag, "BM25_PARAMS_PATH", params_path)

    rag._bm25_vocab = {"chest": 1.0}
    rag._save_bm25_vocab()
    assert params_path.exists()

    rag._bm25_vocab = None
    rag._load_bm25_vocab()
    assert rag._bm25_vocab == {"chest": 1.0}

    params_path.unlink()
    rag._bm25_vocab = None
    rag._load_bm25_vocab()
    assert rag._bm25_vocab == {}


def test_get_client_uses_remote_qdrant_and_creates_collection(monkeypatch):
    import rag

    created = []

    class FakeCollections:
        collections = []

    class FakeClient:
        def __init__(self, host=None, port=None, path=None):
            self.host = host
            self.port = port
            self.path = path

        def get_collections(self):
            return FakeCollections()

        def create_collection(self, **kwargs):
            created.append(kwargs["collection_name"])

    rag._client = None
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("QDRANT_PORT", "6334")
    monkeypatch.setattr(rag, "QdrantClient", FakeClient)

    client = rag._get_client()
    assert client.host == "localhost"
    assert client.port == 6334
    assert created == [rag.COLLECTION_NAME]


def test_search_returns_empty_when_collection_empty(monkeypatch):
    import rag

    monkeypatch.setattr(rag, "_get_client", lambda: object())
    monkeypatch.setattr(rag, "get_collection_size", lambda: 0)
    result = rag.search("headache", n_results=3)
    assert result == []


def test_search_happy_path_with_rerank(monkeypatch):
    import rag

    class FakeEncoded:
        def tolist(self):
            return [[0.1, 0.2, 0.3]]

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            return FakeEncoded()

    class FakeHit:
        def __init__(self, score, payload):
            self.score = score
            self.payload = payload

    class FakeResults:
        def __init__(self, points):
            self.points = points

    class FakeClient:
        def query_points(self, **kwargs):
            return FakeResults(
                [
                    FakeHit(
                        2.0,
                        {
                            "title": "Doc A",
                            "authors": "Author",
                            "year": "2024",
                            "source": "PubMed",
                            "url": "https://example.com/a",
                            "qid": "Q1",
                            "focus": "headache",
                            "qtype": "diagnosis",
                            "document_id": "D1",
                            "text": "This is a long excerpt about headache.",
                        },
                    )
                ]
            )

    monkeypatch.setattr(rag, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(rag, "get_collection_size", lambda: 1)
    monkeypatch.setattr(rag, "_get_dense_model", lambda: FakeModel())
    monkeypatch.setattr(rag, "_text_to_sparse", lambda q: ([], []))
    monkeypatch.setattr(rag, "_rerank", lambda query, results, top_n: results[:top_n])

    result = rag.search("headache", n_results=1)
    assert len(result) == 1
    assert result[0]["title"] == "Doc A"
    assert result[0]["score"] >= 0.15


def test_multi_search_deduplicates_and_sorts(monkeypatch):
    import rag

    def fake_search(query, n_results=10):
        if query == "q1":
            return [
                {"qid": "A", "excerpt": "doc A", "score": 0.6},
                {"qid": "B", "excerpt": "doc B", "score": 0.4},
            ]
        return [
            {"qid": "A", "excerpt": "doc A alt", "score": 0.8},
            {"qid": "C", "excerpt": "doc C", "score": 0.7},
        ]

    monkeypatch.setattr(rag, "search", fake_search)
    out = rag.multi_search(["q1", "q2"], n_results=3)
    assert [x["qid"] for x in out] == ["A", "C", "B"]
    assert out[0]["score"] == 0.8


def test_format_references_for_prompt():
    import rag

    refs = [
        {
            "title": "Doc A",
            "source": "PubMed",
            "focus": "Headache",
            "qid": "Q1",
            "qtype": "diagnosis",
            "score": 0.93,
            "excerpt": "Clinical excerpt",
            "url": "https://example.com/a",
        }
    ]
    text = rag.format_references_for_prompt(refs)
    assert "RELEVANT MEDICAL LITERATURE" in text
    assert "Doc A" in text
    assert "Relevance Score" in text


def test_get_collection_size_returns_zero_on_exception(monkeypatch):
    import rag

    def fail_client():
        raise RuntimeError("qdrant unavailable")

    monkeypatch.setattr(rag, "_get_client", fail_client)
    assert rag.get_collection_size() == 0


def test_text_to_sparse_with_vocab():
    import rag

    rag._bm25_vocab = {"chest": 1.2, "pain": 0.8}
    indices, values = rag._text_to_sparse("chest chest pain unknown")
    assert len(indices) == 2
    assert len(values) == 2
    assert all(v > 0 for v in values)


def test_format_references_for_prompt_empty():
    import rag

    assert rag.format_references_for_prompt([]) == "No relevant medical literature found in local database."


def test_rerank_orders_by_model_score(monkeypatch):
    import rag

    class FakeScores:
        def tolist(self):
            return [0.1, 0.9]

    class FakeReranker:
        def predict(self, pairs):
            return FakeScores()

    monkeypatch.setattr(rag, "_get_reranker", lambda: FakeReranker())

    results = [
        {"title": "Low", "excerpt": "low score"},
        {"title": "High", "excerpt": "high score"},
    ]
    out = rag._rerank("query", results, top_n=2)
    assert [r["title"] for r in out] == ["High", "Low"]
    assert out[0]["score"] == 0.9


def test_search_filters_low_scores_and_handles_empty_points(monkeypatch):
    import rag

    class FakeEncoded:
        def tolist(self):
            return [[0.1, 0.2, 0.3]]

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            return FakeEncoded()

    class FakeResults:
        points = []

    class FakeClient:
        def query_points(self, **kwargs):
            return FakeResults()

    monkeypatch.setattr(rag, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(rag, "get_collection_size", lambda: 10)
    monkeypatch.setattr(rag, "_get_dense_model", lambda: FakeModel())
    monkeypatch.setattr(rag, "_text_to_sparse", lambda q: ([1], [0.5]))

    assert rag.search("query", n_results=3) == []


def test_add_documents_returns_zero_for_existing_documents(monkeypatch):
    import rag

    class FakeClient:
        def retrieve(self, **kwargs):
            return [object()]

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            raise AssertionError("encode should not run when all docs already exist")

    monkeypatch.setattr(rag, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(rag, "_get_dense_model", lambda: FakeModel())

    docs = [{"id": "doc-1", "text": "existing text", "title": "Existing"}]
    assert rag.add_documents(docs) == 0


def test_add_documents_upserts_new_documents(monkeypatch):
    import rag

    upserted_batches = []

    class FakeDenseVectors:
        def tolist(self):
            return [[0.1, 0.2, 0.3]]

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            assert texts == ["new medical document text"]
            return FakeDenseVectors()

    class FakeClient:
        def retrieve(self, **kwargs):
            return []

        def scroll(self, **kwargs):
            raise RuntimeError("scroll unavailable")

        def upsert(self, **kwargs):
            upserted_batches.append(kwargs["points"])

    monkeypatch.setattr(rag, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(rag, "_get_dense_model", lambda: FakeModel())
    monkeypatch.setattr(rag, "_load_bm25_vocab", lambda: None)
    monkeypatch.setattr(rag, "fit_bm25", lambda documents: None)
    monkeypatch.setattr(rag, "_text_to_sparse", lambda text: ([], []))
    rag._bm25_vocab = {}

    docs = [
        {
            "id": "doc-new",
            "text": "new medical document text",
            "title": "New Doc",
            "authors": "A. Author",
            "year": "2026",
            "source": "PubMed",
            "url": "https://example.com/doc-new",
        }
    ]

    assert rag.add_documents(docs) == 1
    assert len(upserted_batches) == 1
    assert len(upserted_batches[0]) == 1
    point = upserted_batches[0][0]
    assert point.payload["doc_id"] == "doc-new"
    assert point.payload["title"] == "New Doc"
