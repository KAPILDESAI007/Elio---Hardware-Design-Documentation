"""Signal classifier service."""
class SignalClassifier:

    def classify(self, df):
        signals = []
        for _, row in df.iterrows():
            signals.append({
                "tag": row["Tag"],
                "io_type": row["IO Type"]
            })
        return signals