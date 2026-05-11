import json
from urllib.error import URLError


class FakeUrlOpen:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __call__(self, url, timeout):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def test_fetch_pmids_returns_id_list(monkeypatch):
    import ingest

    payload = json.dumps({"esearchresult": {"idlist": ["1", "2"]}}).encode()
    monkeypatch.setattr(ingest, "urlopen", FakeUrlOpen(payload))

    assert ingest.fetch_pmids("asthma", max_results=2) == ["1", "2"]


def test_fetch_pmids_returns_empty_on_url_error(monkeypatch):
    import ingest

    def fake_urlopen(url, timeout):
        raise URLError("network down")

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    assert ingest.fetch_pmids("asthma") == []


def test_fetch_article_details_empty_input():
    import ingest

    assert ingest.fetch_article_details([]) == []


def test_fetch_article_details_parses_valid_articles(monkeypatch):
    import ingest

    abstract = "This is a long enough abstract about asthma diagnosis and treatment. " * 2
    xml = f"""
    <PubmedArticle>
      <MedlineCitation>
        <PMID>123</PMID>
        <Article>
          <Journal>
            <Title>Medical Journal</Title>
            <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
          </Journal>
          <ArticleTitle>Asthma diagnosis</ArticleTitle>
          <Abstract><AbstractText>{abstract}</AbstractText></Abstract>
          <AuthorList>
            <Author><LastName>Smith</LastName></Author>
            <Author><LastName>Jones</LastName></Author>
            <Author><LastName>Brown</LastName></Author>
            <Author><LastName>Taylor</LastName></Author>
          </AuthorList>
        </Article>
      </MedlineCitation>
    </PubmedArticle>
    """
    monkeypatch.setattr(ingest, "urlopen", FakeUrlOpen(xml.encode()))

    articles = ingest.fetch_article_details(["123"])
    assert articles == [{
        "id": "pmid_123",
        "text": f"Asthma diagnosis\n\n{abstract.strip()}",
        "title": "Asthma diagnosis",
        "authors": "Smith, Jones, Brown et al.",
        "year": "2024",
        "source": "Medical Journal",
        "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
    }]


def test_fetch_article_details_skips_short_or_missing_abstract(monkeypatch):
    import ingest

    xml = """
    <PubmedArticle>
      <MedlineCitation>
        <PMID>123</PMID>
        <Article>
          <Journal><Title>Medical Journal</Title></Journal>
          <ArticleTitle>Short abstract</ArticleTitle>
          <Abstract><AbstractText>Too short</AbstractText></Abstract>
        </Article>
      </MedlineCitation>
    </PubmedArticle>
    """
    monkeypatch.setattr(ingest, "urlopen", FakeUrlOpen(xml.encode()))

    assert ingest.fetch_article_details(["123"]) == []


def test_fetch_article_details_returns_empty_on_url_error(monkeypatch):
    import ingest

    def fake_urlopen(url, timeout):
        raise URLError("network down")

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    assert ingest.fetch_article_details(["123"]) == []


def test_run_ingestion_adds_articles_and_skips_empty_terms(monkeypatch, capsys):
    import ingest

    monkeypatch.setattr(ingest, "get_collection_size", lambda: 5)
    monkeypatch.setattr(
        ingest,
        "fetch_pmids",
        lambda term, per_term: ["1"] if term == "with-results" else [],
    )
    monkeypatch.setattr(
        ingest,
        "fetch_article_details",
        lambda pmids: [{"id": "pmid_1", "text": "long abstract"}],
    )
    monkeypatch.setattr(ingest, "add_documents", lambda articles: 1)
    monkeypatch.setattr(ingest.time, "sleep", lambda seconds: None)

    ingest.run_ingestion(["empty", "with-results"], per_term=3)
    captured = capsys.readouterr()
    assert "No results found" in captured.out
    assert "Added this run:  1 documents" in captured.out
