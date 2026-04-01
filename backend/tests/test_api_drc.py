"""Tests for DRC API endpoints."""

import base64
import json

import pytest


def _upload_gds(client, gds_path):
    """Upload a GDS file and return project_id."""
    with open(gds_path, "rb") as f:
        resp = client.post(
            "/api/projects/upload",
            files={"file": ("test.gds", f, "application/octet-stream")},
        )
    assert resp.status_code == 200
    return resp.json()["id"]


def _set_mapping(client, project_id, mappings):
    resp = client.put(
        f"/api/projects/{project_id}/layer-mapping",
        json={"mappings": mappings},
    )
    assert resp.status_code == 200


class TestDrcRulesApi:
    def test_save_and_get_rules(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        rules = [
            {"type": "min_width", "layer": "ME1", "value": 5.0, "description": "ME1 min width"},
            {"type": "min_area", "layer": "ME2", "value": 10.0},
        ]
        resp = client.post(f"/api/projects/{pid}/drc/rules", json={"rules": rules})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rules"]) == 2
        assert all(r["id"] for r in data["rules"])

        # GET rules
        resp = client.get(f"/api/projects/{pid}/drc/rules")
        assert resp.status_code == 200
        assert len(resp.json()["rules"]) == 2

    def test_get_rules_empty(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        resp = client.get(f"/api/projects/{pid}/drc/rules")
        assert resp.status_code == 200
        assert resp.json()["rules"] == []

    def test_save_rules_validation_error(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        rules = [{"type": "bad_type", "layer": "ME1", "value": 5.0}]
        resp = client.post(f"/api/projects/{pid}/drc/rules", json={"rules": rules})
        assert resp.status_code == 400

    def test_save_rules_no_rules(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        resp = client.post(f"/api/projects/{pid}/drc/rules", json={})
        assert resp.status_code == 400

    def test_save_rules_with_rule_file(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        rule_file_content = json.dumps({
            "rules": [
                {"type": "min_width", "layer": "ME1", "value": 3.0},
                {"type": "max_width", "layer": "ME2", "value": 200.0},
            ]
        })
        encoded = base64.b64encode(rule_file_content.encode()).decode()
        resp = client.post(
            f"/api/projects/{pid}/drc/rules",
            json={"rule_file": encoded},
        )
        assert resp.status_code == 200
        assert len(resp.json()["rules"]) == 2

    def test_save_rules_project_not_found(self, client, tmp_storage):
        resp = client.post(
            "/api/projects/nonexistent/drc/rules",
            json={"rules": [{"type": "min_width", "layer": "ME1", "value": 5.0}]},
        )
        assert resp.status_code == 404


class TestDrcRunApi:
    def test_full_workflow(self, client, sample_gds_with_devices):
        """Upload GDS -> set mapping -> save rules -> run DRC -> get results."""
        pid = _upload_gds(client, sample_gds_with_devices)
        _set_mapping(client, pid, {"1/0": "ME1", "2/0": "ME2", "3/0": "TFR"})

        # Save rules that will trigger violations
        # The TFR resistor is 50x5, so min_width=10 should trigger (min dim=5)
        rules = [
            {"type": "min_width", "layer": "TFR", "value": 10.0, "description": "TFR min width"},
            {"type": "min_area", "layer": "ME1", "value": 99999.0, "description": "ME1 min area"},
        ]
        resp = client.post(f"/api/projects/{pid}/drc/rules", json={"rules": rules})
        assert resp.status_code == 200

        # Run DRC
        resp = client.post(f"/api/projects/{pid}/drc/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is False
        assert data["summary"]["total"] > 0
        assert data["summary"]["errors"] > 0
        assert len(data["violations"]) == data["summary"]["total"]

        # Get results
        resp = client.get(f"/api/projects/{pid}/drc/results")
        assert resp.status_code == 200
        assert resp.json()["passed"] is False

    def test_run_drc_clean(self, client, sample_gds_with_devices):
        """Rules with very relaxed thresholds should pass."""
        pid = _upload_gds(client, sample_gds_with_devices)
        _set_mapping(client, pid, {"1/0": "ME1", "2/0": "ME2", "3/0": "TFR"})

        rules = [
            {"type": "min_width", "layer": "ME1", "value": 0.1},
            {"type": "min_area", "layer": "ME1", "value": 0.01},
        ]
        client.post(f"/api/projects/{pid}/drc/rules", json={"rules": rules})

        resp = client.post(f"/api/projects/{pid}/drc/run")
        assert resp.status_code == 200
        assert resp.json()["passed"] is True
        assert resp.json()["summary"]["total"] == 0

    def test_run_drc_no_mapping(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        # Save rules but don't set mapping
        client.post(
            f"/api/projects/{pid}/drc/rules",
            json={"rules": [{"type": "min_width", "layer": "ME1", "value": 5.0}]},
        )
        resp = client.post(f"/api/projects/{pid}/drc/run")
        assert resp.status_code == 400

    def test_run_drc_no_rules(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        _set_mapping(client, pid, {"1/0": "ME1"})
        resp = client.post(f"/api/projects/{pid}/drc/run")
        assert resp.status_code == 400

    def test_get_results_not_found(self, client, sample_gds_path):
        pid = _upload_gds(client, sample_gds_path)
        resp = client.get(f"/api/projects/{pid}/drc/results")
        assert resp.status_code == 404
