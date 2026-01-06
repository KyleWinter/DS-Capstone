from src.kb.ingest.chunker import chunk_text


def test_chunker_outputs_well_formed_chunks():
    long_para = (
        "This is a paragraph about transformers and attention mechanisms. "
        "It mentions multi-head attention, positional encoding, and feed-forward layers. "
        "We want this paragraph to be long enough to pass MIN_LEN filtering. "
        "Transformer models are widely used in NLP and beyond. "
    ) * 3  # make it > 200 chars

    md = f"""# Title
{long_para}

Another paragraph mentioning attention and multi-head attention.

## Details
{long_para}
"""

    chunks = chunk_text(md, file_path="dummy.md")
    assert isinstance(chunks, list)
    assert len(chunks) >= 1

    required = {"file_path", "heading", "ordinal", "content"}
    for c in chunks:
        assert required.issubset(c.keys())
        assert c["file_path"] == "dummy.md"
        assert isinstance(c["ordinal"], int)
        assert isinstance(c["content"], str) and c["content"].strip()

    ords = [c["ordinal"] for c in chunks]
    assert ords == sorted(ords)
