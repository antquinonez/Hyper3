PAPERS = {
    "attention_is_all_you_need": {"topic": "transformers", "method": "attention", "year": 2017},
    "bert": {"topic": "pretraining", "method": "transformers", "year": 2018},
    "gpt2": {"topic": "language_models", "method": "transformers", "year": 2019},
    "gpt3": {"topic": "language_models", "method": "few_shot", "year": 2020},
    "t5": {"topic": "text_to_text", "method": "transformers", "year": 2019},
    "resnet": {"topic": "computer_vision", "method": "residual_learning", "year": 2015},
    "vit": {"topic": "computer_vision", "method": "transformers", "year": 2020},
    "clip": {"topic": "multimodal", "method": "contrastive_learning", "year": 2021},
    "dalle": {"topic": "multimodal", "method": "diffusion", "year": 2021},
    "whisper": {"topic": "speech", "method": "transformers", "year": 2022},
    "langchain": {"topic": "applications", "method": "framework", "year": 2022},
    "rag": {"topic": "retrieval_augmented", "method": "retrieval", "year": 2020},
}

CITATIONS = [
    ("attention_is_all_you_need", "bert", "cited_by"),
    ("attention_is_all_you_need", "gpt2", "cited_by"),
    ("attention_is_all_you_need", "t5", "cited_by"),
    ("attention_is_all_you_need", "vit", "cited_by"),
    ("bert", "rag", "cited_by"),
    ("gpt2", "gpt3", "cited_by"),
    ("resnet", "vit", "cited_by"),
    ("clip", "dalle", "cited_by"),
    ("gpt3", "clip", "cited_by"),
    ("gpt3", "whisper", "cited_by"),
    ("gpt3", "langchain", "cited_by"),
]

TOPIC_EDGES = [
    ("bert", "gpt2", "shares_topic"),
    ("gpt2", "gpt3", "shares_topic"),
    ("gpt3", "t5", "shares_topic"),
    ("vit", "clip", "shares_topic"),
    ("clip", "dalle", "shares_topic"),
    ("rag", "langchain", "shares_topic"),
]
