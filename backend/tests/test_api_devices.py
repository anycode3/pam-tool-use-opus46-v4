"""Integration tests for device recognition API endpoints."""

import io
import gdstk
from pathlib import Path


class TestDeviceRecognitionAPI:
    """Test the full API flow: upload -> map layers -> recognize -> list -> get."""

    def _upload_gds(self, client, gds_path):
        with open(gds_path, "rb") as f:
            resp = client.post(
                "/api/projects/upload",
                files={"file": ("test.gds", f, "application/octet-stream")},
            )
        assert resp.status_code == 200
        return resp.json()["id"]

    def _set_layer_mapping(self, client, project_id):
        resp = client.put(
            f"/api/projects/{project_id}/layer-mapping",
            json={"mappings": {
                "1/0": "ME1",
                "2/0": "ME2",
                "3/0": "TFR",
                "4/0": "VA1",
                "5/0": "GND",
            }},
        )
        assert resp.status_code == 200
        return resp.json()

    def test_full_recognition_flow(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)

        # Trigger recognition
        resp = client.post(
            f"/api/projects/{project_id}/devices/recognize",
            json={"method": "geometry"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "devices" in data
        assert "stats" in data
        assert data["stats"]["total"] > 0

        # List devices
        resp = client.get(f"/api/projects/{project_id}/devices")
        assert resp.status_code == 200
        devices = resp.json()["devices"]
        assert len(devices) > 0

        # Get individual device
        first_dev_id = devices[0]["id"]
        resp = client.get(f"/api/projects/{project_id}/devices/{first_dev_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == first_dev_id

    def test_recognize_without_mapping(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        resp = client.post(
            f"/api/projects/{project_id}/devices/recognize",
            json={"method": "geometry"},
        )
        assert resp.status_code == 400

    def test_recognize_invalid_method(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)
        resp = client.post(
            f"/api/projects/{project_id}/devices/recognize",
            json={"method": "ai_magic"},
        )
        assert resp.status_code == 400

    def test_recognize_project_not_found(self, client):
        resp = client.post(
            "/api/projects/nonexistent/devices/recognize",
            json={"method": "geometry"},
        )
        assert resp.status_code == 404

    def test_list_devices_empty(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        resp = client.get(f"/api/projects/{project_id}/devices")
        assert resp.status_code == 200
        assert resp.json()["devices"] == []

    def test_get_device_not_found(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)
        client.post(
            f"/api/projects/{project_id}/devices/recognize",
            json={"method": "geometry"},
        )
        resp = client.get(f"/api/projects/{project_id}/devices/dev_999")
        assert resp.status_code == 404

    def test_device_types_detected(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)

        resp = client.post(
            f"/api/projects/{project_id}/devices/recognize",
            json={"method": "geometry"},
        )
        data = resp.json()
        types_found = {d["type"] for d in data["devices"]}
        assert "capacitor" in types_found
        assert "resistor" in types_found
