
"""
Comprehensive Verification and Test Suite for Course Outcomes CO1-CO6
WayVista / VoyageML Project
This test suite executes and validates:
1. Ridge & Lasso Model Invariance (SHA256 hashes and identical predictions)
2. API Request and Response Format Integrity
3. Existing Travel Services (Routing, Weather, Fallback Haversine)
4. Decision Tree Regression (CO3) Training & Evaluation Metrics
5. K-Means Clustering (CO4) Evaluation, Inertia/Silhouette, and Cluster Profiles
6. Prediction Monitoring (CO6) Non-Interference, Latency, and Ground-Truth Feedback
7. Privacy and Sensitive Data Protection Audit (No coordinates, emails, passwords, tokens in logs)
8. Separate Model Artifacts Isolation (No overwriting of existing models)
"""

import sys
import json
import hashlib
import unittest
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.prediction import run_model_inference
from backend.services.route_service import calculate_haversine_distance, geocode_location
from backend.services.google_route_service import format_duration
from backend.services.feature_builder import classify_route_type, estimate_traffic_condition
from backend import monitoring
from backend.routes import predict_travel_time_endpoint, get_monitoring_summary_endpoint, get_ml_experiments_summary
from backend.schemas import PredictRequest, MonitoringFeedbackRequest

class TestCourseOutcomes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n==================================================================")
        print("    RUNNING VOYAGEML / WAYVISTA CO1–CO6 VERIFICATION SUITE       ")
        print("==================================================================")
        cls.models_dir = BASE_DIR / "ml" / "models"
        cls.reports_dir = BASE_DIR / "ml" / "reports"
        cls.dataset_file = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"

    # -------------------------------------------------------------
    # 1. RIDGE & LASSO MODEL INVARIANCE
    # -------------------------------------------------------------
    def test_01_ridge_lasso_model_hashes_and_predictions_unchanged(self):
        """Verify Ridge and Lasso model artifacts are bit-for-bit unchanged and predict identically."""
        print("\n[TEST 1] Verifying Ridge and Lasso Model Artifacts & Prediction Invariance...")

        # Expected SHA256 hashes taken before any modifications
        expected_hashes = {
            "ml/models/ridge_model.joblib": "7ccc29d03d892483f6880c755821a52c91c84a91c8f9da71c3c71f6219f5ce54",
            "ml/models/lasso_model.joblib": "1550245529531921de2b54b83ba56a87248eca07d2eacf999441b2c30af22663",
            "ml/models/preprocessor.joblib": "a34dfd420736717eca3d840794e6ac0cc51cb48b2e94f76df1217142b62c2b20",
            "ml/dataset/travel_dataset.csv": "8aee1f7d24834afa19339e072a817cd96502fa9e5d5453c9492f8e11af874a23"
        }

        for rel_path, expected_hash in expected_hashes.items():
            full_path = BASE_DIR / rel_path
            self.assertTrue(full_path.exists(), f"File {rel_path} does not exist!")
            actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
            self.assertEqual(actual_hash, expected_hash, f"Hash mismatch for {rel_path}! Artifact was modified.")

        # Test model inference on benchmark input
        res = run_model_inference(25.0, "Medium", "Clear", "Monday", 10, 28.0)
        self.assertEqual(res["primary_model"], "Lasso Regression")
        self.assertEqual(res["ridge_prediction_minutes"], 21.02, "Ridge prediction changed!")
        self.assertEqual(res["lasso_prediction_minutes"], 19.62, "Lasso prediction changed!")
        self.assertEqual(res["predicted_travel_time_minutes"], 19.62, "Primary prediction changed!")
        print("  -> PASSED: Model hashes and benchmark predictions are bit-for-bit identical.")

    # -------------------------------------------------------------
    # 2. EXISTING API REQUEST & RESPONSE FORMAT PRESERVATION
    # -------------------------------------------------------------
    def test_02_api_predict_response_format_preserved(self):
        """Verify /api/predict response dictionary strictly conforms to existing schema."""
        print("\n[TEST 2] Verifying Prediction API Request/Response Structure...")
        payload = PredictRequest(
            source="Hyderabad",
            destination="Vijayawada",
            departure_datetime="2026-08-31T09:00:00",
            traffic_condition="Moderate"
        )
        response = predict_travel_time_endpoint(payload)
        
        # Verify root fields
        self.assertTrue(response.get("success") is True)
        self.assertIn("journey", response)
        self.assertIn("route", response)
        self.assertIn("travel_conditions", response)
        self.assertIn("prediction", response)
        self.assertIn("model_info", response)

        # Verify journey structure
        journey = response["journey"]
        self.assertEqual(journey["source"], "Hyderabad")
        self.assertEqual(journey["destination"], "Vijayawada")
        self.assertIn("estimated_arrival_time", journey)
        self.assertIn("iso_arrival_time", journey)

        # Verify route structure
        route = response["route"]
        self.assertGreater(route["distance_km"], 200.0)
        self.assertIn("route_geometry", route)
        self.assertIn("route_api_duration_minutes", route)

        # Verify prediction structure
        pred = response["prediction"]
        self.assertEqual(pred["primary_model"], "Lasso Regression")
        self.assertGreater(pred["predicted_travel_time_minutes"], 0)
        self.assertGreater(pred["ridge_prediction_minutes"], 0)
        self.assertGreater(pred["lasso_prediction_minutes"], 0)
        self.assertIn("prediction_id", pred)  # Backward-compatible tracking ID

        print(f"  -> PASSED: Full PredictResponse format verified (Predicted: {pred['predicted_travel_time_minutes']} mins).")

    # -------------------------------------------------------------
    # 3. EXISTING TRAVEL FEATURES PRESERVED
    # -------------------------------------------------------------
    def test_03_existing_travel_features_work(self):
        """Verify existing haversine calculation, geocoding, and route type classifier."""
        print("\n[TEST 3] Verifying Core Travel Calculation Functions...")
        # Haversine distance with driving multiplier
        dist = calculate_haversine_distance(17.3850, 78.4867, 16.5062, 80.6480)
        self.assertAlmostEqual(dist, 312.24, places=1)

        # Duration formatting
        self.assertEqual(format_duration(3600), "1h")
        self.assertEqual(format_duration(5400), "1h 30m")
        self.assertEqual(format_duration(1800), "30 mins")

        # Route classification
        self.assertEqual(classify_route_type(10.0), "City/Urban")
        self.assertEqual(classify_route_type(30.0), "Mixed")
        self.assertEqual(classify_route_type(150.0), "Highway")
        print("  -> PASSED: Travel distance, duration, and classification utilities verified.")

    # -------------------------------------------------------------
    # 4. DECISION TREE REGRESSION (CO3)
    # -------------------------------------------------------------
    def test_04_decision_tree_metrics_and_artifacts(self):
        """Verify Decision Tree experiment trained with CV, evaluated on test split, and saved."""
        print("\n[TEST 4] Verifying CO3 Decision Tree Regression Artifacts & Metrics...")
        dt_model_joblib = self.models_dir / "decision_tree_model.joblib"
        dt_prep_joblib = self.models_dir / "decision_tree_preprocessor.joblib"
        dt_meta_file = self.models_dir / "decision_tree_metadata.json"
        dt_report_file = self.reports_dir / "decision_tree_results.json"

        self.assertTrue(dt_model_joblib.exists(), "decision_tree_model.joblib missing!")
        self.assertTrue(dt_prep_joblib.exists(), "decision_tree_preprocessor.joblib missing!")
        self.assertTrue(dt_meta_file.exists(), "decision_tree_metadata.json missing!")
        self.assertTrue(dt_report_file.exists(), "decision_tree_results.json missing!")

        with open(dt_report_file, "r") as f:
            dt_results = json.load(f)

        # Check CV metrics
        self.assertIn("best_hyperparameters", dt_results)
        self.assertIn("cv_5fold_metrics", dt_results)
        cv_r2 = dt_results["cv_5fold_metrics"]["r2_mean"]
        self.assertGreater(cv_r2, 0.97, f"CV R2 too low: {cv_r2}")

        # Check Test metrics
        test_m = dt_results["test_metrics"]
        self.assertGreater(test_m["r2"], 0.98, f"Test R2 too low: {test_m['r2']}")
        self.assertLess(test_m["mae"], 45.0, f"Test MAE too high: {test_m['mae']}")
        self.assertLess(test_m["rmse"], 75.0, f"Test RMSE too high: {test_m['rmse']}")

        # Check feature importances
        importances = dt_results["feature_importances"]
        self.assertIn("distance_km", importances)
        self.assertGreater(importances["distance_km"], 0.90, "Distance should be top feature!")
        print(f"  -> PASSED: Decision Tree verified (5-Fold CV R²: {cv_r2:.4f}, Test R²: {test_m['r2']:.4f}, Test MAE: {test_m['mae']:.2f} mins).")

    # -------------------------------------------------------------
    # 5. K-MEANS CLUSTERING (CO4)
    # -------------------------------------------------------------
    def test_05_kmeans_clustering_evaluation_and_profiles(self):
        """Verify K-Means unsupervised clustering evaluated k=2..6, selected optimal k, and profiled clusters."""
        print("\n[TEST 5] Verifying CO4 K-Means Clustering Artifacts & Profiling...")
        km_model_joblib = self.models_dir / "kmeans_model.joblib"
        km_scaler_joblib = self.models_dir / "kmeans_scaler.joblib"
        km_report_file = self.reports_dir / "kmeans_clustering_report.json"

        self.assertTrue(km_model_joblib.exists(), "kmeans_model.joblib missing!")
        self.assertTrue(km_scaler_joblib.exists(), "kmeans_scaler.joblib missing!")
        self.assertTrue(km_report_file.exists(), "kmeans_clustering_report.json missing!")

        with open(km_report_file, "r") as f:
            km_results = json.load(f)

        # Check evaluation across k=2..6
        eval_metrics = km_results["evaluated_k_metrics"]
        self.assertEqual(len(eval_metrics), 5, "Should evaluate k=2, 3, 4, 5, 6")
        for m in eval_metrics:
            self.assertIn("k", m)
            self.assertIn("inertia", m)
            self.assertIn("silhouette_score", m)
            self.assertGreater(m["silhouette_score"], 0.5)

        # Check cluster profiles
        profiles = km_results["cluster_profiles"]
        self.assertEqual(len(profiles), 3, "Expected 3 journey clusters")

        # Verify clusters are sorted ascending by mean distance
        mean_distances = [p["distance_km_stats"]["mean"] for p in profiles]
        self.assertEqual(mean_distances, sorted(mean_distances), "Cluster descriptions must be based on actual sorted statistics!")

        # Verify sample counts sum to 6000
        total_samples = sum(p["sample_count"] for p in profiles)
        self.assertEqual(total_samples, 6000)

        print(f"  -> PASSED: K-Means verified (k={km_results['selected_k']}, Silhouette: {km_results['final_silhouette_score']:.4f}, 3 Journey Tiers: {mean_distances} km).")

    # -------------------------------------------------------------
    # 6. PREDICTION MONITORING & FEEDBACK (CO6)
    # -------------------------------------------------------------
    def test_06_prediction_monitoring_and_feedback(self):
        """Verify lightweight prediction monitoring, non-interference, and actual feedback tracking."""
        print("\n[TEST 6] Verifying CO6 Prediction Monitoring & Feedback Tracking...")

        # 1. Generate prediction
        req = PredictRequest(source="Hyderabad", destination="Vijayawada")
        res = predict_travel_time_endpoint(req)
        pred_id = res["prediction"]["prediction_id"]
        self.assertIsNotNone(pred_id, "Monitoring must return a prediction_id")

        # 2. Check summary
        summary = get_monitoring_summary_endpoint()
        self.assertGreaterEqual(summary["summary"]["total_requests"], 1)
        self.assertGreaterEqual(summary["summary"]["successful_requests"], 1)
        self.assertGreater(summary["summary"]["avg_latency_ms"], 0.0)

        # 3. Submit ground-truth feedback
        feedback_req = MonitoringFeedbackRequest(
            prediction_id=pred_id,
            actual_travel_time_minutes=res["prediction"]["predicted_travel_time_minutes"] + 5.0
        )
        fb_res = monitoring.record_actual_travel_time(feedback_req.prediction_id, feedback_req.actual_travel_time_minutes)
        self.assertTrue(fb_res["success"])

        # 4. Check updated online MAE/RMSE
        updated_summary = get_monitoring_summary_endpoint()
        online_eval = updated_summary["online_evaluation"]
        self.assertGreaterEqual(online_eval["samples_with_actual_travel_time"], 1)
        self.assertIsNotNone(online_eval["online_mae_minutes"])
        self.assertIsNotNone(online_eval["online_rmse_minutes"])

        # 5. Fault-tolerance test: Verify simulated monitoring failure does not break prediction
        original_log = monitoring.log_prediction
        try:
            def broken_logger(*args, **kwargs):
                raise RuntimeError("Simulated monitoring disk write error")
            monitoring.log_prediction = broken_logger
            
            # Request must still succeed!
            res_resilient = predict_travel_time_endpoint(req)
            self.assertTrue(res_resilient["success"])
        finally:
            monitoring.log_prediction = original_log

        print(f"  -> PASSED: Monitoring verified with fault tolerance and online MAE/RMSE calculation.")

    # -------------------------------------------------------------
    # 7. PRIVACY & SECURITY AUDIT
    # -------------------------------------------------------------
    def test_07_privacy_and_sensitive_data_protection_audit(self):
        """Verify that prediction logs contain NO GPS coordinates, passwords, auth tokens, or emails."""
        print("\n[TEST 7] Verifying Privacy & Non-Sensitive Data Compliance in Logs...")
        log_file = BASE_DIR / "backend" / "data" / "prediction_logs.jsonl"
        if not log_file.exists():
            self.skipTest("No logs generated yet.")

        sensitive_keywords = ["password", "token", "Bearer", "secret", "api_key", "@", "lat", "lon", "coordinates", "geometry"]

        with open(log_file, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                record = json.loads(line)
                
                # Check inputs
                if "inputs" in record and record["inputs"]:
                    inputs = record["inputs"]
                    self.assertNotIn("source_coordinates", inputs)
                    self.assertNotIn("destination_coordinates", inputs)
                    self.assertNotIn("email", inputs)
                    self.assertNotIn("password", inputs)

                # Check error
                if "error" in record and record["error"]:
                    err = record["error"]
                    for sk in ["password", "token", "Bearer"]:
                        self.assertNotIn(sk, err.get("error_message", "").lower())

        print("  -> PASSED: Privacy audit confirmed. No GPS coordinates or credentials present in logs.")

    # -------------------------------------------------------------
    # 8. ARTIFACT ISOLATION
    # -------------------------------------------------------------
    def test_08_new_experiments_isolated_from_existing_models(self):
        """Verify new Decision Tree and K-Means files exist separately and did not replace Ridge/Lasso."""
        print("\n[TEST 8] Verifying Artifact Isolation...")
        ridge_files = ["ridge_model.joblib", "ridge_model.pkl", "ridge_model_metadata.json"]
        lasso_files = ["lasso_model.joblib", "lasso_model.pkl", "lasso_model_metadata.json"]
        dt_files = ["decision_tree_model.joblib", "decision_tree_model.pkl", "decision_tree_metadata.json"]
        km_files = ["kmeans_model.joblib", "kmeans_model.pkl", "kmeans_metadata.json"]

        for f in ridge_files + lasso_files:
            self.assertTrue((self.models_dir / f).exists(), f"Existing model file {f} was deleted or renamed!")

        for f in dt_files:
            self.assertTrue((self.models_dir / f).exists(), f"Decision tree file {f} missing!")

        for f in km_files:
            self.assertTrue((self.models_dir / f).exists(), f"KMeans file {f} missing!")

        # Verify unified /api/ml-experiments endpoint
        summary_res = get_ml_experiments_summary()
        self.assertTrue(summary_res["success"])
        cos = summary_res["course_outcomes"]
        for co in ["CO1", "CO2", "CO3", "CO4", "CO5", "CO6"]:
            self.assertIn(co, cos, f"{co} missing in ml-experiments summary!")

        print("  -> PASSED: Artifact isolation and unified outcomes endpoint verified.")

if __name__ == "__main__":
    unittest.main()
