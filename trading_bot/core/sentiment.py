
import logging
from transformers import pipeline
from core.logger import setup_logger

logger = setup_logger("SentimentAnalyzer", "logs/sentiment.log")

class SentimentAnalyzer:
    _instance = None
    _classifier = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SentimentAnalyzer, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info("Initializing FinBERT pipeline...")
        try:
            self._classifier = pipeline('text-classification', model='yiyanghkust/finbert-tone', tokenizer='yiyanghkust/finbert-tone')
            logger.info("FinBERT ready.")
        except Exception as e:
            logger.error(f"Failed to initialize FinBERT: {e}")
            self._classifier = None

    def analyze(self, headlines):
        if not headlines or not self._classifier:
            return 0.0
        try:
            results = self._classifier(headlines)
            max_conf = 0.0
            for res in results:
                if res['label'] == 'Positive':
                     if res['score'] > max_conf:
                        max_conf = res['score']
            return max_conf
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return 0.0
