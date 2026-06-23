"""Tests for batch embedding classification."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from dataroom.classification.embeddings import EmbeddingClassifier
from dataroom.classification.models import ClassificationConfig
from dataroom.classification.taxonomy import classifiable_categories, parse_categories

MINI_TAXONOMY = {
    "categories": [
        {
            "id": "02",
            "folder": "02_Land_Control",
            "description": "Land control",
            "keywords": ["psa"],
        },
        {
            "id": "05",
            "folder": "05_Environmental",
            "description": "Environmental",
            "keywords": ["brac"],
        },
    ]
}


@patch.object(EmbeddingClassifier, "_load_model")
@patch.object(EmbeddingClassifier, "ensure_ready")
def test_classify_many_batches_encode(mock_ready, mock_load_model):
    categories = classifiable_categories(parse_categories(MINI_TAXONOMY))
    classifier = EmbeddingClassifier(categories, ClassificationConfig())

    mock_model = MagicMock()
    mock_model.encode.return_value = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    classifier._model = mock_model
    classifier._index = MagicMock()
    classifier._index.search.side_effect = [
        (np.array([[0.9]]), np.array([[0]])),
        (np.array([[0.8]]), np.array([[1]])),
    ]
    classifier._category_ids = ["02", "05"]

    results = classifier.classify_many(
        [
            ("a.pdf", "purchase and sale"),
            ("b.pdf", "environmental brac report"),
        ],
        top_k=1,
    )

    assert len(results) == 2
    mock_model.encode.assert_called_once()
    assert mock_model.encode.call_args.kwargs.get("batch_size") == 32
    assert results[0][0] is not None
    assert results[1][0] is not None
