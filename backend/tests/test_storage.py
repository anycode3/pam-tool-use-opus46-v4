from services.storage import StorageService


def test_create_project(tmp_storage):
    svc = StorageService()
    project_id = svc.create_project("test.gds", b"fake gds content")
    assert (tmp_storage / project_id).is_dir()
    assert (tmp_storage / project_id / "original.gds").read_bytes() == b"fake gds content"


def test_create_project_dxf(tmp_storage):
    svc = StorageService()
    project_id = svc.create_project("layout.dxf", b"fake dxf content")
    assert (tmp_storage / project_id / "original.dxf").read_bytes() == b"fake dxf content"


def test_list_projects_empty(tmp_storage):
    svc = StorageService()
    assert svc.list_projects() == []


def test_list_projects(tmp_storage):
    svc = StorageService()
    svc.create_project("a.gds", b"data")
    svc.create_project("b.dxf", b"data")
    projects = svc.list_projects()
    assert len(projects) == 2


def test_get_project(tmp_storage):
    svc = StorageService()
    pid = svc.create_project("test.gds", b"data")
    info = svc.get_project(pid)
    assert info["name"] == "test.gds"
    assert info["file_type"] == "gds"


def test_delete_project(tmp_storage):
    svc = StorageService()
    pid = svc.create_project("test.gds", b"data")
    svc.delete_project(pid)
    assert not (tmp_storage / pid).exists()


def test_get_nonexistent_project(tmp_storage):
    svc = StorageService()
    assert svc.get_project("nonexistent") is None
