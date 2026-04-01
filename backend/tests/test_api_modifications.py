"""Integration tests for device modification API endpoints.

Tests the full flow: upload -> map layers -> recognize -> modify -> apply -> download.
"""

import gdstk


class TestModificationAPI:
    """Integration tests for modification endpoints."""

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

    def _recognize(self, client, project_id):
        resp = client.post(
            f"/api/projects/{project_id}/devices/recognize",
            json={"method": "geometry"},
        )
        assert resp.status_code == 200
        return resp.json()

    def test_full_modify_flow(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)
        result = self._recognize(client, project_id)

        # Find a capacitor
        cap = None
        for dev in result["devices"]:
            if dev["type"] == "capacitor":
                cap = dev
                break
        assert cap is not None, "No capacitor found in test data"

        # Modify device
        resp = client.post(
            f"/api/projects/{project_id}/devices/{cap['id']}/modify",
            json={"new_value": cap["value"] * 2, "mode": "auto"},
        )
        assert resp.status_code == 200
        mod = resp.json()
        assert mod["device_id"] == cap["id"]
        assert mod["device_type"] == "capacitor"
        assert len(mod["changes"]) > 0
        mod_id = mod["id"]

        # Apply modifications
        resp = client.post(
            f"/api/projects/{project_id}/apply-modifications",
            json={"modifications": [mod_id]},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"
        assert "download_url" in resp.json()

        # Check diff
        resp = client.get(f"/api/projects/{project_id}/diff")
        assert resp.status_code == 200
        assert len(resp.json()["changes"]) > 0

        # Download
        resp = client.get(f"/api/projects/{project_id}/download")
        assert resp.status_code == 200

    def test_modify_resistor(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)
        result = self._recognize(client, project_id)

        res = None
        for dev in result["devices"]:
            if dev["type"] == "resistor":
                res = dev
                break
        assert res is not None

        resp = client.post(
            f"/api/projects/{project_id}/devices/{res['id']}/modify",
            json={"new_value": res["value"] * 2, "mode": "auto"},
        )
        assert resp.status_code == 200
        mod = resp.json()
        assert mod["device_type"] == "resistor"

    def test_modify_manual_mode(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)
        result = self._recognize(client, project_id)

        cap = None
        for dev in result["devices"]:
            if dev["type"] == "capacitor":
                cap = dev
                break
        assert cap is not None

        resp = client.post(
            f"/api/projects/{project_id}/devices/{cap['id']}/modify",
            json={
                "new_value": 5.0,
                "mode": "manual",
                "manual_params": {"width": 80, "length": 60},
            },
        )
        assert resp.status_code == 200
        mod = resp.json()
        for change in mod["changes"]:
            new_pts = change["new_points"]
            w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
            h = max(p[1] for p in new_pts) - min(p[1] for p in new_pts)
            assert abs(w - 80) < 0.01
            assert abs(h - 60) < 0.01

    def test_modify_device_not_found(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)
        self._set_layer_mapping(client, project_id)
        self._recognize(client, project_id)

        resp = client.post(
            f"/api/projects/{project_id}/devices/dev_999/modify",
            json={"new_value": 5.0, "mode": "auto"},
        )
        assert resp.status_code == 404

    def test_modify_project_not_found(self, client):
        resp = client.post(
            "/api/projects/nonexistent/devices/dev_001/modify",
            json={"new_value": 5.0},
        )
        assert resp.status_code == 404

    def test_apply_no_modifications(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)

        resp = client.post(
            f"/api/projects/{project_id}/apply-modifications",
            json={"modifications": ["mod_nonexistent"]},
        )
        assert resp.status_code == 404  # No modifications.json exists

    def test_diff_before_apply(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)

        resp = client.get(f"/api/projects/{project_id}/diff")
        assert resp.status_code == 404  # No original layout saved yet

    def test_download_original(self, client, sample_gds_with_devices):
        project_id = self._upload_gds(client, sample_gds_with_devices)

        resp = client.get(f"/api/projects/{project_id}/download")
        assert resp.status_code == 200
