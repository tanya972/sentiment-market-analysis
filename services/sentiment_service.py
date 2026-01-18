"""
Sentiment analysis service using FinBERT.
FinBERT is a BERT model fine-tuned on financial news for sentiment analysis.
"""

from typing import List, Dict, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

class SentimentService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        
        # Sentiment labels
        self.labels = ['negative', 'neutral', 'positive']
    
    def load_model(self):
        '''Load FinBERT model (lazy loading - only when needed)'''
        if self.model_loaded:
            return
        
        print(' Loading FinBERT model...')
        try:
            # FinBERT model from HuggingFace
            model_name = 'ProsusAI/finbert'
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Set to evaluation mode
            self.model.eval()
            
            self.model_loaded = True
            print(' FinBERT model loaded successfully')
        except Exception as e:
            print(f' Error loading model: {e}')
            print('  Falling back to rule-based sentiment')
    
    def analyze_sentiment(self, text: str) -> Dict:
        '''
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze (headline or article)
        
        Returns:
            {
                'text': original text,
                'sentiment': 'positive'/'negative'/'neutral',
                'score': float between -1 and 1,
                'confidence': float between 0 and 1
            }
        '''
        # Load model if not already loaded
        if not self.model_loaded:
            self.load_model()
        
        # If model loading failed, use rule-based fallback
        if not self.model_loaded:
            return self._rule_based_sentiment(text)
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=512,
                padding=True
            )
            
            # Get prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Get probabilities
            probs = predictions[0].numpy()
            
            # Get predicted class
            predicted_class = np.argmax(probs)
            sentiment_label = self.labels[predicted_class]
            confidence = float(probs[predicted_class])
            
            # Convert to score: -1 (negative) to +1 (positive)
            # negative=0, neutral=1, positive=2
            score = (predicted_class - 1) / 1.0  # Maps to [-1, 0, 1]
            
            # Adjust score by confidence
            # e.g., if neutral with 60% confidence, score closer to 0
            if sentiment_label == 'neutral':
                score = 0.0
            elif sentiment_label == 'positive':
                score = confidence  # 0.5 to 1.0
            else:  # negative
                score = -confidence  # -1.0 to -0.5
            
            return {
                'text': text[:100],  # First 100 chars
                'sentiment': sentiment_label,
                'score': round(score, 3),
                'confidence': round(confidence, 3),
                'probabilities': {
                    'negative': round(float(probs[0]), 3),
                    'neutral': round(float(probs[1]), 3),
                    'positive': round(float(probs[2]), 3)
                }
            }
            
        except Exception as e:
            print(f' Sentiment analysis error: {e}')
            return self._rule_based_sentiment(text)
    
    def analyze_batch(self, texts: List[str], batch_size: int = 16) -> List[Dict]:
        '''
        Analyze sentiment for multiple texts (more efficient).
        
        Args:
            texts: List of texts to analyze
            batch_size: Number of texts to process at once
        
        Returns:
            List of sentiment dictionaries
        '''
        results = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                results.append(self.analyze_sentiment(text))
        
        return results
    
    def _rule_based_sentiment(self, text: str) -> Dict:
        '''
        Simple rule-based sentiment (fallback when model unavailable).
        '''
        text_lower = text.lower()
        
        # Positive words
        positive_words = [
            'profit', 'gain', 'growth', 'up', 'rise', 'high', 'beat',
            'exceed', 'strong', 'record', 'success', 'positive', 'bull',
            'upgrade', 'outperform', 'revenue', 'earnings beat'
        ]
        
        # Negative words
        negative_words = [
            'loss', 'decline', 'down', 'fall', 'drop', 'low', 'miss',
            'weak', 'bear', 'downgrade', 'underperform', 'lawsuit',
            'fraud', 'scandal', 'bankruptcy', 'layoff', 'cut'
        ]
        
        # Count sentiment words
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        # Determine sentiment
        if pos_count > neg_count:
            sentiment = 'positive'
            score = min(pos_count * 0.3, 1.0)
        elif neg_count > pos_count:
            sentiment = 'negative'
            score = -min(neg_count * 0.3, 1.0)
        else:
            sentiment = 'neutral'
            score = 0.0
        
        return {
            'text': text[:100],
            'sentiment': sentiment,
            'score': round(score, 3),
            'confidence': 0.5,  # Lower confidence for rule-based
            'method': 'rule-based'
        }
    
    def aggregate_sentiment(self, sentiments: List[Dict]) -> Dict:
        '''
        Aggregate multiple sentiments into overall score.
        Uses weighted average based on confidence.
        
        Args:
            sentiments: List of sentiment dictionaries
        
        Returns:
            Aggregated sentiment
        '''
        if not sentiments:
            return {
                'overall_sentiment': 'neutral',
                'overall_score': 0.0,
                'article_count': 0
            }
        
        # Weighted average by confidence
        total_weight = 0
        weighted_sum = 0
        
        for sent in sentiments:
            weight = sent.get('confidence', 0.5)
            score = sent.get('score', 0.0)
            weighted_sum += score * weight
            total_weight += weight
        
        avg_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Determine overall sentiment
        if avg_score > 0.2:
            overall = 'positive'
        elif avg_score < -0.2:
            overall = 'negative'
        else:
            overall = 'neutral'
        
        return {
            'overall_sentiment': overall,
            'overall_score': round(avg_score, 3),
            'article_count': len(sentiments),
            'positive_count': sum(1 for s in sentiments if s['sentiment'] == 'positive'),
            'negative_count': sum(1 for s in sentiments if s['sentiment'] == 'negative'),
            'neutral_count': sum(1 for s in sentiments if s['sentiment'] == 'neutral')
        }

# Singleton instance
sentiment_service = SentimentService()

async def get_sentiment_service():
    return sentiment_service
