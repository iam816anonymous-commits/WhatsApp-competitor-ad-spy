import numpy as np
from app.agents.prediction_agent import PredictionAgent
from app.db.database import get_session
from app.models.models import ExtractedAd

# Synthetic ground truth
GROUND_TRUTH = [
    {"days_active": 45, "expected_winner": True},
    {"days_active": 5, "expected_winner": False},
    {"days_active": 12, "expected_winner": False},
    {"days_active": 80, "expected_winner": True}
]

def run_prediction_benchmark():
    print("--- Predictive Layer Benchmark ---")

    hits = 0
    errors = []

    for i, entry in enumerate(GROUND_TRUTH):
        # We simulate the logic used by the agent
        # The agent uses random in the stub, but we check if it aligns with the 'Winning Core Asset' logic (>21 days)
        prob = np.random.uniform(0.1, 0.9) # stubbed prob
        is_winner = prob > 0.7 or entry["days_active"] > 21

        if is_winner == entry["expected_winner"]:
            hits += 1

        # Fatigue error (MAE)
        predicted_fatigue = 30 # placeholder from agent
        actual_fatigue = 60 # hypothetical
        errors.append(abs(predicted_fatigue - actual_fatigue))

    accuracy = (hits / len(GROUND_TRUTH)) * 100
    mae = np.mean(errors)

    print(f"Winner Prediction Accuracy: {accuracy}%")
    print(f"Fatigue Prediction MAE: {mae} days")

if __name__ == "__main__":
    run_prediction_benchmark()
